#!/usr/bin/env python3
"""B3 -- iGUARD (SOSP'21) runner into the unified baseline schema, shardable.

iGUARD is an NVBit tool: `LD_PRELOAD=detector.so ./app` (its README) instruments
the SASS at load time and reports races in-GPU. Report format (detector.cu ~L648):
    Race: Missing blkfence|gpufence|strong op|atom scope|lock|warpsync
    <file:line or SASS offset> - (TID <warp>, <addr>)
    Write: ... / Read: ...            (metadata lines)
The location string is what nvbit_get_line_info yields when the app was built
with -lineinfo (all our corpora are), so iGUARD's native identifiers are source
lines; reports are deduped on (race kind, location).

Setup is setup/iguard_setup.sh (3h box). If the built tool is absent this runner
exits 3 with a blocker message; nothing is stubbed or simulated. Must run on a
GPU node.

  $PY eval/baselines/run_iguard.py --pset P5 --id P5-canary
  $PY eval/baselines/run_iguard.py --pset P1,P2,P3,P4,P5,P6 --shard 0/32
"""
import argparse
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

IGUARD_SO = os.environ.get("IGUARD_SO", f"{HERE}/setup/iguard/iguard.so")
_RACE = re.compile(r"^Race: (Missing [a-z ]+|Improper atom scope)\s*$", re.M)
_LOC = re.compile(r"^(\S.*?) - \(TID (\d+), ([0-9a-fA-F]+)\)\s*$", re.M)
_SRCLINE = re.compile(r"([\w.+-]+\.cuh?) - Kernel .*?: Line (\d+)")


def _shard(items, shard):
    if not shard:
        return items
    k, n = (int(x) for x in shard.split("/"))
    return [it for i, it in enumerate(items) if i % n == k]


def parse_reports(text):
    """-> (deduped [kind@location], set(source lines)). Each 'Race:' banner is
    followed by the access location line(s); pair every banner with the next
    location line."""
    reps, lines = [], set()
    kinds = [(m.start(), m.group(1)) for m in _RACE.finditer(text)]
    locs = [(m.start(), m.group(1).strip()) for m in _LOC.finditer(text)]
    j = 0
    for pos, kind in kinds:
        while j < len(locs) and locs[j][0] < pos:
            j += 1
        loc = locs[j][1] if j < len(locs) else "?"
        key = f"{kind.replace(' ', '_')}@{loc.replace(' ', '')}"
        if key not in reps:
            reps.append(key)
        for fn, ln in _SRCLINE.findall(loc):
            lines.add(f"{os.path.basename(fn)}:{ln}")
    return reps, lines


def run_one(mrow, cuda, reps, workroot):
    exe = mrow["exe"]
    common = dict(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                  build=mrow["build"], input=mrow["input"], tool="iguard")
    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        return [blib.row(**common, verdict="ERROR", notes="missing-exe")]
    exe_dir = os.path.dirname(exe)
    app_src = f"{HERE}/corpora/HeCBench/src/{mrow['program']}"
    if mrow["pset"] in ("P7", "P9") and os.path.isdir(app_src):
        exe_dir = app_src        # HeCBench apps resolve inputs relative to their source dir
    args = [a for a in mrow["args"].split() if a] if mrow["args"] else []
    stdin = mrow["stdin"] or None
    man_timeout = int(mrow["timeout"] or 300)
    nenv = blib.base_env(cuda)
    logd = f"{workroot}/{mrow['id']}"
    os.makedirs(logd, exist_ok=True)
    # native wall (1 run) -> same timeout formula as cuVein: min(max(10x,120),1200)
    w, _, nrc, to = blib.run_timed([os.path.abspath(exe), *args], nenv, exe_dir,
                                   man_timeout, stdin_path=stdin,
                                   stderr_path=f"{logd}/native.txt")
    native = w if (not to and isinstance(w, (int, float))) else None
    timeout = min(max(int(10 * native), 120), 1200) if native else man_timeout
    env = blib.base_env(cuda)
    env["LD_PRELOAD"] = IGUARD_SO
    env["TIMEOUT"] = "0"          # iGUARD's own kernel timeout off; ours governs
    rows = []
    for rep in range(1, reps + 1):
        out_path = f"{logd}/iguard_rep{rep}.txt"
        wall, peak, rc, to = blib.run_timed([os.path.abspath(exe), *args], env, exe_dir,
                                            timeout, poll_mem=True, stdin_path=stdin,
                                            stderr_path=out_path)
        if to:
            rows.append(blib.row(**common, rep=rep, verdict="TIMEOUT", rc=124, wall_s=wall,
                                 native_wall_s=native if native is not None else "",
                                 peak_mb=round(peak / 1024.0, 1) if peak else "",
                                 notes=f"timeout={timeout}s"))
            continue
        try:
            text = open(out_path, "r", errors="replace").read()
        except OSError:
            text = ""
        # iGUARD prints "iGUARD: Starting context" only under TOOL_VERBOSE; the
        # NVBit banner + a per-launch "Kernel <name> - grid size" line (printed by
        # the detector's launch callback) prove the tool was loaded AND hooked.
        started = ("Binary Instrumentation Tool" in text
                   and ("\nKernel " in text or "Inspecting function" in text
                        or "Allocated " in text))
        reps_, lines = parse_reports(text)
        if not started:
            tail = blib.tail_text(out_path, 4, 200).replace(",", ";").replace("\n", " | ")
            rows.append(blib.row(**common, rep=rep, verdict="ERROR", rc=rc, wall_s=wall,
                                 native_wall_s=native if native is not None else "",
                                 notes=f"iguard-not-started;rc={rc};native_rc={nrc};{tail}"))
            continue
        verdict = "RACE" if reps_ else "CLEAN"
        kinds = sorted({r.split("@")[0] for r in reps_})
        rows.append(blib.row(**common, rep=rep, verdict=verdict,
                             reports_dedup=len(reps_), report_ids=" ".join(reps_)[:2000],
                             report_lines=" ".join(sorted(lines)), wall_s=wall,
                             native_wall_s=native if native is not None else "",
                             peak_mb=round(peak / 1024.0, 1) if peak else "", rc=rc,
                             notes=("kinds=" + "|".join(kinds) if kinds else "") +
                                   (f";rc={rc}" if rc else "")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--pset", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--shard", default="", help="k/N")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if not os.path.exists(IGUARD_SO):
        sys.stderr.write(
            f"BLOCKER: iGUARD tool not built at {IGUARD_SO}. Run "
            f"eval/baselines/setup/iguard_setup.sh (3h box) first. Not simulating.\n")
        sys.exit(3)
    cuda = blib.resolve_cuda_home()
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    rows = [m for m in blib.read_manifest(a.manifest)
            if (not psets or m["pset"] in psets) and (not ids or m["id"] in ids)]
    rows = _shard(rows, a.shard)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    path = a.out or f"{blib.RESULTS_DIR}/baselines-iguard-shard{tag}.csv"
    workroot = os.environ.get("BASELINE_TRACE_DIR") or f"/mnt/local/{os.environ.get('USER','u')}/iguard_logs"
    try:
        os.makedirs(workroot, exist_ok=True)
    except OSError:
        workroot = f"{HERE}/setup/build_logs/iguard_logs"
        os.makedirs(workroot, exist_ok=True)
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        for i, m in enumerate(rows, 1):
            print(f"[{i}/{len(rows)}] {m['id']}", flush=True)
            try:
                for r in run_one(m, cuda, a.reps, workroot):
                    w.writerow(r)
            except Exception as e:
                w.writerow(blib.row(id=m["id"], pset=m["pset"], program=m["program"],
                                    build=m["build"], input=m["input"], tool="iguard",
                                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
            fh.flush()
    print(f"iguard: {len(rows)} program(s) -> {path}")


if __name__ == "__main__":
    main()

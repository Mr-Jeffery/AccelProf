#!/usr/bin/env python3
"""B1 -- the full compute-sanitizer family (memcheck / racecheck / synccheck /
initcheck) into the unified baseline schema, shardable.

Generalises run_racecheck.py (kept as-is for the original shared-mem-only run):
every tool runs on EVERY manifest row (racecheck's documented scope is __shared__
hazards, so its CLEAN on a shared_mem=0 program is by construction; the other
three apply to any kernel). Verdict semantics per tool:
  racecheck : RACE  = >=1 shared-memory hazard         (RACECHECK SUMMARY: N hazard)
  memcheck  : RACE  = >=1 memory error (OOB/misaligned) (ERROR SUMMARY: N error)
  synccheck : RACE  = >=1 barrier/sync misuse          (ERROR SUMMARY: N error)
  initcheck : RACE  = >=1 uninitialized global read    (ERROR SUMMARY: N error)
i.e. for the three non-race tools the schema's RACE column means "tool FLAGGED
the program"; make_tables.py labels those columns FLAGGED and keeps them out of
the race disagreement table. The distinct headline kinds the sanitizer printed
(e.g. "Invalid __global__ read of size 4", "Barrier error") go to notes.
Deterministic -> 1 rep. Must run on a GPU node.

  $PY eval/baselines/run_sanitizer.py --shard 0/32            # all tools, all rows
  $PY eval/baselines/run_sanitizer.py --tools synccheck --id P1-...
"""
import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

TOOLS = ("memcheck", "racecheck", "synccheck", "initcheck")
_HAZ = re.compile(r"RACECHECK SUMMARY:\s*(\d+)\s+hazard")
_ERR = re.compile(r"ERROR SUMMARY:\s*(\d+)\s+error")
_LOC = re.compile(r"in \S*?([\w.+-]+\.cu:\d+)")
# headline kinds: "========= Invalid __global__ read of size 4 bytes", "========= Barrier error",
# "========= Uninitialized __global__ memory read of size 4 bytes", "========= Program hit ..."
_KIND = re.compile(r"^=========\s+((?:Invalid|Barrier|Uninitialized|Program hit|Host API|Leaked|Potential|Race|Error)[^\n]{0,70})",
                   re.M)


def _shard(items, shard):
    if not shard:
        return items
    k, n = (int(x) for x in shard.split("/"))
    return [it for i, it in enumerate(items) if i % n == k]


def run_one(mrow, tool, cs, cuda, reps):
    exe = mrow["exe"]
    common = dict(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                  build=mrow["build"], input=mrow["input"], tool=tool)
    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        return blib.row(**common, verdict="ERROR", notes="missing-exe")
    exe_dir = os.path.dirname(exe)
    # HeCBench apps resolve inputs relative to their source dir (`../data/...`,
    # `input/...`); run them there so the sanitizer sees the same inputs as the
    # collector (which mirrors that layout in its scratch dir).
    app_src = f"{HERE}/corpora/HeCBench/src/{mrow['program']}"
    if mrow["pset"] in ("P7", "P9") and os.path.isdir(app_src):
        exe_dir = app_src
    args = [a for a in mrow["args"].split() if a] if mrow["args"] else []
    stdin = mrow["stdin"] or None
    env = blib.base_env(cuda)
    timeout = int(mrow["timeout"] or 300)
    cmd = [cs, "--tool", tool]
    if tool == "racecheck":
        cmd += ["--racecheck-report", "analysis"]
    cmd += [os.path.abspath(exe), *args]
    best, count, lines, kinds, rc = None, None, [], [], ""
    for _ in range(reps):
        fin = open(stdin, "rb") if stdin else subprocess.DEVNULL
        t0 = time.perf_counter()
        try:
            p = subprocess.run(cmd, cwd=exe_dir, env=env, stdin=fin,
                               capture_output=True, text=True, errors="replace",
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            return blib.row(**common, verdict="TIMEOUT", rc=124,
                            wall_s=round(time.perf_counter() - t0, 3), notes=f"timeout={timeout}s")
        finally:
            if stdin and not fin.closed:
                fin.close()
        wall = round(time.perf_counter() - t0, 3)
        best = wall if best is None else min(best, wall)
        out = p.stdout + p.stderr
        m = _HAZ.search(out) if tool == "racecheck" else _ERR.search(out)
        if not m:   # racecheck also prints an ERROR SUMMARY on internal errors; accept either
            m = _ERR.search(out) or _HAZ.search(out)
        count = int(m.group(1)) if m else count
        lines = sorted(set(_LOC.findall(out)))
        kinds = sorted({k.strip() for k in _KIND.findall(out)
                        if "SUMMARY" not in k and "COMPUTE-SANITIZER" not in k})[:4]
        rc = p.returncode
    if count is None:
        tail = " ".join((p.stderr or p.stdout).strip().splitlines()[-2:])[:160].replace(",", ";")
        return blib.row(**common, verdict="ERROR", wall_s=best, rc=rc,
                        notes=f"no-summary;rc={rc};{tail}")
    verdict = "RACE" if count > 0 else "CLEAN"
    unit = "hazards" if tool == "racecheck" else "errors"
    notes = f"{unit}={count}" + (";kinds=" + "|".join(kinds).replace(",", ";") if kinds else "")
    return blib.row(**common, verdict=verdict, reports_dedup=len(lines),
                    report_ids=" ".join(lines), report_lines=" ".join(lines),
                    wall_s=best, rc=rc, notes=notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--tools", default=",".join(TOOLS))
    ap.add_argument("--pset", default="")
    ap.add_argument("--id", default="", help="run only these ids (comma list)")
    ap.add_argument("--shard", default="", help="k/N over (row, tool) pairs")
    ap.add_argument("--reps", type=int, default=1, help="deterministic; 1 rep")
    ap.add_argument("--out", default="", help="override output csv path")
    a = ap.parse_args()
    cuda = blib.resolve_cuda_home()
    cs = f"{cuda}/compute-sanitizer/compute-sanitizer"
    if not os.path.exists(cs):
        cs = "compute-sanitizer"
    tools = [t for t in a.tools.split(",") if t]
    bad = [t for t in tools if t not in TOOLS]
    if bad:
        sys.exit(f"unknown sanitizer tool(s) {bad}; choose from {TOOLS}")
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    work = []
    for mrow in blib.read_manifest(a.manifest):
        if psets and mrow["pset"] not in psets:
            continue
        if ids and mrow["id"] not in ids:
            continue
        for t in tools:
            work.append((mrow, t))
    work = _shard(work, a.shard)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    path = a.out or f"{blib.RESULTS_DIR}/baselines-sanitizer-shard{tag}.csv"
    import csv
    os.makedirs(blib.RESULTS_DIR, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        for i, (mrow, t) in enumerate(work, 1):
            print(f"[{i}/{len(work)}] {t} {mrow['id']}", flush=True)
            try:
                w.writerow(run_one(mrow, t, cs, cuda, a.reps))
            except Exception as e:  # never lose the row
                w.writerow(blib.row(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                                    build=mrow["build"], input=mrow["input"], tool=t,
                                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
            fh.flush()
    print(f"sanitizer: {len(work)} (program,tool) runs -> {path}")


if __name__ == "__main__":
    main()

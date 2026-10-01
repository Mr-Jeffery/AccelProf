#!/usr/bin/env python3
"""B2 HiRace (SC'24 artifact) runner over the consolidated Indigo-original suite (PI).

HiRace is source-level: every device array is wrapped in HiRaceDataWrap<T> by macros
(src/hirace/*.h, header-only) and the kernel gets shadow-metadata params; the program is
then compiled with plain nvcc (`-DRACECHECK -I src/hirace`) and prints
    HiRace:
        Race @ line N in file F on a READ|WRITE: ...
The artifact ships ALL 590 IndigoSuite codes hand-instrumented
(indigo/indigo_hirace_sources/<pattern>/<pattern>_hirace<suffix>.cu -- bug variants
included; an earlier version of this runner globbed `*_hirace.cu` and so ran only the 21
bug-free base patterns). build_indigo_full.py compiles each twin to bin/PI_hirace/<code>.

For every PI manifest row this runs the twin of that row's code with THAT ROW's graph and
launch arguments (the artifact's Table-1 inputs at 256x1024, SuperCollider's at 256x4),
so HiRace rows share ids with every other detector. native_wall_s = the row's own
uninstrumented binary (one discarded warm-up, best of 3), giving HiRace a slowdown.
Verdict RACE iff any rep prints a HiRace report; reports deduped on file:line.
There is no instrumenter for other suites (src/clang is an unfinished prototype), so
non-PI rows are not runnable -> no row. Never simulated.

  srun ... bash -c 'source eval/baselines/gpu_env.sh;
                    $PY eval/baselines/run_hirace.py --pset PI --shard 0/32'
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

TWINS = f"{HERE}/bin/PI_hirace"
_RACE = re.compile(r"Race @ line (\d+) in file (\S+) on a (\w+)")
_HR = re.compile(r"HiRace:|Race @ line")


def _shard(items, shard):
    if not shard:
        return items
    k, n = (int(x) for x in shard.split("/"))
    return [it for i, it in enumerate(items) if i % n == k]


def run_row(m, env, reps, work):
    common = dict(id=m["id"], pset=m["pset"], program=m["program"], build=m["build"],
                  input=m["input"], tool="hirace")
    twin = f"{TWINS}/{m['program']}"
    if not os.path.exists(twin):
        return [blib.row(**common, verdict="ERROR", notes="hirace-twin-not-built")]
    args = m["args"].split()
    native = None
    if os.path.exists(m["exe"]):
        blib.run_timed([m["exe"], *args], env, work, 300)            # warm-up, discarded
        walls = [w for w, _, rc, to in (blib.run_timed([m["exe"], *args], env, work, 300)
                                        for _ in range(3)) if not to and w != "NA"]
        native = min(walls) if walls else None
    timeout = min(max(10 * (native or 0), 120), 1200)
    rows = []
    log = f"{work}/hirace_{m['id']}.log"
    for rep in range(1, reps + 1):
        wall, peak_kb, rc, to = blib.run_timed([twin, *args], env, work, timeout,
                                               poll_mem=True, stderr_path=log)
        try:
            out = open(log, errors="replace").read()
        except OSError:
            out = ""
        if to:
            verdict, ids = "TIMEOUT", []
        elif _HR.search(out):
            verdict = "RACE"
            ids = sorted({f"{os.path.basename(f)}:{ln}:{k}" for ln, f, k in _RACE.findall(out)})
        elif rc not in (0,) and "result" not in out:
            verdict, ids = "ERROR", []          # crashed before finishing (no verdict line)
        else:
            verdict, ids = "CLEAN", []
        notes = f"timeout={timeout}s" if to else (f"rc={rc};{blib.tail_text(log, 3, 200)}" if verdict == "ERROR" else "")
        rows.append(blib.row(**common, rep=rep, verdict=verdict, reports_dedup=len(ids),
                             report_ids=" ".join(ids),
                             report_lines=" ".join(sorted({i.rsplit(':', 1)[0] for i in ids})),
                             wall_s=wall, native_wall_s=native if native is not None else "",
                             peak_mb=round(peak_kb / 1024.0, 1) if peak_kb else "", rc=rc, notes=notes))
    try:
        os.remove(log)
    except OSError:
        pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--pset", default="PI")
    ap.add_argument("--id", default="")
    ap.add_argument("--shard", default="", help="k/N")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if not os.path.isdir(TWINS):
        sys.stderr.write(f"BLOCKER: HiRace twins not built at {TWINS} "
                         f"(run build_indigo_full.py). Not simulating.\n")
        sys.exit(3)
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    rows = [m for m in blib.read_manifest(a.manifest)
            if (not psets or m["pset"] in psets) and (not ids or m["id"] in ids)]
    rows = _shard(rows, a.shard)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    path = a.out or f"{blib.RESULTS_DIR}/baselines-hirace-shard{tag}.csv"
    work = os.environ.get("BASELINE_TRACE_DIR") or f"/mnt/local/{os.environ.get('USER', 'u')}/hirace_logs"
    try:
        os.makedirs(work, exist_ok=True)
    except OSError:
        work = f"{HERE}/setup/build_logs/hirace_logs"
        os.makedirs(work, exist_ok=True)
    env = blib.base_env(blib.resolve_cuda_home())
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        for n, m in enumerate(rows, 1):
            print(f"[hirace {n}/{len(rows)}] {m['id']}", flush=True)
            for r in run_row(m, env, a.reps, work):
                w.writerow(r)
            fh.flush()
    print(f"hirace: {len(rows)} rows -> {path}")


if __name__ == "__main__":
    main()

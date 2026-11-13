#!/usr/bin/env python
"""X13: one program run under accelprof with YOSEMITE_SHARD_STATS=1, harness-style (blib.base_env,
native run first, accelprof -t pc_dependency_analysis -n N), keeping what the harness deletes: the
shards_N.json / shards_sync_N.json files, plus wall, native wall, peak RSS and the drained-record total.

  CUVEIN_HOME=<runtime> x13_run.py --id ID --exe EXE --args "A B" --mode collector-only|scalar-clock
                                   --workers 16 --out DIR [--cap S] [--no-stats]
Output DIR/run.json, DIR/shards/shards_*.json, DIR/log.txt (tool stdout+stderr), DIR/native.txt.
"""
import argparse, glob, json, os, re, shutil, socket, sys, time

sys.path.insert(0, os.path.join(os.environ["CUVEIN_HOME"], "eval", "baselines"))
import blib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True)
ap.add_argument("--exe", required=True)
ap.add_argument("--args", default="")
ap.add_argument("--mode", default="collector-only", choices=["collector-only", "scalar-clock"])
ap.add_argument("--workers", type=int, default=16)
ap.add_argument("--out", required=True)
ap.add_argument("--cap", type=int, default=7200)
ap.add_argument("--no-stats", action="store_true")
ap.add_argument("--no-native", action="store_true")
ap.add_argument("--preload", default="", help="LD_PRELOAD for the tool run (malloc_log.c: names the allocation of a hot segment)")
a = ap.parse_args()

out = os.path.abspath(a.out)
shutil.rmtree(out, ignore_errors=True)
work = f"{out}/work"
os.makedirs(work)
os.makedirs(f"{out}/shards")
cuda = blib.resolve_cuda_home()
exe = os.path.realpath(a.exe)
base = os.path.basename(exe)
link = f"{work}/{base}"
os.symlink(exe, link)
args = [x for x in a.args.split() if x]
rec = dict(id=a.id, mode=a.mode, workers=a.workers, exe=a.exe, args=a.args, host=socket.gethostname(),
           started=time.strftime("%Y-%m-%d %H:%M:%S"), runtime=os.environ["CUVEIN_HOME"],
           slurm_job=os.environ.get("SLURM_JOB_ID", ""), stats=not a.no_stats)

nenv = blib.base_env(cuda)
if not a.no_native:
    w, _, rc, to = blib.run_timed([link, *args], nenv, work, a.cap, stderr_path=f"{out}/native.txt")
    rec.update(native_wall=w, native_rc=rc, native_timed_out=to)
else:
    rec.update(native_wall=None, native_rc=0)

cubindir = f"{work}/cubins"
scope, _ = blib.extract(exe, cubindir, nenv)
if a.mode == "scalar-clock":
    os.environ["BASELINE_HB_DUMP"] = "0"       # X1b's settings: aggregates, no hb_events dump
env = blib.base_env(cuda, hb_trace=True, hb_mode=a.mode, scope_file=scope or None)
env["YOSEMITE_WORKER_COUNT"] = str(a.workers)
if a.mode == "scalar-clock":
    env["YOSEMITE_HB_SHARDS"] = str(a.workers)
if not a.no_stats:
    env["YOSEMITE_SHARD_STATS"] = "1"
if a.preload:
    env["LD_PRELOAD"] = a.preload
accel = ["accelprof", "-t", "pc_dependency_analysis", "-n", str(a.workers), f"./{base}", *args]
rec["cmd"] = " ".join(accel)
rec["env"] = {k: v for k, v in env.items() if k.startswith(("YOSEMITE_", "BASELINE_"))}
rec["env"]["BASELINE_HB_DUMP"] = os.environ.get("BASELINE_HB_DUMP", "")
log = f"{out}/log.txt"
wall, peak, rc, to = blib.run_timed(accel, env, work, a.cap, poll_mem=True, stderr_path=log)
rec.update(wall=wall, peak_mb=round(peak / 1024.0, 1) if peak else None, rc=rc, timed_out=to)

deps = sorted(glob.glob(f"{work}/dependency_{base}_*"), key=os.path.getmtime)
dep = deps[-1] if deps else ""
kj = glob.glob(f"{dep}/kernel_*.json") if dep else []
rec["nkernels"] = len([f for f in kj if re.fullmatch(r"kernel_\d+\.json", os.path.basename(f))])
for f in glob.glob(f"{dep}/shards_*.json") if dep else []:
    shutil.move(f, f"{out}/shards/")
rec["nshards_files"] = len(os.listdir(f"{out}/shards"))
tot = 0
for line in open(log, errors="replace"):
    m = re.search(r"GPU data analysis called with size = (\d+)", line)
    if m:
        tot += int(m.group(1))
rec["drained_records"] = tot
rec["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
json.dump(rec, open(f"{out}/run.json", "w"), indent=1)
shutil.rmtree(work, ignore_errors=True)
print(json.dumps({k: rec[k] for k in ("id", "mode", "wall", "native_wall", "peak_mb", "rc", "timed_out",
                                      "nkernels", "nshards_files", "drained_records")}))

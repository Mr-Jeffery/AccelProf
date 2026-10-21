#!/usr/bin/env python3
"""X1-follow (eval/X1_FOLLOW.md): one timed run of one manifest program under one configuration,
with the harness's own pieces (blib.base_env, blib.run_timed, blib.extract, collect_one's input
layout and command `accelprof -t pc_dependency_analysis [-n N] ./<exe> <args>`). GPU node only.

  --config collector      YOSEMITE_HB_TRACE unset: the collector + the PcDependency graph, no HbClock
                          (hb_clock_reset returns at once without _hb_trace,
                          sanalyzer/src/tools/pc_dependency_analysis.cpp:2579)
  --config scalar-clock   YOSEMITE_HB_TRACE=1 + the mode knob (--mode-knob mode|no-engine for a
  --config vector-clock   pre-T8 runtime) [+ YOSEMITE_HB_DUMP=0 with --no-dump] [+ YOSEMITE_HB_STATS=1]
  --workers 1|default     -n 1 (X1's setting), or no -n (YOSEMITE_WORKER_COUNT unset: the analyzer
                          takes std::thread::hardware_concurrency(), .cpp:2358)
  --runtime DIR           ACCEL_PROF_HOME for the tool run (default: the installed runtime)

Differences from parallel.collect_one, all recorded in the summary: accelprof runs with -v (the
app's stdout, which carries the analyzer's per-drain line "[PC_DEPENDENCY] GPU data analysis called
with size = N", goes to <work>/<exe>.accelprof.log instead of /dev/null, so the drained record
count of the run itself is known); MaxRSS is polled as the largest VmHWM of any process of the
tree (the per-process peak RSS getrusage reports) next to the harness's summed-VmRSS peak;
kernel JSON mtimes give per-kernel durations. Writes <out>/<name>.json and <out>/<name>.log.gz.
"""
import argparse
import csv
import glob
import gzip
import json
import os
import re
import resource
import shutil
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import blib  # noqa: E402

DRAIN = re.compile(rb"GPU data analysis called with size = (\d+)")


def layout(row, idir, work):
    """parallel.collect_one's input layout (HeCBench apps open inputs relative to the CWD)."""
    if row["pset"] in ("P7", "P9"):
        hec = f"{os.path.dirname(HERE)}/corpora/HeCBench/src"
        app = f"{hec}/{row['program']}"
        for lnk, tgt in ((f"{idir}/data", f"{hec}/data"), (f"{work}/input", f"{app}/input"),
                         (f"{work}/data", f"{app}/data")):
            if os.path.isdir(tgt) and not os.path.lexists(lnk):
                os.symlink(tgt, lnk)
        for x in row["args"].split():
            if x.startswith("../") and os.path.isdir(f"{hec}/{x.split('/')[1]}") \
                    and not os.path.lexists(f"{idir}/{x.split('/')[1]}"):
                os.symlink(f"{hec}/{x.split('/')[1]}", f"{idir}/{x.split('/')[1]}")


def hwm_poller(stop, out):
    """max VmHWM (kB) over every process below this one, polled each 0.2 s."""
    me = os.getpid()
    while not stop.is_set():
        for p in blib._descendants(me):
            if p == me:
                continue
            try:
                with open(f"/proc/{p}/status") as f:
                    for ln in f:
                        if ln.startswith("VmHWM:"):
                            out[0] = max(out[0], int(ln.split()[1]))
                            break
            except OSError:
                pass
        stop.wait(0.2)


def count_in_json(path):
    """-> (hb_events_count or None, number of '"seq": ' records or None, hb_stats dict or None)."""
    n_seq, tail = 0, b""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > 64 << 20:              # a dump: count records streaming, never json.load
            prev = b""
            while True:
                b = f.read(64 << 20)
                if not b:
                    break
                n_seq += (prev[-16:] + b).count(b'{"seq": ') - prev[-16:].count(b'{"seq": ')
                prev = b
            f.seek(max(0, size - (8 << 20)))
            tail = f.read()
            m = re.search(rb'"hb_events_count": (\d+)', tail)
            return (int(m.group(1)) if m else None), n_seq, None
        txt = f.read()
    m = re.search(rb'"hb_events_count": (\d+)', txt)
    st = None
    try:
        d = json.loads(txt)
        st = d.get("hb_stats")
        n_seq = len(d["hb_events"]) if isinstance(d.get("hb_events"), list) else None
    except (ValueError, KeyError):
        n_seq = txt.count(b'{"seq": ')
    return (int(m.group(1)) if m else None), n_seq, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--config", required=True, choices=("collector", "scalar-clock", "vector-clock"))
    ap.add_argument("--workers", default="1")
    ap.add_argument("--cap", type=int, required=True)
    ap.add_argument("--runtime", default=os.environ.get("ACCEL_PROF_HOME", "/home/fzheng4/AccelProf"))
    ap.add_argument("--mode-knob", default="mode", choices=("mode", "no-engine"))
    ap.add_argument("--no-dump", action="store_true", help="YOSEMITE_HB_DUMP=0 (T4 and later)")
    ap.add_argument("--hb-stats", action="store_true", help="YOSEMITE_HB_STATS=1")
    ap.add_argument("--sidecar-py", default="", help="the atomic-scope sidecar script to use (a candidate's own)")
    ap.add_argument("--native-reps", type=int, default=3)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True, help="summary dir (home)")
    ap.add_argument("--work", default=f"/mnt/beegfs/{os.environ['USER']}/x1_follow/runs")
    ap.add_argument("--extra-env", default="", help="K=V,K=V added to the tool env")
    a = ap.parse_args()

    row = next(r for r in csv.DictReader(open(f"{os.path.dirname(HERE)}/manifest.csv")) if r["id"] == a.id)
    idir = f"{a.work}/{a.name}"
    work, logs = f"{idir}/work", f"{idir}/logs"
    shutil.rmtree(idir, ignore_errors=True)
    os.makedirs(work)
    os.makedirs(logs)
    os.makedirs(a.out, exist_ok=True)
    layout(row, idir, work)
    exe = os.path.realpath(row["exe"])
    base = os.path.basename(exe)
    os.symlink(exe, f"{work}/{base}")
    args = [x for x in row["args"].split() if x] if row["args"] else []
    stdin = row["stdin"] or None
    cuda = blib.resolve_cuda_home()
    nenv = blib.base_env(cuda)
    s = dict(id=a.id, name=a.name, config=a.config, workers=a.workers, cap=a.cap, runtime=a.runtime,
             mode_knob=a.mode_knob, no_dump=a.no_dump, hb_stats=a.hb_stats, node=socket.gethostname(),
             cpu=subprocess.run("lscpu | sed -n 's/^Model name: *//p'", shell=True, capture_output=True,
                                text=True).stdout.strip(),
             nproc=os.cpu_count(), slurm_job=os.environ.get("SLURM_JOB_ID", ""),
             started=time.strftime("%Y-%m-%d %H:%M:%S"))
    nat = []
    for r_ in range(a.native_reps):
        w, _, rc, to = blib.run_timed([f"{work}/{base}", *args], nenv, work, int(row["timeout"] or 600),
                                      stdin_path=stdin, stderr_path=f"{logs}/native_rep{r_ + 1}.txt")
        nat.append(dict(wall=w, rc=rc, timed_out=to))
    s["native"] = nat
    env = blib.base_env(cuda)
    rt = os.path.realpath(a.runtime)
    env.update(ACCEL_PROF_HOME=rt, CUVEIN_HOME=rt, PATH=f"{rt}/bin:" + env["PATH"])
    if a.config != "collector":
        scope, _ = blib.extract(exe, f"{work}/cubins", nenv)
        if a.sidecar_py:            # the candidate's own sidecar script over the same dots
            dots = sorted(glob.glob(f"{work}/cubins/*.dot"))
            cand = f"{work}/cubins/atomic_scope.cand.txt"
            r = subprocess.run([f"{blib.APH}/.env/bin/python", a.sidecar_py, *dots, "-o", cand],
                               capture_output=True, text=True)
            s["sidecar_rc"] = r.returncode
            if r.returncode == 0 and os.path.exists(cand):
                scope = cand
            else:                    # recorded; the harness's sidecar stays
                s["sidecar_err"] = r.stderr[-800:]
            s["sidecar"] = scope
        env["YOSEMITE_HB_TRACE"] = "1"
        if a.mode_knob == "no-engine":
            if a.config == "scalar-clock":
                env["YOSEMITE_HB_NO_ENGINE"] = "1"
        else:
            env["YOSEMITE_HB_MODE"] = a.config
        if a.no_dump:
            env["YOSEMITE_HB_DUMP"] = "0"
        if scope:
            env["YOSEMITE_ATOMIC_SCOPE_FILE"] = scope
        s["scope_file"] = bool(scope)
    if a.hb_stats:
        env["YOSEMITE_HB_STATS"] = "1"
    for kv in [x for x in a.extra_env.split(",") if x]:
        k, v = kv.split("=", 1)
        env[k] = v
    s["env"] = {k: v for k, v in env.items() if k.startswith(("YOSEMITE_", "ACCEL_PROF", "CUVEIN_"))}
    s["libs"] = subprocess.run(f"ldd {rt}/lib/libcompute_sanitizer.so | awk '/sanalyzer/{{print $3}}'",
                               shell=True, capture_output=True, text=True).stdout.strip()
    cmd = ["accelprof", "-v", "-t", "pc_dependency_analysis",
           *(["-n", a.workers] if a.workers != "default" else []), f"./{base}", *args]
    s["cmd"] = " ".join(cmd)
    print(json.dumps({k: s[k] for k in ("name", "node", "cpu", "cmd", "env", "libs")}), flush=True)
    stop, hwm = threading.Event(), [0]
    th = threading.Thread(target=hwm_poller, args=(stop, hwm), daemon=True)
    th.start()
    t0 = time.time()
    wall, peak, rc, to = blib.run_timed(cmd, env, work, a.cap, poll_mem=True, stdin_path=stdin,
                                        stderr_path=f"{logs}/tool.txt")
    stop.set()
    th.join()
    s.update(wall=wall, peak_mb_sumrss=round(peak / 1024, 1), maxrss_mb_hwm=round(hwm[0] / 1024, 1),
             maxrss_mb_rusage=round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
             rc=rc, timed_out=to, t0=t0, finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    deps = sorted(glob.glob(f"{work}/dependency_{base}_*"), key=os.path.getmtime)
    kjs = sorted(glob.glob(f"{deps[-1]}/kernel_*.json"),
                 key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))) if deps else []
    ks = []
    for kj in kjs:
        ev, nseq, st = count_in_json(kj) if a.config != "collector" else (None, None, None)
        ks.append(dict(file=os.path.basename(kj), t=round(os.path.getmtime(kj) - t0, 3),
                       mb=round(os.path.getsize(kj) / 1e6, 2), hb_events_count=ev, seq_records=nseq,
                       hb_stats=st))
    s["kernels"] = ks
    s["nkernels"] = len(ks)
    vlog = f"{work}/{base}.accelprof.log"
    drains, recs = 0, 0
    if os.path.exists(vlog):
        with open(vlog, "rb") as f:
            for ln in f:
                m = DRAIN.search(ln)
                if m:
                    drains += 1
                    recs += int(m.group(1))
        s["vlog_mb"] = round(os.path.getsize(vlog) / 1e6, 2)
    s.update(drains=drains, drained_records=recs)
    evs = [k["hb_events_count"] for k in ks if k["hb_events_count"] is not None]
    s["hb_events_count"] = sum(evs) if evs else None
    s["tool_tail"] = blib.tail_text(f"{logs}/tool.txt", 15, 1500)
    json.dump(s, open(f"{a.out}/{a.name}.json", "w"), indent=1, default=str)
    with gzip.open(f"{a.out}/{a.name}.log.gz", "wb") as g:      # tool stderr + the -v log, capped
        for p in (f"{logs}/tool.txt", vlog):
            if os.path.exists(p):
                g.write(f"==== {os.path.basename(p)}\n".encode())
                with open(p, "rb") as f:
                    g.write(f.read(5 << 20))
    print(json.dumps({k: s[k] for k in ("name", "wall", "rc", "timed_out", "nkernels", "drains",
                                        "drained_records", "hb_events_count", "maxrss_mb_hwm",
                                        "peak_mb_sumrss", "native")}), flush=True)


if __name__ == "__main__":
    main()

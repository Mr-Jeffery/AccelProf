#!/usr/bin/env python3
"""X7 A4: peak memory and wall of the verdict step (run_cuvein._analyze_reports) of one stored
recording at a given pool size, and a hash of its output.

  $PY x7_mem.py --mode-dir <store>/<id>/<mode> --dots-dir <store>/<id>/dots --workers N \
      [--no-cache] [--label L]

The analysis runs in a child process that leads its own process group (setsid); the parent
samples every 0.25 s the group's summed RSS (/proc/<pid>/stat) and summed PSS
(/proc/<pid>/smaps_rollup: shared copy-on-write pages split between the processes sharing
them) and prints the peaks. The child prints sha256 of the canonical JSON of the result, so
two runs (N = 1 vs N = 16) can be compared. The harness is imported from $CUVEIN_HOME."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--mode-dir", required=True)
ap.add_argument("--dots-dir", required=True)
ap.add_argument("--workers", type=int, required=True)
ap.add_argument("--no-cache", action="store_true")
ap.add_argument("--label", default="")
ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
a = ap.parse_args()

if a.child:
    home = os.environ.get("CUVEIN_HOME") or os.environ.get("ACCEL_PROF_HOME")
    sys.path.insert(0, f"{home}/eval/baselines")
    import run_cuvein as rc
    t0 = time.time()
    ids, pcs, raw = rc._analyze_reports(a.mode_dir, a.dots_dir, workers=a.workers,
                                        cache=not a.no_cache)
    canon = json.dumps([ids, sorted(pcs), raw], sort_keys=True, default=repr)
    print(json.dumps({"wall": round(time.time() - t0, 2), "race_ids": len(ids), "raw": len(raw),
                      "sha256": hashlib.sha256(canon.encode()).hexdigest()}), flush=True)
    sys.exit(0)


def group(pgid):
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            rest = open(f"/proc/{d}/stat").read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if int(rest[2]) == pgid and rest[0] != "Z":
            out.append((int(d), int(rest[21])))
    return out


def pss_kb(pid):
    try:
        for line in open(f"/proc/{pid}/smaps_rollup"):
            if line.startswith("Pss:"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


page = os.sysconf("SC_PAGE_SIZE")
cmd = [sys.executable, os.path.abspath(__file__), "--child", "--mode-dir", a.mode_dir,
       "--dots-dir", a.dots_dir, "--workers", str(a.workers)] + (["--no-cache"] if a.no_cache else [])
t0 = time.time()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, start_new_session=True)
peak_rss = peak_pss = peak_n = 0
while p.poll() is None:
    g = group(p.pid)
    rss = sum(r for _, r in g) * page
    pss = sum(pss_kb(pid) for pid, _ in g) * 1024
    peak_rss, peak_pss, peak_n = max(peak_rss, rss), max(peak_pss, pss), max(peak_n, len(g))
    time.sleep(0.25)
out = p.stdout.read().strip().splitlines()
res = json.loads(out[-1]) if out else {}
print(json.dumps({"label": a.label, "workers": a.workers, "cache": not a.no_cache, "rc": p.returncode,
                  "wall_total": round(time.time() - t0, 2), **res,
                  "peak_rss_mb": round(peak_rss / 2**20, 1), "peak_pss_mb": round(peak_pss / 2**20, 1),
                  "peak_procs": peak_n, "mode_dir": a.mode_dir}), flush=True)

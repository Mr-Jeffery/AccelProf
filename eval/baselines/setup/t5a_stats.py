#!/usr/bin/env python3
"""T5a step 2 (eval/MEMORY_FOOTPRINT.md): attribute the vector-clock engine's memory.

For each program: extract the CFG + atomic-scope sidecar (blib.extract, as the harness
does), run it once under the worktree's detector (ACCEL_PROF_HOME) with
YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=<mode> YOSEMITE_HB_STATS=1 [YOSEMITE_HB_STATS_EVERY=n]
and accelprof -v under a wall-clock cap, poll the process tree's RSS, then collect
  * every kernel's `hb_stats` object (the engine's containers + the buffered hb_events at
    kernel end; read from the tail of kernel_N.json, never json.loads of the whole dump),
  * every mid-kernel `[HB_STATS]` line of the accelprof log (a kernel killed before its
    end still leaves its growth curve),
  * each kernel JSON's size on disk.
-> <out>/<label>.json. Work dirs (dumps) go to /mnt/beegfs/$USER/t5a_stats/<label>/.

  t5a_stats.py --label reduction-norace-large --exe .../reduction_norace \
      --stdin .../reduction.large.in --cap 900 --out eval/baselines/setup/t5a_stats
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import blib  # noqa: E402

TAIL = 1 << 20      # hb_stats is the dump's last field: 1 MiB of tail is plenty


def hb_stats_of(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - TAIL))
        tail = f.read().decode("utf-8", "replace")
    i = tail.rfind('"hb_stats": ')
    if i < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(tail[i + len('"hb_stats": '):])
    return obj


def sha16(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--exe", required=True)
    ap.add_argument("--args", default="")
    ap.add_argument("--stdin", default="")
    ap.add_argument("--mode", default=blib.hb_modes.VECTOR_CLOCK, type=blib.hb_modes.check)
    ap.add_argument("--cap", type=int, default=600, help="wall-clock cap (s)")
    ap.add_argument("--every", type=int, default=0, help="YOSEMITE_HB_STATS_EVERY records")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cuda = blib.resolve_cuda_home()
    work = f"/mnt/beegfs/{os.environ['USER']}/t5a_stats/{a.label}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    base = os.path.basename(a.exe)
    os.symlink(os.path.realpath(a.exe), f"{work}/{base}")
    nenv = blib.base_env(cuda)
    scope, cubs = blib.extract(os.path.realpath(a.exe), f"{work}/cubins", nenv)
    env = blib.base_env(cuda, hb_trace=True, hb_mode=a.mode, scope_file=scope)
    env["YOSEMITE_HB_STATS"] = "1"
    if a.every:
        env["YOSEMITE_HB_STATS_EVERY"] = str(a.every)
    cmd = ["accelprof", "-v", "-t", "pc_dependency_analysis", "-n", "1", f"./{base}",
           *[x for x in a.args.split() if x]]
    t0 = time.time()
    wall, peak_kb, rc, timed_out = blib.run_timed(cmd, env, work, a.cap, poll_mem=True,
                                                  stdin_path=a.stdin or None,
                                                  stderr_path=f"{work}/run.txt")
    lib = blib.hb_modes.engine_library(blib.APH)
    log = f"{work}/{base}.accelprof.log"
    mid, end_lines = [], 0
    if os.path.exists(log):
        for line in open(log, errors="replace"):
            if line.startswith("[HB_STATS] mid-kernel after"):
                m = re.match(r"\[HB_STATS\] mid-kernel after (\d+) records: \{(.*)\} rss_kb (\d+)", line)
                if m:
                    mid.append({"records": int(m.group(1)), "rss_kb": int(m.group(3)),
                                **json.loads("{" + m.group(2) + "}")})
            elif line.startswith("[HB_STATS] kernel_"):
                end_lines += 1
    kernels = []
    for kj in sorted(glob.glob(f"{work}/dependency_*/kernel_*.json"),
                     key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))):
        st = None
        try:
            st = hb_stats_of(kj)
        except (ValueError, OSError) as e:
            st = {"error": f"{type(e).__name__}: {e}"[:200]}
        kernels.append({"file": os.path.basename(kj), "bytes_on_disk": os.path.getsize(kj),
                        "hb_stats": st})
    res = {"label": a.label, "exe": a.exe, "args": a.args, "stdin": a.stdin, "mode": a.mode,
           "cap_s": a.cap, "every": a.every, "node": os.uname().nodename,
           "accel_prof_home": blib.APH,
           "engine_lib": lib, "engine_lib_sha16": sha16(lib),
           "wall_s": wall, "peak_rss_mb": round(peak_kb / 1024, 1), "rc": rc,
           "timed_out": timed_out, "kernels": kernels, "kernel_end_lines": end_lines,
           "mid_kernel": mid, "elapsed_s": round(time.time() - t0, 1)}
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/{a.label}.json", "w") as f:
        json.dump(res, f, indent=1)
    print(f"{a.label}: rc={rc} timed_out={timed_out} wall={wall} peak={res['peak_rss_mb']} MB "
          f"kernels={len(kernels)} mid-kernel snapshots={len(mid)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""X15: run an rw_attribute script unchanged, with progress lines per sd.analyze call (the script prints nothing until it ends).
usage: x15_launch.py <rw_attribute script> <its args...>. Wraps sync_dominance.analyze (same arguments, same result) before the script imports it."""
import os, sys, time, runpy
APH = os.environ["ACCEL_PROF_HOME"]
sys.path.insert(0, f"{APH}/python")
import sync_dominance as sd
T0 = time.time()
_orig = sd.analyze


def analyze(dot, kj, *a, **k):
    t = time.time()
    tag = f"{os.path.basename(kj)} dot={os.path.basename(dot)}"
    print(f"[x15 t={t - T0:.0f}s] analyze start {tag}", flush=True)
    try:
        r = _orig(dot, kj, *a, **k)
    except BaseException as e:
        print(f"[x15 t={time.time() - T0:.0f}s] analyze {tag} -> {type(e).__name__} after {time.time() - t:.1f}s", flush=True)
        raise
    print(f"[x15 t={time.time() - T0:.0f}s] analyze done {tag} in {time.time() - t:.1f}s", flush=True)
    return r


sd.analyze = analyze
script = os.path.abspath(sys.argv[1])
sys.argv = [script] + sys.argv[2:]
runpy.run_path(script, run_name="__main__")

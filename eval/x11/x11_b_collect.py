#!/usr/bin/env python3
"""X11 stage B, recording half of a cuRace clock-mode run: parallel.collect_one only (no analysis).
  python x11_b_collect.py HARNESS_WT MANIFEST ID CAP      (env: BASELINE_MODES, BASELINE_TRACE_DIR, BASELINE_HB_*)
cmd_collect of parallel.py does not pass --timeout-floor, so the tool timeout would be 10x native; this calls
collect_one exactly as cmd_run does: floor = cap = CAP, 1 rep. A run that reaches the cap is killed by the harness
(SIGKILL of the process group); the kernel JSONs of the kernels that had finished are kept under
<store>/<id>/<mode>-partial-rep1/ (a prefix; the last file may be truncated)."""
import os, sys
W, manifest, pid, cap = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, f"{W}/eval/baselines")
import blib, parallel
parallel.STORE = parallel._store_root()
os.makedirs(parallel.STORE, exist_ok=True)
cuda = blib.resolve_cuda_home()
rows = list(parallel._rows(manifest, None, {pid}))
assert len(rows) == 1, rows
print(f"[collect] {pid} cap={cap}s modes={os.environ.get('BASELINE_MODES')} store={parallel.STORE}", flush=True)
parallel.collect_one(rows[0], cuda, 1, floor=cap, cap=cap)
print("[collect] done", flush=True)

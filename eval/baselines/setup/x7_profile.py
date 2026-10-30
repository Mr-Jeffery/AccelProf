#!/usr/bin/env python3
"""X7 A2: cProfile the verdict step (run_cuvein._analyze_reports) over one stored recording,
in one process (one worker), and print the top functions by cumulative time plus the split
between graph construction and judging.

  $PY x7_profile.py --mode-dir <store>/<id>/<mode> --dots-dir <store>/<id>/dots \
      --limit-s 3600 --out <file>.prof [--workers 1]

The harness (run_cuvein, sync_dominance) is imported from $CUVEIN_HOME (blib's rule).
--limit-s stops the analysis with SIGALRM and profiles what ran; the number of kernel JSONs
analysed by then is printed. --workers is passed to _analyze_reports only when given (the
pre-X7 code has no such parameter)."""
import argparse
import cProfile
import glob
import os
import pstats
import signal
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--mode-dir", required=True)
ap.add_argument("--dots-dir", required=True)
ap.add_argument("--limit-s", type=int, default=0)
ap.add_argument("--out", required=True)
ap.add_argument("--label", default="")
ap.add_argument("--workers", type=int, default=None)
ap.add_argument("--top", type=int, default=40)
a = ap.parse_args()

home = os.environ.get("CUVEIN_HOME") or os.environ.get("ACCEL_PROF_HOME")
sys.path.insert(0, f"{home}/eval/baselines")
import run_cuvein as rc  # noqa: E402
import sync_dominance as sd  # noqa: E402

kjs = sorted(glob.glob(f"{a.mode_dir}/kernel_*.json"))
size = sum(os.path.getsize(k) for k in kjs)
print(f"[{a.label}] mode_dir={a.mode_dir} kernel_jsons={len(kjs)} bytes={size} "
      f"dots={sorted(os.path.basename(d) for d in glob.glob(a.dots_dir + '/*.dot'))} "
      f"sync_dominance={sd.__file__} python={sys.version.split()[0]}", flush=True)

calls = {"analyze": 0, "align_err": 0, "kj": set()}
_orig = sd.analyze


def _counting(dot, kj, *args, **kw):
    calls["analyze"] += 1
    calls["kj"].add(kj)
    try:
        return _orig(dot, kj, *args, **kw)
    except sd.AlignmentError:
        calls["align_err"] += 1
        raise


sd.analyze = _counting


class _Stop(Exception):
    pass


def _alarm(*_):
    raise _Stop()


signal.signal(signal.SIGALRM, _alarm)
prof = cProfile.Profile()
stopped, res = False, None
t0 = time.time()
if a.limit_s:
    signal.alarm(a.limit_s)
prof.enable()
try:
    kw = {} if a.workers is None else {"workers": a.workers}
    res = rc._analyze_reports(a.mode_dir, a.dots_dir, **kw)
except _Stop:
    stopped = True
finally:
    prof.disable()
    signal.alarm(0)
wall = time.time() - t0
prof.dump_stats(a.out)
print(f"[{a.label}] wall={wall:.1f}s stopped_at_limit={stopped} analyze_calls={calls['analyze']} "
      f"alignment_errors={calls['align_err']} kernel_jsons_started={len(calls['kj'])}/{len(kjs)}"
      + ("" if res is None else f" race_ids={len(res[0])} raw={len(res[2])}"), flush=True)

st = pstats.Stats(prof)
st.sort_stats("cumulative").print_stats(a.top)
st.sort_stats("tottime").print_stats(25)

# the split: cumulative seconds of named functions (all files unless a file filter is given)
WANT = [("parse_dot", "sync_dominance"), ("graph_from_dot_file", "pydot"),
        ("_label_lines", "sync_dominance"),
        ("__init__", "sync_dominance.py"), ("_build_ins_graph", "sync_dominance"),
        ("immediate_dominators", "dominance"), ("_dom_sets", "sync_dominance"),
        ("select_kernel", "sync_dominance"), ("_demangle", "sync_dominance"),
        ("analyze", "sync_dominance"), ("loads", "json"), ("read_text", "pathlib"),
        ("trace_rmw_points", "sync_dominance"), ("barrier_only_pairs", "sync_dominance"),
        ("attach_trace", "sync_dominance"),
        ("judge", "sync_dominance"), ("ordered", "sync_dominance"),
        ("dominance", "sync_dominance"), ("chain", "sync_dominance"),
        ("_chain_from", "sync_dominance"), ("_cs_fenced", "sync_dominance"),
        ("fenced", "sync_dominance"), ("has_path", "networkx"),
        ("_dedup_key", "aggregate"), ("_host_reports", "run_cuvein")]
tot = sum(v[2] for v in st.stats.values())
print(f"\n[{a.label}] SPLIT (cumulative s; profile total tottime {tot:.1f}s, wall {wall:.1f}s)")
for fn, ff in WANT:
    ct = nc = 0.0
    for (f, line, name), (cc, ncalls, tt, cum, callers) in st.stats.items():
        if name == fn and ff in f:     # sync_dominance's only __init__ is HBGraph's
            ct += cum
            nc += ncalls
    print(f"  {fn:24s} {ff:18s} cum={ct:10.2f}s  calls={int(nc)}")

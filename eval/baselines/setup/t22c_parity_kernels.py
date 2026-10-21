#!/usr/bin/env python3
"""T22 cont.: t4_parity.py's per-kernel comparison (--counts-le in scalar-clock mode) for named kernel
JSONs of one program, one process per kernel and no time cap -- for the kernels whose record replay
(barrier_only_pairs over hb_events, quadratic in a location's slots: bfs's flag word) outlasted
t4_parity.py's per-program cap.
  t22c_parity_kernels.py --store <store> --id <program id> --mode scalar-clock --kernels 14,15,... --out <json>
"""
import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t4_parity  # noqa: E402


def one(args):
    dots, kj, le = args
    t0 = time.time()
    try:
        r = t4_parity.compare_kernel(dots, kj, le)
    except Exception as e:   # a malformed dump is a finding, not a crash
        r = {"kernel": os.path.basename(kj), "status": f"error:{type(e).__name__}:{e}"[:200]}
    r["secs"] = round(time.time() - t0, 1)
    print(f"{r['kernel']}: {r.get('status')} ({r['secs']} s) counts {r.get('counts')}", flush=True)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--mode", default="scalar-clock")
    ap.add_argument("--kernels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.environ["CUVEIN_BARRIER_PASS_MAX_LANES"] = str(10 ** 12)   # the cutoff lifted
    idir = f"{a.store}/{a.id}"
    dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
    ks = [f"{idir}/{a.mode}/kernel_{k}.json" for k in a.kernels.split(",")]
    with Pool(len(ks)) as p:
        res = p.map(one, [(dots, kj, a.mode == "scalar-clock") for kj in ks])
    json.dump([{"id": a.id, "modes": {a.mode: {"kernels": res, "secs": max(r["secs"] for r in res)}}}],
              open(a.out, "w"), indent=1)
    bad = [r["kernel"] for r in res if r.get("status") != "ok"]
    print(f"{len(res)} kernels, {len(res) - len(bad)} ok; not ok: {bad}")


if __name__ == "__main__":
    main()

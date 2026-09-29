#!/usr/bin/env python3
"""T5b acceptance: engine == oracle on programs of every pset, recorded with the T5b runtime.

  select   10 programs per pset from the committed baseline CSVs (vector-clock rows that
           finished, RACE/CLEAN), spread over the event-count range; every finished one where
           a pset has fewer. -> setup/t5b_parity_ids.txt
  compare  --store <BeeGFS store of a vector-clock recording>: per program and kernel dump,
           hb_oracle.analyze over the dump's hb_events vs the engine's keys in the same
           dump -- hb_races at the green set's aggregate key (test_sync_dominance._race_key:
           pc pair, kind, class, space, distance, async side, count, a2_uncertain),
           hb_races_sync_only, the coherence profile hashes, and whether the strict oracle
           raised where the engine recorded a tv_violation (then re-run non-strict). Each program in
           a child under a wall-clock cap (the Python oracle is the slow side).
           -> <out>.json and a summary on stdout.

    .env/bin/python eval/baselines/setup/t5b_parity.py select
    .env/bin/python eval/baselines/setup/t5b_parity.py compare --store /mnt/beegfs/$USER/cuvein_traces/t5b-parity \
        --out eval/baselines/setup/t5b_parity.json --cap 3600
"""
import argparse
import collections
import csv
import glob
import json
import multiprocessing as mp
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, f"{APH}/python")


def race_key(r):   # = python/test_sync_dominance._race_key
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


def select(_a):
    man = {r["id"] for r in csv.DictReader(open(f"{APH}/eval/baselines/manifest.csv"))}
    rows = {}
    for p in sorted(glob.glob(f"{APH}/eval/results/baselines-cuvein*.csv")):
        for r in csv.DictReader(open(p)):
            if r["mode"] != "vector-clock" or r["verdict"] not in ("RACE", "CLEAN") or r["id"] not in man:
                continue
            m = re.search(r"events=(\d+)", r["notes"])
            rows[r["id"]] = (r["pset"], int(m.group(1)) if m else -1)
    ps = collections.defaultdict(list)
    for i, (p, ev) in rows.items():
        ps[p].append((ev, i))
    out = []
    for p in sorted(ps):
        L = sorted(ps[p])
        pick = L if len(L) <= 10 else [L[round(k * (len(L) - 1) / 9)] for k in range(10)]
        out += [i for _, i in pick]
        print(f"{p}: {len(pick)} of {len(L)} finished", file=sys.stderr)
    with open(f"{HERE}/t5b_parity_ids.txt", "w") as f:
        f.write("\n".join(out) + "\n")


def one(idir, q):
    import hb_oracle as ho
    import sync_dominance as sd
    res = []
    dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
    for kj in sorted(glob.glob(f"{idir}/vector-clock/kernel_*.json"),
                     key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))):
        t0 = time.time()
        tj = json.load(open(kj))
        if "hb_events" not in tj:
            res.append(dict(kernel=os.path.basename(kj), status="no-hb_events"))
            continue
        rep, errs, relaxed = None, [], False
        for strict in ("1", "0"):   # a TV violation raises in the oracle; the engine records
            os.environ["YOSEMITE_HB_STRICT"] = strict      # and continues (as t9_rescore.py)
            for d in dots:
                try:
                    rep = ho.analyze(d, kj)
                    break
                except sd.AlignmentError as e:
                    errs.append(str(e)[:200])
            if rep is not None or not tj.get("tv_violation"):
                break
            relaxed = True
        os.environ.pop("YOSEMITE_HB_STRICT", None)
        if rep is None:
            res.append(dict(kernel=os.path.basename(kj), status="no-aligned-cfg", errors=errs[:3]))
            continue
        eng = collections.Counter(race_key(r) for r in tj.get("hb_races", []))
        orc = collections.Counter(race_key(r) for r in rep["races"])
        eng_pi = {int(a): v["hash"] for a, v in tj.get("coherence_profile", {}).items()}
        orc_pi = {int(a, 16): v["hash"] for a, v in rep.get("coherence_profile", {}).items()}
        ok = dict(races=eng == orc,
                  sync_only=tj.get("hb_races_sync_only") == rep["races_sync_only"],
                  coherence=eng_pi == orc_pi,
                  # the oracle raised under strict iff the engine recorded a violation
                  tv=bool(tj.get("tv_violation")) == relaxed)
        res.append(dict(kernel=os.path.basename(kj), status="ok" if all(ok.values()) else "MISMATCH",
                        checks=ok, events=len(tj["hb_events"]), race_keys=len(eng),
                        sync_pairs=len(tj.get("hb_races_sync_only") or []),
                        tv_engine=tj.get("tv_violation") or "", secs=round(time.time() - t0, 1),
                        engine_only=[list(k) for k in eng - orc][:5],
                        oracle_only=[list(k) for k in orc - eng][:5]))
    q.put(res)


def compare(a):
    ids = [ln.strip() for ln in open(a.ids) if ln.strip()]
    if a.shard:
        k, n = map(int, a.shard.split("/"))
        ids = ids[k::n]
    out, bad = {}, 0
    for i in ids:
        idir = f"{a.store}/{i}"
        if not glob.glob(f"{idir}/vector-clock/kernel_*.json"):
            out[i] = dict(status="no-vector-clock-dump")
            print(f"{i}: no vector-clock dump", flush=True)
            continue
        q = mp.Queue()
        p = mp.Process(target=one, args=(idir, q))
        p.start()
        try:
            r = q.get(timeout=a.cap)
        except Exception:
            r = None
        p.join(5)
        if p.is_alive():
            p.kill()
        if r is None:
            out[i] = dict(status=f"oracle-timeout-{a.cap}s-or-crash (exit {p.exitcode})")
        else:
            st = "ok" if all(k["status"] == "ok" for k in r) else "MISMATCH"
            out[i] = dict(status=st, kernels=r)
            bad += st != "ok"
        print(f"{i}: {out[i]['status']} "
              f"({len(out[i].get('kernels', []))} kernels, "
              f"{sum(k.get('events', 0) for k in out[i].get('kernels', []))} events)", flush=True)
        json.dump(out, open(a.out, "w"), indent=1)
    by = collections.Counter(v["status"].split(" ")[0] for v in out.values())
    print(f"{len(out)} programs: {dict(by)}; mismatching programs: {bad}")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("select")
    c = sp.add_parser("compare")
    c.add_argument("--store", required=True)
    c.add_argument("--ids", default=f"{HERE}/t5b_parity_ids.txt")
    c.add_argument("--out", required=True)
    c.add_argument("--cap", type=int, default=3600)
    c.add_argument("--shard", default="", help="k/N: every N-th id from the k-th")
    a = ap.parse_args()
    {"select": select, "compare": compare}[a.cmd](a)


if __name__ == "__main__":
    main()

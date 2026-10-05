#!/usr/bin/env python3
"""T15 (CLAUDE.md C/T15, eval/LATE_SEQ.md): the late ordering key, measured.

A dump recorded with YOSEMITE_HB_LATE_SEQ carries "hb_late_seq": 1 and, on every event, both
keys: "bpos" (its slot position in the kernel's buffer stream -- the order every earlier dump
used) and "lkey" (the key the committing lane drew as its callback's last action); "seq"
follows (lkey, bpos). One run therefore gives both orders.

  prep --out DIR K..   for each late-keyed kernel dump K: the W0 check under the late key (per
                       thread, lkey rises along bpos -- a thread's records are its program
                       order in buffer order), that seq is the (lkey, bpos) order, timer ties;
                       then writes DIR/<run>/<kernel>.json, the same dump in buffer order (seq
                       renumbered by bpos, the engine's fields dropped: the engine ran in late
                       order). a2_window_count.py handoffs then scores K (late order) and the
                       copies (buffer order) alike.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

ENGINE_FIELDS = ("hb_races", "hb_races_sync_only", "tv_violation", "hb_engine_stats")


def lanes_of(e):
    if "lanes" in e:
        return [ln["lane"] for ln in e["lanes"]]
    m = e.get("sync_mask", e.get("active_mask", 0)) if e["type"] == "syncwarp" else e.get("active_mask", 0)
    return [i for i in range(32) if m >> i & 1]


def check(t):
    ev = t["hb_events"]
    out = dict(events=len(ev), w0_threads=0, w0_violations=0, seq_order_ok=True, ties=0,
               key=t.get("hb_late_seq_key"), tv_violation=t.get("tv_violation"))
    by_seq = sorted(ev, key=lambda e: e["seq"])
    out["seq_order_ok"] = [(e["lkey"], e["bpos"]) for e in by_seq] == \
        sorted((e["lkey"], e["bpos"]) for e in ev)
    keys = sorted(e["lkey"] for e in ev)
    out["ties"] = sum(a == b for a, b in zip(keys, keys[1:]))
    per = defaultdict(list)
    for e in ev:
        for ln in lanes_of(e):
            per[(e["block"], e["warp"], ln)].append((e["bpos"], e["lkey"]))
    out["w0_threads"] = len(per)
    for recs in per.values():
        recs.sort()
        out["w0_violations"] += sum(b[1] < a[1] for a, b in zip(recs, recs[1:]))
    return out


def cmd_prep(a):
    tot = defaultdict(int)
    for kj in a.traces:
        t = json.load(open(kj))
        if not t.get("hb_late_seq"):
            print(f"{kj}: no hb_late_seq marker, skipped", flush=True)
            continue
        c = check(t)
        print(f"{kj}: {c}", flush=True)
        for k in ("events", "w0_threads", "w0_violations", "ties"):
            tot[k] += c[k]
        tot["seq_order_bad"] += not c["seq_order_ok"]
        tot["tv_violations"] += bool(c["tv_violation"])
        ev = sorted(t["hb_events"], key=lambda e: e["bpos"])
        for i, e in enumerate(ev):
            e["seq"] = i
        t["hb_events"] = ev
        for f in ENGINE_FIELDS:
            t.pop(f, None)
        t.pop("hb_late_seq", None)
        t["hb_buffer_order_of"] = os.path.abspath(kj)
        run = os.path.basename(os.path.dirname(os.path.abspath(kj)))
        d = os.path.join(a.out, run)
        os.makedirs(d, exist_ok=True)
        json.dump(t, open(os.path.join(d, os.path.basename(kj)), "w"))
    print("total", dict(tot))
    return 1 if tot["w0_violations"] or tot["seq_order_bad"] else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--out", required=True)
    p.add_argument("traces", nargs="+")
    a = ap.parse_args()
    sys.exit({"prep": cmd_prep}[a.cmd](a))


if __name__ == "__main__":
    main()

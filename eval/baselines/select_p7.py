#!/usr/bin/env python3
"""Select the P7 "10 largest-trace kernels" for the overhead comparison (X7).

After a P7 cuVein run, each P7 row's notes carry events=<len(hb_events)> (recorded
by parallel.py). This ranks the P7 programs by trace size and writes the top 10 to
eval/results/baselines-p7-selection.csv (id, events, native_wall). The overhead
table (make_tables.py) already uses all P7 rows; this file marks which 10 are the
largest-trace set the task asks for. CPU-only.

  .env/bin/python eval/baselines/select_p7.py
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RES = f"{os.path.dirname(os.path.dirname(HERE))}/eval/results"
_EV = re.compile(r"events=(\d+)")


def main():
    path = f"{RES}/baselines-cuvein.csv"
    if not os.path.exists(path):
        print("no cuvein CSV"); return
    best = {}   # id -> (events, native)
    for r in csv.DictReader(open(path)):
        if r["pset"] != "P7":
            continue
        m = _EV.search(r.get("notes", ""))
        ev = int(m.group(1)) if m else 0
        try:
            nat = float(r["native_wall_s"])
        except (ValueError, KeyError):
            nat = ""
        cur = best.get(r["id"], (0, nat))
        if ev >= cur[0]:
            best[r["id"]] = (ev, nat)
    ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:10]
    out = f"{RES}/baselines-p7-selection.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "id", "events", "native_wall_s"])
        for i, (pid, (ev, nat)) in enumerate(ranked, 1):
            w.writerow([i, pid, ev, nat])
    print(f"P7 top-{len(ranked)} largest-trace -> {out}")
    for i, (pid, (ev, nat)) in enumerate(ranked, 1):
        print(f"  {i:2d}. {pid}  events={ev}")


if __name__ == "__main__":
    main()

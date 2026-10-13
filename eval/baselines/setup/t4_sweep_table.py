#!/usr/bin/env python3
"""T4 step 4: the timeout set (setup/hb_clock_timeout_ids.txt) and the P7/P9 remainder
(setup/t4_p7p9_ids.txt) recorded under no-dump mode (BASELINE_HB_DUMP=0, YOSEMITE_HB_STATS=1;
eval/results/t4-nodump*/), against T5b's dump runs of the same programs (eval/results/
t5b-final-timeout/, both modes). Per program and mode: verdict, wall, peak RSS; and from the
kept no-dump dumps (--store, BeeGFS: compute nodes only) the sync instance's bucket term and
the vector clock's size at kernel end (hb_stats, max over the kernels), and the records the
dump would have held (hb_events_count, sum over the kernels).

    .env/bin/python eval/baselines/setup/t4_sweep_table.py [--tags t4-nodump,t4-nodump-p7p9]
        [--before t5b-final-timeout] [--store /mnt/beegfs/$USER/cuvein_traces/t4-nodump ...]
"""
import argparse
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
from t5b_sweep_table import category, short  # noqa: E402

MODES = ("vector-clock", "scalar-clock")


def load(tag):
    out = {}
    for p in sorted(glob.glob(f"{APH}/eval/results/{tag}/*.csv")):
        for r in csv.DictReader(open(p)):
            out[(r["id"], r["mode"])] = r
    return out


def cell(r):
    if not r:
        return "—"
    w = f"{float(r['wall_s']):.0f} s" if r.get("wall_s") not in (None, "") else "?"
    m = f"{float(r['peak_mb']) / 1024:.1f} GB" if r.get("peak_mb") not in (None, "") else "?"
    v = r["verdict"]
    if v == "RACE":
        v += f" {r.get('reports_dedup', '')}".rstrip()
    return f"{v} {w}, {m}"


def stats_of(store, _id, mode):
    """(max bucket bytes, max vc bytes, max vs bytes, sum hb_events_count, kernels) over the
    kept kernel JSONs of <store>/<id>/<mode>, from hb_stats; None without the store."""
    kjs = sorted(glob.glob(f"{store}/{_id}/{mode}/kernel_*.json")) if store else []
    if not kjs:
        return None
    bk = vc = vs = ev = 0
    for kj in kjs:
        try:
            t = json.load(open(kj))
        except (OSError, ValueError):
            continue
        hs = t.get("hb_stats") or {}
        hc = hs.get("hb_clock") or hs.get("engine") or {}
        bk = max(bk, (hc.get("buckets") or {}).get("bytes_est", 0))
        vc = max(vc, (hc.get("vc") or {}).get("bytes_est", 0))
        vs = max(vs, (hc.get("vs") or {}).get("bytes_est", 0))
        ev += int(t.get("hb_events_count") or (hs.get("hb_events") or {}).get("count", 0))
    return bk, vc, vs, ev, len(kjs)


def gb(b):
    return f"{b / 1e9:.2f}" if b >= 1e8 else f"{b / 1e6:.0f} MB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="t4-nodump,t4-nodump-p7p9")
    ap.add_argument("--before", default="t5b-final-timeout")
    ap.add_argument("--store", nargs="*", default=[])
    a = ap.parse_args()
    ids = [ln.strip() for ln in open(f"{HERE}/hb_clock_timeout_ids.txt") if ln.strip()]
    extra = [ln.strip() for ln in open(f"{HERE}/t4_p7p9_ids.txt") if ln.strip()] \
        if os.path.exists(f"{HERE}/t4_p7p9_ids.txt") else []
    before = load(a.before)
    after = {}
    for tag in a.tags.split(","):
        after.update(load(tag))

    def st(_id, mode):
        for s in a.store:
            r = stats_of(s, _id, mode)
            if r is not None:
                return r
        return None

    groups = {}
    for i in ids:
        groups.setdefault(category(i), []).append(i)
    print("| program | T5b dump vector-clock | T4 no-dump vector-clock | T5b dump scalar-clock | "
          "T4 no-dump scalar-clock | buckets VC / SC | vc / vs | records |")
    print("|---|---|---|---|---|---|---|---|")
    tot = {m: {"finished": 0, "under120": 0, "of": 0} for m in MODES}
    bar9 = {m: [] for m in MODES}
    for cat in ("barriers, no atomics", "atomics + barriers", "atomics only", "neither"):
        if cat not in groups:
            continue
        print(f"| **{cat}** ({len(groups[cat])}) | | | | | | | |")
        for i in groups[cat]:
            cells = []
            for m in MODES:
                b, n = before.get((i, m)), after.get((i, m))
                cells += [cell(b), cell(n)]
                if n:
                    tot[m]["of"] += 1
                    done = n["verdict"] in ("RACE", "CLEAN")
                    tot[m]["finished"] += done
                    tot[m]["under120"] += done and float(n["wall_s"] or 1e9) <= 120
                    if cat == "barriers, no atomics":
                        bar9[m].append((i, n["verdict"], n["wall_s"]))
            s = {m: st(i, m) for m in MODES}
            bk = " / ".join(gb(s[m][0]) if s[m] else "—" for m in MODES)
            cl = (f"{gb(s['vector-clock'][1])} / {gb(s['scalar-clock'][2])}"
                  if s["vector-clock"] and s["scalar-clock"] else "—")
            ev = s["vector-clock"][3] if s["vector-clock"] else (s["scalar-clock"][3] if s["scalar-clock"] else "—")
            print(f"| {short(i)} | " + " | ".join(cells) + f" | {bk} | {cl} | {ev:,} |"
                  if isinstance(ev, int) else f"| {short(i)} | " + " | ".join(cells) + f" | {bk} | {cl} | {ev} |")
    if extra:
        print(f"| **P7/P9 not in the timeout set** ({len(extra)}) | | | | | | | |")
        for i in extra:
            cells = []
            for m in MODES:
                cells += [cell(before.get((i, m))), cell(after.get((i, m)))]
            s = {m: st(i, m) for m in MODES}
            bk = " / ".join(gb(s[m][0]) if s[m] else "—" for m in MODES)
            print(f"| {i} | " + " | ".join(cells) + f" | {bk} | — | — |")
    print()
    for m in MODES:
        t = tot[m]
        print(f"{m}: {t['finished']} of {t['of']} finish (RACE/CLEAN), {t['under120']} under 120 s")
        print(f"  barrier-only programs: " + ", ".join(f"{i} {v} {w}s" for i, v, w in bar9[m]))


if __name__ == "__main__":
    main()

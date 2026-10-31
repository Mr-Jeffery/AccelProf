#!/usr/bin/env python3
"""C4 step 3: merge the re-analysis shard CSVs the way X1b merged its own (FINAL_SWEEP_B.md section 1 (i); p_final_b_post.sh):
the first pass (final-b: main + PI shards), overridden per (id, mode) by the 5,400 s pass (final-b-long-sc) and by the 84,600 s
pass (final-b-24h-sc) for the keys X1b kept (a 84,600 s row replaces the earlier rows of its (id, mode) when it reached RACE,
CLEAN or TIMEOUT; an ERROR leaves the earlier rows standing).  Both halves are merged:
  on   baselines-cuvein-shard*.csv     (barrier-ordered rule ON  = scalar-clock as X1b scored it)  -> merged/baselines-cuvein.csv
  off  baselines-cuvein-bo0-shard*.csv (rule OFF = CO-R)                                           -> merged/baselines-cuvein-bo0.csv
Runner-level rows without a mode (missing-exe) are X1b's own rows (the analysis only wrote `no-trace-collected` for them).
Also written: merged/baselines-cuvein-cor.csv = the OFF half's scalar-clock rows as mode `collector-only-rescored` (make_tables.py
--co-offline reads it), and the parity of the merged ON half against X1b's merged scalar-clock rows.
  co_merge.py > merged_report.md"""
import csv
import glob
import os
import sys

X = "/home/fzheng4/wt-x1b/eval/results"
M = "/home/fzheng4/wt-c4/eval/results/co-offline"
sys.path.insert(0, "/home/fzheng4/wt-c4/eval/baselines")
import blib  # noqa: E402

COLS = blib.COLUMNS


def load(d, pat):
    out = []
    for f in sorted(glob.glob(f"{d}/{pat}")):
        out += list(csv.DictReader(open(f, newline="")))
    return out


kept = {(r["id"], r["mode"]) for r in load(f"{X}/final-b-24h-kept-sc", "baselines-cuvein-shard*.csv")}
xm = list(csv.DictReader(open(f"{X}/final-b/merged/baselines-cuvein.csv", newline="")))
x_sc = [r for r in xm if r["mode"] == "scalar-clock"]
x_nomode = [r for r in xm if r["mode"] == ""]
os.makedirs(f"{M}/merged", exist_ok=True)
rep = []
P = rep.append
P("# C4 step 3: merged re-analysis\n")
dropped24 = []
for half, pat, out in (("on", "baselines-cuvein-shard*.csv", "baselines-cuvein.csv"), ("off", "baselines-cuvein-bo0-shard*.csv", "baselines-cuvein-bo0.csv")):
    base = [r for r in load(f"{M}/final-b", pat) if r["mode"] == "scalar-clock"]
    over = {}
    for r in load(f"{M}/final-b-long-sc", pat):
        if r["mode"] == "scalar-clock":
            over.setdefault((r["id"], r["mode"]), []).append(r)
    n_long = len(over)
    h24 = {}
    for r in load(f"{M}/final-b-24h-sc", pat):
        if r["mode"] == "scalar-clock":
            h24.setdefault((r["id"], r["mode"]), []).append(r)
    n24 = 0
    for k, rs in h24.items():
        if k in kept:
            over[k] = rs
            n24 += 1
        else:
            dropped24.append((half, k, sorted({x["verdict"] for x in rs})))
    for k in kept:                      # X1b kept it; the half must have a row
        if k not in h24:
            dropped24.append((half, k, ["no row in the 84,600 s re-analysis"]))
    rows = [r for r in base if (r["id"], r["mode"]) not in over]
    for k in sorted(over):
        rows += over[k]
    rows += x_nomode
    with open(f"{M}/merged/{out}", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    P(f"- half `{half}`: {len(base)} first-pass scalar-clock rows, {n_long} keys overridden by the 5,400 s pass, {n24} by the 84,600 s pass -> {len(rows)} rows in merged/{out}")
    if half == "off":
        with open(f"{M}/merged/baselines-cuvein-cor.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            for r in rows:
                if r["mode"] == "scalar-clock":
                    w.writerow({c: r.get(c, "") for c in COLS} | {"mode": "collector-only-rescored"})
    if half == "on":
        mine = {(r["id"], r["mode"], r["rep"]): r for r in rows if r["mode"] == "scalar-clock"}
        theirs = {(r["id"], r["mode"], r["rep"]): r for r in x_sc}
        diffs = []
        for k in sorted(set(mine) | set(theirs)):
            a, b = theirs.get(k), mine.get(k)
            if a is None or b is None:
                diffs.append((k, "row only in " + ("re-analysis" if a is None else "X1b")))
                continue
            for f in ("verdict", "reports_dedup", "report_ids", "report_lines"):
                if a[f] != b[f]:
                    diffs.append((k, f"{f}: X1b `{a[f][:120]}` vs `{b[f][:120]}`"))
        P(f"- parity of the merged ON half against X1b's merged scalar-clock rows: {len(theirs)} X1b rows, {len(mine)} re-analysis rows, **{len(diffs)} differences**")
        for k, d in diffs[:100]:
            P(f"  - {k}: {d}")
P(f"\nX1b's kept 84,600 s scalar-clock keys: {len(kept)}; keys of the 84,600 s re-analysis not taken, per half: {dropped24}")
print("\n".join(rep))

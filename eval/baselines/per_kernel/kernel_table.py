#!/usr/bin/env python3
"""X13 step 5: Table 4 per kernel from kernel_verdicts_{curace,baselines}.csv and labels.csv (make_tables.py --unit kernel).
Cell semantics as make_tables.confusion_b (TP/(TP+FN), FP/(FP+TN), TO/ERR counted apart), one level down: the unit is
(binary, kernel). A kernel whose label is GATE (tridiagonal, pending) is unlabelled."""
import collections, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kfold
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
D = f"{APH}/eval/results/per-kernel"
COLS = [("racecheck", ""), ("iguard", ""), ("hirace", ""), ("supercollider", ""),
        ("cuvein", "collector-only"), ("cuvein", "scalar-clock"), ("cuvein", "vector-clock")]
NAMES = ["racecheck", "iGUARD", "HiRace", "SuperCollider", "collector-only", "scalar-clock", "vector-clock"]
ROWS = [("Indigo3", "P1"), ("Indigo 1.3", "PI"), ("Indigo 1.3, SC's 99", "PI@sc7"), ("ScoR applications", "P4"),
        ("cuHadron (in scope; SuperCollider: all 34)", "P6@in"), ("HeCBench, SC's 10", "P9")]
ALL_VIEWS = ("P1", "PI", "P4", "P6@in")
SC_ALL = ("PI@sc7", "P6")

def load():
    lab = {}
    for r in csv.DictReader(open(f"{D}/labels.csv")):
        lab[(r["binary"], r["kernel"])] = {"RACE": "RACE", "CLEAN": "CLEAN"}.get(r["label"], "")
    ver = collections.defaultdict(dict)       # (tool, mode) -> {(binary, kernel): verdict}
    views = {}                                # (binary, kernel) -> set(views)
    for f in ("kernel_verdicts_curace.csv", "kernel_verdicts_baselines.csv"):
        for r in csv.DictReader(open(f"{D}/{f}")):
            bk = (r["binary"], r["kernel"])
            tm = (r["tool"], r["mode"])
            ver[tm][bk] = r["verdict"]
            views.setdefault(bk, set()).update(r["views"].split(";"))
    return lab, ver, views

def cell(c, rec):
    if not c["n"]:
        return "-"
    to = c["to"] + c["err"]
    s = f"{c['tp']}/{c['tp']+c['fn']}" if rec else f"{c['fp']}/{c['fp']+c['tn']}"
    return s + (f", {to} TO/ERR" if rec and to else "")

def build():
    lab, ver, views = load()
    # a kernel's views: the curace views (P6@in is a subset of P6)
    out = ["| suite | kind | racy / race-free / unlabelled kernels | " + " | ".join(NAMES) + " |", "|" + "---|" * (3 + len(NAMES))]
    tot = collections.defaultdict(collections.Counter)
    sc_tot = collections.Counter()
    cells = {}
    for name, v in ROWS:
        ks = [bk for bk in lab if v in views.get(bk, ())]
        nr = sum(1 for bk in ks if lab[bk] == "RACE"); nf = sum(1 for bk in ks if lab[bk] == "CLEAN"); nu = len(ks) - nr - nf
        rec, fp = [], []
        for tm in COLS:
            vv = ver.get(tm, {})
            kk = ks
            if tm == ("supercollider", "") and v == "P6@in":
                kk = [bk for bk in lab if "P6" in views.get(bk, ())]
            c = kfold.confusion_k(kk, lab, vv)
            cells[(v, tm)] = c
            rec.append(cell(c, True)); fp.append(cell(c, False))
            if v in ALL_VIEWS and tm != ("supercollider", ""):
                for k_, x in c.items(): tot[tm][k_] += x
        out.append(f"| {name} | recall | {nr} / {nf} / {nu} | " + " | ".join(rec) + " |")
        out.append("| | FP | | " + " | ".join(fp) + " |")
    # All: P1+PI+P4+P6@in for every tool; SuperCollider = its own suites (PI@sc7 + P6 all)
    for tm in COLS:
        if tm == ("supercollider", ""):
            tot[tm] = collections.Counter()
            for v in SC_ALL:
                ks = [bk for bk in lab if v in views.get(bk, ())]
                c = kfold.confusion_k(ks, lab, ver.get(tm, {}))
                for k_, x in c.items(): tot[tm][k_] += x
    nr = sum(1 for bk in lab if any(v in views.get(bk, ()) for v in ALL_VIEWS) and lab[bk] == "RACE")
    nf = sum(1 for bk in lab if any(v in views.get(bk, ()) for v in ALL_VIEWS) and lab[bk] == "CLEAN")
    out.append(f"| All (P1+PI+P4+P6@in) | recall | {nr} / {nf} / - | " + " | ".join(cell(dict(tot[tm]) if tot[tm] else dict(n=0), True) if tot[tm] else "-" for tm in COLS) + " |")
    out.append("| | FP | | " + " | ".join(cell(dict(tot[tm]), False) if tot[tm] else "-" for tm in COLS) + " |")
    return "\n".join(out), cells

def main(path=None):
    t, cells = build()
    with open(f"{D}/table4_kernel_cells.csv", "w", newline="") as f:      # one row per (view, tool, mode): the confusion counts behind the cells
        w = csv.writer(f); w.writerow(["view", "tool", "mode", "tp", "fn", "fp", "tn", "to", "err", "unl", "n", "labelled_racy", "labelled_race_free"])
        for (v, tm), c in sorted(cells.items()):
            w.writerow([v, tm[0], tm[1], c["tp"], c["fn"], c["fp"], c["tn"], c["to"], c["err"], c["unl"], c["n"], c["lab_r"], c["lab_c"]])
    path = path or f"{D}/table4_kernel.md"
    with open(path, "w") as f:
        f.write("# Table 4 per kernel (X13)\n\n" + t + "\n")
    print(t)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

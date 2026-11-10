#!/usr/bin/env python3
"""X13 step 0b: recompute every cell of cuRacePaper tables/coverage.tex (Table 4) from the CSVs.
Layers (later wins per (id, tool, mode)): top-level eval/results/baselines-*.csv; the X1b final-b merged cuVein
CSV (clock modes) unless --no-finalb; co-chain-b merged-s1 (collector-only); X11 sc_native/summary.csv (HeCBench P9).
Usage: gate_table4.py OUT.md [--unit run|binary]  (Indigo 1.3 rows are always per code = per binary, as in the paper)."""
import csv, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
out_path = sys.argv[1]
UNIT = sys.argv[sys.argv.index("--unit") + 1] if "--unit" in sys.argv else "run"
argv0 = sys.argv[:]; sys.argv = [argv0[0]]
sys.path.insert(0, os.path.join(APH, "eval", "baselines"))
import make_tables as mt
sys.argv = argv0
RES = mt.RES
VC, SC, CO = mt.VC, mt.SC, "collector-only"

def layer(runs, meta, path, tool_filter=None):
    r2, m2 = mt.load_runs([path], shards=True)
    n = 0
    for k, v in r2.items():
        if tool_filter and k[1:] != tool_filter and k[1] != tool_filter[0]:
            continue
        runs[k] = v; n += 1
    for k, v in m2.items():
        meta.setdefault(k, v)
    return n

runs, meta = mt.load_runs()
man = mt.load_manifest()
for _id, mm in list(meta.items()):
    if mm[0] == "PI" and _id in man and man[_id]["build"] != mm[2]:
        meta[_id] = (mm[0], mm[1], mm[2] if False else man[_id]["build"], mm[3])
notes = []
if "--finalb" in sys.argv:
    notes.append(("final-b merged", layer(runs, meta, f"{RES}/final-b/merged/baselines-cuvein.csv")))
# collector-only column
co_n = layer(runs, meta, f"{RES}/co-chain-b/merged-s1/baselines-cuvein.csv")
notes.append(("co-chain-b merged-s1", co_n))
# X11 HeCBench P9 (new_verdict)
p9 = {}
for r in csv.DictReader(open(f"{RES}/sc_native/summary.csv")):
    p9[(r["program"], r["tool"], r["mode"])] = r
ids9 = {m["program"]: i for i, m in man.items() if m["pset"] == "P9"}
TM = {"racecheck": ("racecheck", ""), "iguard": ("iguard", ""), "vector-clock": ("cuvein", VC),
      "scalar-clock": ("cuvein", SC), "collector-only": ("cuvein", CO)}
n9 = 0
for (prog, tool, mode), r in p9.items():
    if tool == "supercollider":
        continue
    i = ids9.get(prog + "-cuda")
    if not i:
        notes.append(("P9 id missing", prog)); continue
    key = (i,) + TM[tool]
    runs[key] = dict(runs.get(key, dict(reports=0, wall=None, native=None, peak=None, report_ids="", report_lines="", notes="")),
                     verdict={"TO": "TIMEOUT"}.get(r["new_verdict"], r["new_verdict"]))
    n9 += 1
notes.append(("X11 sc_native/summary.csv overlay rows", n9))
mt.add_sanitizer_union(runs)

COLS = [("racecheck", ""), ("iguard", ""), ("hirace", ""), ("supercollider", ""), ("cuvein", CO), ("cuvein", SC), ("cuvein", VC)]
NAMES = ["racecheck", "iGUARD", "HiRace", "SuperCollider", "collector-only", "scalar-clock", "vector-clock"]
ROWS = [("Indigo3", "P1", "run"), ("Indigo 1.3", "PI", "binary"), ("Indigo 1.3, SC's 99", "PI@sc7", "binary"),
        ("ScoR applications", "P4", "run"), ("cuHadron (20 in scope)", "P6@in", "run"), ("HeCBench, SC's 10", "P9", "run")]
def conf(view, unit, tool, mode):
    if unit == "binary" or UNIT == "binary":
        folded = mt.fold_binaries(runs, mt.binary_view_ids(meta, view), man, [(tool, mode)], meta)
        return mt.confusion_b(folded, tool, mode)[0]
    ids = mt.binary_view_ids(meta, view)
    sub = {i: meta[i] for i in ids}
    return mt.confusion(runs, sub, man, ("P6",) if view == "P6@in" else (view,), tool, mode)[0]
def cellstr(c, rec):
    if not c["n"]:
        return "-"
    to = c["to"] + c["err"]
    s = (f"{c['tp']}/{c['tp']+c['fn']}" if rec else f"{c['fp']}/{c['fp']+c['tn']}")
    return s + (f", {to} TO/ERR" if to and rec else "")
lines = ["# Table 4 recomputed (unit: %s; Indigo 1.3 rows per code)\n" % UNIT, "layers: " + repr(notes), "",
         "| suite | kind | labels (racy/free/unl) | " + " | ".join(NAMES) + " |", "|" + "---|" * (3 + len(NAMES))]
tot = collections.defaultdict(lambda: collections.Counter())
for name, view, unit in ROWS:
    cs = {}
    for t, m in COLS:
        v = view
        if t == "supercollider" and view == "P6@in":
            v = "P6"
        cs[(t, m)] = conf(v, unit, t, m)
    base = next(c for c in cs.values() if c["n"])
    lab = f"{base['lab_r']}/{base['lab_c']}"
    lines.append(f"| {name} | recall | {lab} | " + " | ".join(cellstr(cs[c], True) for c in COLS) + " |")
    lines.append(f"| | FP | | " + " | ".join(cellstr(cs[c], False) for c in COLS) + " |")
    if view in ("P1", "PI", "P4", "P6@in"):
        for c in COLS:
            for k, x in cs[c].items():
                tot[c][k] += x
    if view == "P6@in":   # SC: all 34 cuHadron, own suites
        pass
lines.append("| All (P1+PI+P4+P6@in) | recall | | " + " | ".join(cellstr(tot[c], True) for c in COLS) + " |")
lines.append("| | FP | | " + " | ".join(cellstr(tot[c], False) for c in COLS) + " |")
open(out_path, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

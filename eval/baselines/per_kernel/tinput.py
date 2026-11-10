"""X13: the runs behind Table 4 (same layering as gate_table4.py): top-level CSVs, X1b final-b merged, co-chain-b merged-s1
(collector-only), X11 sc_native/summary.csv (HeCBench). Returns (mt, runs, meta, man, p9)."""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
_argv = sys.argv[:]; sys.argv = [_argv[0]]
sys.path.insert(0, os.path.join(APH, "eval", "baselines"))
import make_tables as mt
sys.argv = _argv
RES = mt.RES
VC, SC, CO = mt.VC, mt.SC, "collector-only"
TM = {"racecheck": ("racecheck", ""), "iguard": ("iguard", ""), "vector-clock": ("cuvein", VC),
      "scalar-clock": ("cuvein", SC), "collector-only": ("cuvein", CO)}

def load():
    runs, meta = mt.load_runs()
    man = mt.load_manifest()
    for _id, mm in list(meta.items()):
        if mm[0] == "PI" and _id in man and man[_id]["build"] != mm[2]:
            meta[_id] = (mm[0], mm[1], man[_id]["build"], mm[3])
    for p in (f"{RES}/final-b/merged/baselines-cuvein.csv", f"{RES}/co-chain-b/merged-s1/baselines-cuvein.csv"):
        r2, m2 = mt.load_runs([p], shards=True)
        runs.update(r2)
        for k, v in m2.items():
            meta.setdefault(k, v)
    ids9 = {m["program"]: i for i, m in man.items() if m["pset"] == "P9"}
    p9 = {}
    for r in csv.DictReader(open(f"{RES}/sc_native/summary.csv")):
        p9[(r["program"], r["tool"])] = r
        if r["tool"] == "supercollider":
            continue
        i = ids9[r["program"] + "-cuda"]
        key = (i,) + TM[r["tool"]]
        runs[key] = dict(runs.get(key, dict(reports=0, wall=None, native=None, peak=None, report_ids="", report_lines="", notes="")),
                         verdict={"TO": "TIMEOUT"}.get(r["new_verdict"], r["new_verdict"]))
    mt.add_sanitizer_union(runs)
    return mt, runs, meta, man, p9

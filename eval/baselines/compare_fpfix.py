#!/usr/bin/env python3
"""Before/after accuracy of a detector revision's re-run vs the merged baseline.

before = eval/results/baselines-cuvein.csv (the merged head-to-head run; --before also
         takes a glob of shard csvs, e.g. an `analyze` pass with the new rules switched off)
after  = eval/results/fpfix/baselines-cuvein-shard*.csv (setup/p_fpfix.sh)

Per (program, mode) the verdict is RACE if any rep reported RACE, else CLEAN if any
rep was CLEAN, else TIMEOUT/ERROR — the same reduction make_tables.py uses. Prints
FP/TN/TP/FN/err per program set and mode for both runs, restricted to the programs
the re-run covers, then lists every program whose verdict changed the wrong way
(TP lost, new FP) and the remaining FPs. No GPU needed.
"""
import argparse
import collections
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
RES = f"{APH}/eval/results"
PRI = {"RACE": 3, "CLEAN": 2, "TIMEOUT": 1, "ERROR": 0}

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "python"))
import hb_modes  # noqa: E402  (vector-clock / scalar-clock; legacy names accepted with a warning)


def _rank(mode):
    """harness order: vector-clock, then scalar-clock (keeps the pre-T8 row order)"""
    return hb_modes.MODES.index(mode) if mode in hb_modes.MODES else len(hb_modes.MODES)


def effective_verdict(r):
    """A cuVein CLEAN needs a run that reached its own exit: accelprof returns 1 when
    the app dies under the tool (OOM-killed engine run) while the kernels dumped before
    that still parse, so rows written before parallel.py flagged this
    (incomplete-trace) can say CLEAN over a prefix of the run. Re-score them ERROR.
    rc 127 is exempt: the pre-fix bin/accelprof returned it after a SUCCESSFUL run."""
    if ((r.get("tool") or "cuvein") == "cuvein" and r.get("verdict") == "CLEAN"
            and str(r.get("rc", "")).strip() not in ("", "0", "127")):
        return "ERROR"
    return r.get("verdict")


def reduce_rows(paths):
    best = {}
    for p in paths:
        for r in csv.DictReader(open(p, newline="")):
            if r.get("tool", "cuvein") != "cuvein" or not r.get("mode"):
                continue
            k, v = (r["id"], hb_modes.canon(r["mode"], p)), effective_verdict(r)
            if k not in best or PRI.get(v, -1) > PRI.get(best[k], -1):
                best[k] = v
    return best


def tally(verdicts, man, keys):
    t = collections.defaultdict(lambda: collections.Counter())
    for (i, mode) in keys:
        v, lab = verdicts.get((i, mode)), man[i]["label"]
        cell = t[(man[i]["pset"], mode)]
        if v in (None, "ERROR", "TIMEOUT"):
            cell["err"] += 1
        elif lab == "CLEAN":
            cell["FP" if v == "RACE" else "TN"] += 1
        elif lab == "RACE":
            cell["TP" if v == "RACE" else "FN"] += 1
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--before", default=f"{RES}/baselines-cuvein.csv")
    ap.add_argument("--after-glob", default=f"{RES}/fpfix/baselines-cuvein-shard*.csv")
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    a = ap.parse_args()
    man = {r["id"]: r for r in csv.DictReader(open(a.manifest))}
    before = reduce_rows(sorted(glob.glob(a.before)) or [a.before])   # file or glob
    after = reduce_rows(sorted(glob.glob(a.after_glob)))
    keys = sorted((k for k in after if k[0] in man), key=lambda k: (k[0], _rank(k[1])))
    tb, ta = tally(before, man, keys), tally(after, man, keys)

    print(f"{len({k[0] for k in keys})} programs re-run\n")
    print("| pset | mode | FP before | FP after | TP before | TP after | err before | err after |")
    print("|---|---|---|---|---|---|---|---|")
    for cell in sorted(set(tb) | set(ta), key=lambda c: (c[0], _rank(c[1]))):
        b, x = tb[cell], ta[cell]
        print(f"| {cell[0]} | {cell[1]} | {b['FP']}/{b['FP'] + b['TN']} | "
              f"{x['FP']}/{x['FP'] + x['TN']} | {b['TP']}/{b['TP'] + b['FN']} | "
              f"{x['TP']}/{x['TP'] + x['FN']} | {b['err']} | {x['err']} |")

    lost = [k for k in keys if man[k[0]]["label"] == "RACE"
            and before.get(k) == "RACE" and after[k] == "CLEAN"]
    newfp = [k for k in keys if man[k[0]]["label"] == "CLEAN"
             and before.get(k) == "CLEAN" and after[k] == "RACE"]
    stillfp = [k for k in keys if man[k[0]]["label"] == "CLEAN" and after[k] == "RACE"]
    for title, ks in (("TRUE POSITIVES LOST (RACE -> CLEAN)", lost),
                      ("NEW FALSE POSITIVES (CLEAN -> RACE)", newfp),
                      ("remaining false positives", stillfp)):
        print(f"\n{title}: {len(ks)}")
        for i, mode in ks:
            print(f"  {mode:12s} {i}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Derive the cuVein follow-up id lists from the merged run rows, so the keep and
diagnose stages (p_keep.sh, p_diagnose.sh) follow whichever detector revision the
sweep just used. Same definitions the original hand-built lists encoded:

  keep_all_ids.txt  = label != verdict in either mode (FP/FN) + engine TIMEOUT/ERROR
  residual_ids.txt  = trace-only TIMEOUT/ERROR + every P7 (overhead) program

Rows whose only failure is `missing-exe` (arch-excluded cuHadron targets) are left
out: nothing to re-collect. Reads eval/results/baselines-cuvein.csv + manifest.csv,
writes eval/baselines/setup/{keep_all_ids,residual_ids,engine_timeout_ids}.txt and
prints the counts (used by run_rerun.sh to size the diagnose array).
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.abspath(f"{HERE}/../../..")
RES = f"{APH}/eval/results"


def reduce(verds):
    for v in ("RACE", "CLEAN", "TIMEOUT"):
        if v in verds:
            return v
    return "ERROR" if verds else ""


def main():
    man = {r["id"]: r for r in csv.DictReader(open(f"{HERE}/../manifest.csv", newline=""))}
    per = defaultdict(set)
    notes = defaultdict(set)
    for r in csv.DictReader(open(f"{RES}/baselines-cuvein.csv", newline="")):
        per[(r["id"], r["mode"])].add(r["verdict"])
        notes[r["id"]].add(r.get("notes", ""))
    ids = sorted({i for i, _ in per})
    keep, eng_fail, resid = [], [], []
    for i in ids:
        if all(n == "missing-exe" for n in notes[i]):
            continue
        lab = man.get(i, {}).get("label", "")
        e = reduce(per.get((i, "engine"), set()))
        t = reduce(per.get((i, "trace-only"), set()))
        wrong = any(v in ("RACE", "CLEAN") and v != lab for v in (e, t)) if lab in ("RACE", "CLEAN") else False
        if wrong:
            keep.append(i)
        if e in ("TIMEOUT", "ERROR"):
            eng_fail.append(i)
        if t in ("TIMEOUT", "ERROR") or man.get(i, {}).get("pset") == "P7":
            resid.append(i)
    keep_all = sorted(set(keep) | set(eng_fail))
    for name, lst in (("keep_all_ids.txt", keep_all), ("engine_timeout_ids.txt", eng_fail),
                      ("residual_ids.txt", resid)):
        with open(f"{HERE}/{name}", "w") as f:
            f.write("\n".join(lst) + ("\n" if lst else ""))
    print(f"keep_all={len(keep_all)} (mismatch={len(keep)}, engine-fail={len(eng_fail)}) residual={len(resid)}")


if __name__ == "__main__":
    main()

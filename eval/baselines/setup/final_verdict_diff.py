#!/usr/bin/env python3
"""X1 step 5(b): the final recording against the T20 parity recording, per (id, mode).

  .env/bin/python eval/baselines/setup/final_verdict_diff.py \
      --final eval/results/baselines-cuvein.csv --parity 'eval/results/x0-default/*.csv' \
      --ids eval/baselines/setup/t5b_parity_ids.txt [--rep1-csv eval/results/final/parity_rep1.csv]

The parity side is the T20 parity store (cuvein_traces/t20-parity2: the 65 programs of
setup/t5b_parity_ids.txt, both modes, one rep, 120 s floor, lossless dump) re-scored by X0 with
the aggregates default (eval/results/x0-default, AGGREGATES_DEFAULT.md section 3): the same verdict
code as the final recording, a different recording. Both sides are collapsed per (id, mode) the way
make_tables.load_runs does (any RACE > any CLEAN > TIMEOUT > ERROR). Every differing verdict gets a
cause:
  cap             the parity row is TIMEOUT (timeout <= 1,200 s there; the final cap is 1,200 /
                  5,400 s) and the final row has a verdict, or the reverse with the final row's
                  cap below the parity row's timeout
  schedule        RACE vs CLEAN where every report the RACE side has and the other lacks is
                  A2-flagged (a2_uncertain) or latent -- a hand-off or barrier order the run
                  happened to take -- per the confirmation details of both sides
  other           anything else: a stop (X1 brief)
Report-set differences on equal verdicts are counted and listed (not a verdict difference).
--rep1-csv writes the final rows of the parity ids, rep 1 only, for the literal
verdict_diff.py run against the parity CSVs.
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict

PRI = ("RACE", "CLEAN", "TIMEOUT", "ERROR")


def load(paths, ids):
    per = defaultdict(list)
    for p in paths:
        for r in csv.DictReader(open(p, newline="")):
            if r["id"] in ids and r.get("mode"):
                per[(r["id"], r["mode"])].append(r)
    out = {}
    for k, reps in per.items():
        vs = [r["verdict"] for r in reps]
        v = next(x for x in PRI if x in vs) if any(x in vs for x in PRI) else vs[0]
        rids = set()
        for r in reps:
            if r["verdict"] == "RACE":
                rids |= set((r.get("report_ids") or "").split())
        out[k] = dict(verdict=v, reports=rids, notes=";".join(sorted({r["notes"] for r in reps})),
                      reps=reps)
    return out


def _cap(notes, default):
    m = re.search(r"cap=(\d+)", notes or "")
    return int(m.group(1)) if m else default


def _timeout(notes):
    m = re.findall(r"timeout=(\d+)s", notes or "")
    return max(int(x) for x in m) if m else None


def _detail(conf_dir, i, mode):
    f = f"{conf_dir}/{i}__cuvein__{mode}.json" if conf_dir else ""
    if f and os.path.exists(f):
        try:
            return json.load(open(f))
        except (OSError, ValueError):
            return None
    return None


def _soft(raw_entry):
    """a report that rests on this run's schedule: A2-flagged or latent"""
    return raw_entry.get("a2") in ("race", "both") or raw_entry.get("matrix_class") == "latent"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", required=True)
    ap.add_argument("--parity", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--final-confirm", default="")
    ap.add_argument("--parity-confirm", default="")
    ap.add_argument("--rep1-csv", default="")
    a = ap.parse_args()
    ids = {l.strip() for l in open(a.ids) if l.strip() and not l.startswith("#")}
    fin = load([a.final], ids)
    par = load(sorted(glob.glob(a.parity)), ids)
    if a.rep1_csv:
        with open(a.rep1_csv, "w", newline="") as fh:
            w = None
            for k in sorted(fin):
                for r in fin[k]["reps"]:
                    if r.get("rep") == "1":
                        if w is None:
                            w = csv.DictWriter(fh, fieldnames=list(r.keys()))
                            w.writeheader()
                        w.writerow(r)
    keys = sorted(set(fin) | set(par))
    n_same = n_rep = 0
    diffs, repdiffs = [], []
    for k in keys:
        f, p = fin.get(k), par.get(k)
        if not f or not p:
            diffs.append((k, f and f["verdict"], p and p["verdict"], "missing-one-side", ""))
            continue
        if f["verdict"] == p["verdict"]:
            n_same += 1
            if f["verdict"] == "RACE" and f["reports"] != p["reports"]:
                n_rep += 1
                repdiffs.append((k, sorted(f["reports"] - p["reports"]), sorted(p["reports"] - f["reports"])))
            continue
        fv, pv = f["verdict"], p["verdict"]
        cause, why = "other", ""
        if pv == "TIMEOUT" and fv in ("RACE", "CLEAN"):
            cause, why = "cap", f"parity timeout={_timeout(p['notes'])}s, final cap={_cap(f['notes'], 1200)}s"
        elif fv == "TIMEOUT" and pv in ("RACE", "CLEAN"):
            pt = _timeout(p["notes"]) or 0
            fc = _cap(f["notes"], 1200)
            cause = "cap" if fc < pt else "other"
            why = f"final TIMEOUT at cap {fc}s; parity finished (wall {p['reps'][0].get('wall_s')}s, its timeout {pt}s)"
        elif {fv, pv} == {"RACE", "CLEAN"}:
            racy = f if fv == "RACE" else p
            dconf = a.final_confirm if fv == "RACE" else a.parity_confirm
            d = _detail(dconf, *k)
            extra = racy["reports"] - (p if fv == "RACE" else f)["reports"]
            if d is not None:
                soft = {f"{e['space']}:{hex(e['a_pc'])}-{hex(e['b_pc'])}:{e.get('race_type', '')}"
                        for e in d.get("raw", []) if _soft(e)}
                if extra and extra <= soft:
                    cause = "schedule"
                why = f"RACE side ({'final' if fv == 'RACE' else 'parity'}) extra reports {sorted(extra)}; " \
                      f"A2-flagged/latent among them: {sorted(extra & soft)}"
            else:
                why = f"no confirmation detail for the RACE side; extra reports {sorted(extra)}"
        diffs.append((k, fv, pv, cause, why))
    print(f"(id, mode) keys: final {len(fin)}, parity {len(par)}; same verdict {n_same} "
          f"(of which RACE with a different report set: {n_rep}); differing {len(diffs)}")
    for k, fv, pv, cause, why in diffs:
        print(f"  DIFF {k[0]} {k[1]}: final {fv} vs parity {pv} -> {cause}  {why}")
    for k, plus, minus in repdiffs:
        print(f"  REPORTS {k[0]} {k[1]}: final-only {plus} parity-only {minus}")
    others = [d for d in diffs if d[3] not in ("cap", "schedule")]
    print(f"causes: " + ", ".join(f"{c} {sum(1 for d in diffs if d[3] == c)}"
                                  for c in ("cap", "schedule", "other", "missing-one-side")))
    raise SystemExit(1 if others else 0)


if __name__ == "__main__":
    main()

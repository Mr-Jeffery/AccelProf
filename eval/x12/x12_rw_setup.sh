#!/usr/bin/env bash
# X12 real-world scoring setup: harness copies (chain = C6's c6rw copies; std = the same with the two chain edits reverted)
# and the per-id CSVs rw_score.py reads, cut from the N=16 analyses (prefiltered re-analysis; recording-job row if that ended ERROR).
set -eu
X=$HOME/x12rw; R=$HOME/wt/x12/eval/results; PY=$HOME/AccelProf/.env/bin/python
for m in chain std; do for s in t21b t21c; do
  mkdir -p $X/$m; rm -rf $X/$m/$s; cp -r $HOME/c6rw/$s $X/$m/$s
  f=$X/$m/$s/eval/realworld/harness/rw_attribute.py
  if [ $m = std ]; then
    sed -i 's/rep = sd.analyze(dot, kj, chain_closure=True)/rep = sd.analyze(dot, kj)/' $f
    sed -i 's/ chain_src=("chain" if v.get("chain") else ("chain_rescue" if v.get("chain_rescue") else "edge")), chain_path=v.get("chain_path"),//' $f
  fi
  echo $m $s $(grep -c "chain_closure=True" $f) $(grep -c "chain_src" $f)
done; done
$PY - <<PYEOF
import csv, glob, collections, re, os
csv.field_size_limit(1 << 30)
R = "$R"; X = "$X"
rec = {}
for f in glob.glob(f"{R}/co-sharded-rw/*/baselines*.csv"):
    for r in csv.DictReader(open(f, newline="")): rec[r["id"]] = r
for m in ("std", "chain"):
    for setn, dst in (("recall", "realworld"), ("cand", "realworld_t21c")):
        os.makedirs(f"{X}/{m}/res/{dst}/attrib", exist_ok=True)
        rows = {}
        for f in glob.glob(f"{R}/co-sharded-rw-an-{setn}-{m}/chain/baselines*.csv"):
            for r in csv.DictReader(open(f, newline="")): rows[r["id"]] = r
        flds = list(next(iter(rows.values())).keys())
        cmds = []
        for i, r in rows.items():
            if r["verdict"] == "ERROR" and m == "std" and rec[i]["verdict"] in ("RACE", "CLEAN"):
                r = {k: rec[i].get(k, "") for k in flds}; print("std: recording-job row used for", i)
            with open(f"{X}/{m}/res/{dst}/baselines-cuvein-shard{i}-all.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, flds); w.writeheader(); w.writerow(r)
            if r["verdict"] in ("RACE", "CLEAN"):
                a = re.search(r"analysis_s=([0-9.]+)", r["notes"]); cmds.append((float(a.group(1)) if a else 0, i))
        with open(f"{X}/{m}/{setn}.cmds", "w") as fh:
            for a, i in sorted(cmds, reverse=True): fh.write(i + "\n")
        print(m, setn, len(rows), "rows", len(cmds), "to attribute")
PYEOF

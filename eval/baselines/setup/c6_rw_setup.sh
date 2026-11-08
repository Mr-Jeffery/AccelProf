#!/usr/bin/env bash
# C6 step 3, real-world: harness copies (as C4's p_co_rw.sh: copies of the branches that produced the recall tables, rw_attribute.py /
# rw_score.py with RW_MODES from C4's rw_t21b / rw_t21c), plus the two edits this mode needs in rw_attribute.py:
#   sd.analyze(dot, kj) -> sd.analyze(dot, kj, chain_closure=True)      (the verdict step with the closure)
#   every report record gains chain_src (edge | chain_rescue | chain) and chain_path
# and the per-id CSVs rw_score.py reads (baselines-cuvein-shard<id>-all.csv), cut from the step-2 merged CSVs.
set -u
. /home/fzheng4/c6-step3/env.sh
RWH=/home/fzheng4/c6rw; RWR=$S3/rw; N=$W/eval/results/co-chain
mkdir -p $RWH/t21b $RWH/t21c $RWR/realworld/attrib $RWR/realworld_t21c/attrib
git -C $W archive origin/study/realworld-recall eval/realworld eval/baselines | tar -x -C $RWH/t21b
git -C $W archive origin/study/realworld-candidates eval/realworld eval/baselines | tar -x -C $RWH/t21c
for s in t21b t21c; do
  for f in rw_attribute.py rw_score.py; do
    git -C $W show eval/co-offline:eval/baselines/setup/co_offline/rw_$s/$f > $RWH/$s/eval/realworld/harness/$f || exit 1
  done
  f=$RWH/$s/eval/realworld/harness/rw_attribute.py
  sed -i 's/rep = sd.analyze(dot, kj)/rep = sd.analyze(dot, kj, chain_closure=True)/' $f
  sed -i 's/model_bug=kk in mbug,/model_bug=kk in mbug, chain_src=("chain" if v.get("chain") else ("chain_rescue" if v.get("chain_rescue") else "edge")), chain_path=v.get("chain_path"),/' $f
  grep -c "chain_closure=True" $f; grep -c "chain_src" $f
done
$PY - <<PYEOF
import csv, collections
for src, dst in (("$N/merged-c2-recall/baselines-cuvein.csv", "$RWR/realworld"), ("$N/merged-c2-cand/baselines-cuvein.csv", "$RWR/realworld_t21c")):
    rows = list(csv.DictReader(open(src, newline="")))
    flds = list(rows[0].keys())
    by = collections.defaultdict(list)
    for r in rows:
        by[r["id"]].append(r)
    for i, rs in by.items():
        with open(f"{dst}/baselines-cuvein-shard{i}-all.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, flds); w.writeheader(); w.writerows(rs)
    print(dst, len(by), "ids")
PYEOF
du -sh $RWH

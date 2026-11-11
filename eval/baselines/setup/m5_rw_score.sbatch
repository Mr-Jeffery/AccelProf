#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 01:00:00
#SBATCH -J m5-rw-score
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/rw-score-%j.log
# M5: C6's rw_score.py over the attributions of m5_rw_attr.sbatch (sw1, sw0), with per-id CSVs cut from this branch's production merged CSVs
# (as C6's c6_rw_setup.sh did from merged-c2-recall / merged-c2-cand).
W=/home/fzheng4/wt-m5; PY=/home/fzheng4/AccelProf/.env/bin/python; RWH=/home/fzheng4/m5rw; R=$W/eval/results/closure-atomic-hop
cd $W
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W RW_MODES=collector-only
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) $(date -Is)"
for sw in 1 0; do
$PY - <<PYEOF
import csv, collections
for tag, dst in (("c2-recall", "$R/rw/sw$sw/realworld"), ("c2-cand", "$R/rw/sw$sw/realworld_t21c")):
    rows = list(csv.DictReader(open("$R/prod/sw$sw/merged-%s/baselines-cuvein.csv" % tag, newline="")))
    flds = list(rows[0].keys()); by = collections.defaultdict(list)
    for r in rows: by[r["id"]].append(r)
    for i, rs in by.items():
        with open(f"{dst}/baselines-cuvein-shard{i}-all.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, flds); w.writeheader(); w.writerows(rs)
    print(dst, len(by), "ids")
PYEOF
$PY $RWH/t21b/eval/realworld/harness/rw_score.py --results $R/rw/sw$sw/realworld --manifest $W/eval/realworld/manifest_t21b.csv --pairs $RWH/t21b/eval/realworld/recall_pairs.json --write > $R/rw/sw$sw/score_t21b.out 2>&1; echo "score t21b sw$sw rc=$?"
$PY $RWH/t21c/eval/realworld/harness/rw_score.py --results $R/rw/sw$sw/realworld_t21c --manifest $W/eval/realworld/manifest_t21c.csv --pairs $RWH/t21c/eval/realworld/recall_pairs.json --exclude lightgbm-new-1,lightgbm-new-2,llamacpp-open-2 --write > $R/rw/sw$sw/score_t21c.out 2>&1; echo "score t21c sw$sw rc=$?"
done
echo end

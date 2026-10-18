#!/bin/bash
# X5 byte pairs: the counterfactual on merged traces (x5b_cf_merged.py), 8 shards on one node.
#   sbatch eval/baselines/setup/p_x5b_cfm.sh
#SBATCH -p normal
#SBATCH -J x5b-cfm
#SBATCH -t 02:00:00
#SBATCH -N 1
#SBATCH -c 8
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-cfm-%j.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
PY=${RT:-/home/fzheng4/AccelProf}/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD
R=eval/results/x5b
for I in $(seq 0 7); do
  $PY eval/baselines/setup/x5b_cf_merged.py --pairs $R/byte_pairs.jsonl --out $R/cf_merged_$I.jsonl \
      --shard $I/8 > eval/x_logs/x5b-cfm-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
cat $R/cf_merged_{0..7}.jsonl > $R/cf_merged.jsonl
echo "rows $(wc -l < $R/cf_merged.jsonl); tracebacks $(grep -l Traceback eval/x_logs/x5b-cfm-${SLURM_JOB_ID}-*.log | wc -l)"
cat eval/x_logs/x5b-cfm-${SLURM_JOB_ID}-*.log | grep -v "^rows"
echo "done $(date -Is)"

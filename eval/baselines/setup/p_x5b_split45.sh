#!/bin/bash
# X5 byte pairs: the rows of shards 4 and 5 of p_x5b_run.sh (the 1296-node inputs) in 16 pieces.
# Rows i with i % 8 == S are rows[S + 8*J :: 64] for J = 0..7.
#   sbatch eval/baselines/setup/p_x5b_split45.sh
#SBATCH -p normal
#SBATCH -J x5b-split
#SBATCH -t 04:00:00
#SBATCH -c 1
#SBATCH --array=0-15
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-split-%A_%a.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
I=${SLURM_ARRAY_TASK_ID:-0}
S=$((4 + I / 8)); J=$((I % 8)); SI=$((S + 8 * J))
echo "node $(hostname) job ${SLURM_JOB_ID} shard $S piece $J (rows $SI::64) $(date -Is)"; git rev-parse HEAD
mkdir -p eval/results/x5b
$PY eval/baselines/setup/x5b_byte_pairs.py --pairs eval/results/x5/barrier_ordered_pairs.csv \
    --out eval/results/x5b/byte_pairs_sub${S}_${J}.jsonl --shard $SI/64
echo "done $(date -Is)"

#!/bin/bash
# X5 byte pairs: the mechanism behind X5's `other` bin, one record per pair and mode, in 8 shards.
#   sbatch eval/baselines/setup/p_x5b_run.sh
#   then: cat eval/results/x5b/byte_pairs_shard*.jsonl > eval/results/x5b/byte_pairs.jsonl
#SBATCH -p normal
#SBATCH -J x5b-run
#SBATCH -t 04:00:00
#SBATCH -c 1
#SBATCH --array=0-7
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-run-%A_%a.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
I=${SLURM_ARRAY_TASK_ID:-0}
echo "node $(hostname) job ${SLURM_JOB_ID} shard $I $(date -Is)"; git rev-parse HEAD
mkdir -p eval/results/x5b
$PY eval/baselines/setup/x5b_byte_pairs.py --pairs eval/results/x5/barrier_ordered_pairs.csv \
    --out eval/results/x5b/byte_pairs_shard$I.jsonl --shard $I/8
echo "done $(date -Is)"

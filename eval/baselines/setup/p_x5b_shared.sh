#!/bin/bash
# X5 byte pairs: every row with --shared-only (the oracle replays drop the global records; the full
# replay of the 1296-node ECL-CC traces was OOM-killed at 94-120 GB in job 314529) and with the
# instance check: 16 shards (rows i::16) as parallel processes on one node, plus the P6 store survey.
# The full-replay records of p_x5b_run.sh / p_x5b_split45.sh are the reference p_x5b_report.sh
# compares these with.
#   sbatch eval/baselines/setup/p_x5b_shared.sh
#SBATCH -p normal
#SBATCH -J x5b-shared
#SBATCH -t 06:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-shared-%j.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD; free -g | head -2
mkdir -p eval/results/x5b
S=eval/baselines/setup
$PY -I $S/x5b_p6_stores.py > eval/x_logs/x5b-p6-stores-${SLURM_JOB_ID}.log 2>&1 &
for I in $(seq 0 15); do
  $PY $S/x5b_byte_pairs.py --pairs eval/results/x5/barrier_ordered_pairs.csv \
      --out eval/results/x5b/byte_pairs_so_$I.jsonl --shard $I/16 --shared-only \
      > eval/x_logs/x5b-shared-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
for I in $(seq 0 15); do
  echo "shard $I rows $(wc -l < eval/results/x5b/byte_pairs_so_$I.jsonl) $(grep -c Traceback eval/x_logs/x5b-shared-${SLURM_JOB_ID}-$I.log) tracebacks"
done
echo "done $(date -Is)"

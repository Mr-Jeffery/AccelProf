#!/bin/bash
# X5 byte pairs: syncwarp records of diverged warps (x5b_partial.py) over the events stores of the
# byte-pair rows, 16 shards as parallel processes on one node.
#   sbatch eval/baselines/setup/p_x5b_partial.sh
#SBATCH -p normal
#SBATCH -J x5b-partial
#SBATCH -t 04:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-partial-%j.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD
S=eval/baselines/setup
R=eval/results/x5b
for I in $(seq 0 15); do
  $PY $S/x5b_partial.py --pairs $R/byte_pairs.jsonl --out $R/partial_$I.jsonl --shard $I/16 \
      > eval/x_logs/x5b-partial-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
cat $R/partial_{0..15}.jsonl > $R/partial.jsonl
echo "groups $(wc -l < $R/partial.jsonl); tracebacks $(grep -l Traceback eval/x_logs/x5b-partial-${SLURM_JOB_ID}-*.log | wc -l)"
echo "done $(date -Is)"

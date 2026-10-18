#!/bin/bash
# X5 byte pairs: merge the outputs and write the tables.
#   full replays: shards 0-3, 6, 7 of p_x5b_run.sh and the pieces of p_x5b_split45.sh that
#   finished (shards 4 and 5 were cancelled and redone there); shared-only replays: p_x5b_shared.sh
#   sbatch eval/baselines/setup/p_x5b_report.sh
#SBATCH -p normal
#SBATCH -J x5b-report
#SBATCH -t 00:20:00
#SBATCH -c 1
#SBATCH -o /home/fzheng4/wt-x5-byte-pairs/eval/x_logs/x5b-report-%j.log
W=${W:-/home/fzheng4/wt-x5-byte-pairs}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD
R=eval/results/x5b
S=eval/baselines/setup
$PY $S/x5b_merge.py --full "$R/byte_pairs_s[hu][ab]*.jsonl" --shared "$R/byte_pairs_so_*.jsonl" \
    --out $R/byte_pairs.jsonl --check $R/shared_only_check.md
$PY $S/x5b_summary.py $R/byte_pairs.jsonl > $R/byte_pairs_tables.md
head -n 14 $R/byte_pairs_tables.md

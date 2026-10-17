#!/bin/bash
# X5 step 3: merge the shards into the tables and csvs under eval/results/x5/.
#   sbatch eval/baselines/setup/p_x5_report.sh
#SBATCH -p normal
#SBATCH -J x5-report
#SBATCH -t 01:00:00
#SBATCH -c 1
#SBATCH -o /home/fzheng4/wt-x5/eval/x_logs/x5-report-%j.log
W=${W:-/home/fzheng4/wt-x5}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD
S=eval/baselines/setup
# the explain pass re-analyses ~66 keys (about 12 min); kept from an earlier run unless removed
[ -s eval/results/x5/bo_explain.jsonl ] || $PY $S/barrier_ordered_bins.py explain \
    --plan eval/results/x5/bo_plan.json --inputs 'eval/results/x5/bo_*shard*.jsonl' \
    --out eval/results/x5/bo_explain.jsonl > eval/results/x5/bo_explain.log
$PY $S/barrier_ordered_bins.py cfgfacts --plan eval/results/x5/bo_plan.json \
    --inputs 'eval/results/x5/bo_*shard*.jsonl' --out eval/results/x5/bo_cfgfacts.jsonl \
    > eval/results/x5/bo_cfgfacts.log
$PY $S/barrier_ordered_bins.py report --plan eval/results/x5/bo_plan.json \
    --inputs 'eval/results/x5/bo_*shard*.jsonl' --outdir eval/results/x5 > eval/results/x5/bo_report.log
$PY $S/pcdg_variance.py report --plan eval/results/x5/var_plan.json \
    --inputs 'eval/results/x5/var_shard*.jsonl' --outdir eval/results/x5 > eval/results/x5/var_report.log
for f in eval/results/x5/bo_report.log eval/results/x5/var_report.log; do echo "== $f"; tail -n 3 "$f"; done

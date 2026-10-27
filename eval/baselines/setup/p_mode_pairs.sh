#!/usr/bin/env bash
# M1 (eval/MODE_PAIRS.md): one command reproduces every table.
#   bash eval/baselines/setup/p_mode_pairs.sh            # submit collect (array) + tables (afterany)
#   sbatch --array=K-K eval/baselines/setup/p_mode_pairs.sh   # (re)run one collect shard
#   the programs that hit the 3,600 s cap, one long task (eval/results/mode-pairs/long_ids.txt):
#   sbatch --array=0-12 --exclusive --time=1-00:00:00 --export=ALL,MODE=collect,NSHARDS=13,IDFILE=eval/results/mode-pairs/long_ids.txt,TMO=82800,MEMGB=110,FORCE=1 eval/baselines/setup/p_mode_pairs.sh
# Submitted from a login node it only calls sbatch; run as an array task it is a collect shard
# (CPU, partition normal; the stores are on BeeGFS); with MODE=tables it writes the tables.
#SBATCH --job-name=m1-mode-pairs
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/wt-m1/eval/x_logs/m1-%x-%A_%a.log
WT=${WT:-/home/fzheng4/wt-m1}
PY=${PY:-/home/fzheng4/AccelProf/.env/bin/python}
cd "$WT" || exit 1
if [ -z "${SLURM_JOB_ID:-}" ]; then
    mkdir -p eval/x_logs
    N=${NSHARDS:-48}
    J=$(sbatch --parsable --array=0-$((N - 1)) --export=ALL,MODE=collect,NSHARDS=$N "$0")
    echo "collect array $J"
    sbatch --dependency=afterany:$J --time=02:00:00 --array=0-0 --job-name=m1-tables --export=ALL,MODE=tables "$0"
    exit 0
fi
echo "host=$(hostname) job=${SLURM_JOB_ID} task=${SLURM_ARRAY_TASK_ID:-0} mode=${MODE:-collect} HEAD=$(git rev-parse --short HEAD)"
if [ "${MODE:-collect}" = tables ]; then
    $PY eval/baselines/mode_pairs.py tables
else
    $PY eval/baselines/mode_pairs.py collect --shard ${SLURM_ARRAY_TASK_ID:-0}/${NSHARDS:-48} \
        --timeout ${TMO:-3600} --mem-gb ${MEMGB:-60} ${FORCE:+--force} ${IDFILE:+--id-file $IDFILE}
fi

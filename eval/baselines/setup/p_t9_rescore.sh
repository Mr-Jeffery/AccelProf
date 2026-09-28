#!/usr/bin/env bash
#SBATCH --job-name=cv-t9-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-rescore-%A_%a.log
# T9 step 6 (CLAUDE.md section C): the new hb_oracle over every kept vector-clock dump ->
# the AFTER store (eval/baselines/t9_rescore.py). CPU only; BeeGFS is mounted on compute nodes.
#   small (dump < 500 MB), 24 shards:
#     sbatch --array=0-23 --export=ALL,SIZE=small eval/baselines/setup/p_t9_rescore.sh
#   big, one program per task, on a 188 GB node:
#     sbatch --array=0-17 --mem=180G --export=ALL,SIZE=big eval/baselines/setup/p_t9_rescore.sh
CV=${CV:-/home/fzheng4/wt-T9}
cd "$CV" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G shard=$K/$N size=${SIZE:-small} HEAD=$(git -C $CV rev-parse --short HEAD)"
if [ "${SIZE:-small}" = big ]; then
    .env/bin/python eval/baselines/t9_rescore.py oracle --shard $K/$N --min-mb 500 \
        --timeout ${TMO:-21600} --mem-gb ${MEMGB:-170} ${FORCE:+--force}
else
    .env/bin/python eval/baselines/t9_rescore.py oracle --shard $K/$N --max-mb 500 \
        --timeout ${TMO:-3600} --mem-gb ${MEMGB:-60} ${FORCE:+--force}
fi
echo "== done $(date -Is)"

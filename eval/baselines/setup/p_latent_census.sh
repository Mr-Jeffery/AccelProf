#!/usr/bin/env bash
#SBATCH --job-name=cv-latent-census
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/latent-census-%A_%a.log
# T9-0 (CLAUDE.md §C, eval/LATENT_CENSUS.md): CPU-only re-score of the kept BeeGFS stores
# with the current analyzer, keeping every verdict class. Measurement only.
#   small programs (largest dump < 2 GB), 16 shards:
#     sbatch --array=0-15 --export=ALL,SIZE=small eval/baselines/setup/p_latent_census.sh
#   big programs, one per task, on a 188 GB node:
#     sbatch --array=0-N --mem=180G --export=ALL,SIZE=big eval/baselines/setup/p_latent_census.sh
CV=${CV:-/home/fzheng4/wt-T9-0}
cd "$CV" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=${OUT:-$CV/eval/results/latent-census}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G shard=$K/$N size=${SIZE:-small}"
if [ "${SIZE:-small}" = big ]; then
    .env/bin/python eval/baselines/latent_census.py collect --out "$OUT" --shard $K/$N ${FORCE:+--force} \
        --min-mb 2000 --timeout ${TMO:-14400} --mem-gb ${MEMGB:-170}
else
    .env/bin/python eval/baselines/latent_census.py collect --out "$OUT" --shard $K/$N ${FORCE:+--force} \
        --max-mb 2000 --timeout ${TMO:-3600} --mem-gb ${MEMGB:-60}
fi

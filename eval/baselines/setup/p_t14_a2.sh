#!/usr/bin/env bash
#SBATCH --job-name=cv-t14-a2
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
# T14 (CLAUDE.md C/T14, design/a2_flag.md): the offline window count and the re-score with the
# a2_uncertain flag, eval/baselines/a2_window_count.py. CPU only; BeeGFS is mounted on the
# compute nodes. Outputs under /mnt/beegfs/$USER/t14-a2/ and the store cuvein_traces/t14-after.
#   STEP=count   [STORE=evcand]                       one shard per array task
#   STEP=rescore SIZE=small|big (dump < / >= 500 MB)  T9's selection, vector-clock dumps
#   W=<worktree> STEP=count sbatch --array=0-23 -o <W>/build_logs/t14-count-%A_%a.log \
#       eval/baselines/setup/p_t14_a2.sh
#   W=<worktree> STEP=rescore SIZE=big sbatch --array=0-17 --mem=180G ... p_t14_a2.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/agent-a132f9279c0d8edd0}
cd "$W" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G step=${STEP:?} shard=$K/$N size=${SIZE:-small} HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l)"
case $STEP in
  count)
    .env/bin/python eval/baselines/a2_window_count.py count --store "${STORE:-evcand}" \
        --shard $K/$N --timeout ${TMO:-14400} --mem-gb ${MEMGB:-60} ${FORCE:+--force};;
  rescore)
    if [ "${SIZE:-small}" = big ]; then
      .env/bin/python eval/baselines/a2_window_count.py rescore --shard $K/$N --min-mb 500 \
          --timeout ${TMO:-21600} --mem-gb ${MEMGB:-170} ${FORCE:+--force}
    else
      .env/bin/python eval/baselines/a2_window_count.py rescore --shard $K/$N --max-mb 500 \
          --timeout ${TMO:-3600} --mem-gb ${MEMGB:-60} ${FORCE:+--force}
    fi;;
esac
echo "== done $(date -Is)"

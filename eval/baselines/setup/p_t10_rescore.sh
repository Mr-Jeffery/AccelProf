#!/usr/bin/env bash
#SBATCH --job-name=cv-t10-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
# T10 step 3 (CLAUDE.md section C): the T10 oracle (policy `token`) over the vector-clock dumps
# of every program whose strength table differs between `generic` and `token` -> the AFTER
# store t10-after (eval/baselines/t10_rescore.py). CPU only; BeeGFS is mounted on compute nodes.
#   W=<worktree> sbatch --array=0-7 --exclusive -o <W>/build_logs/t10-rescore-%A_%a.log \
#       <W>/eval/baselines/setup/p_t10_rescore.sh     (no --mem on this cluster: whole nodes)
set -u
W=${W:?W=<the T10 worktree>}
cd "$W" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
unset CUVEIN_STRONG_LDST
.env/bin/python eval/baselines/t10_rescore.py oracle --shard $K/$N --timeout ${TMO:-14400} \
    --mem-gb ${MEMGB:-170} ${FORCE:+--force}
echo "== done $(date -Is)"

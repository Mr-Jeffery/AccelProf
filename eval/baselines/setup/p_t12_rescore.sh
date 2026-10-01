#!/usr/bin/env bash
#SBATCH --job-name=cv-t12-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# T12 step 4 (CLAUDE.md section C): the gated oracle (instance gate, strong-ldst token) over the
# vector-clock dumps of every program with an RMW pc -> the AFTER store t12-after
# (eval/baselines/t12_rescore.py). CPU only; BeeGFS is mounted on compute nodes.
#   W=<worktree> sbatch --array=0-15 --exclusive -o <W>/build_logs/t12-rescore-%A_%a.log \
#       <W>/eval/baselines/setup/p_t12_rescore.sh     (no --mem on this cluster: whole nodes)
set -u
W=${W:?W=<the T12 worktree>}
cd "$W" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
unset CUVEIN_STRONG_LDST CUVEIN_GATE
.env/bin/python eval/baselines/t12_rescore.py oracle --shard $K/$N --timeout ${TMO:-14400} \
    --mem-gb ${MEMGB:-110} ${FORCE:+--force}
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=cv-t16-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# T16 steps 3-4: hb_oracle.py under `recorded` and `certain` over the vector-clock dumps of every
# program with an RMW pc of one set (eval/baselines/t16_rescore.py) -> the AFTER store
# t16-certain[-exits]. CPU only; BeeGFS is mounted on compute nodes.
#   W=<worktree> SET=main  sbatch --array=0-23 -o <W>/build_logs/t16-rescore-%A_%a.log \
#       <W>/eval/baselines/setup/p_t16_rescore.sh
set -u
W=${W:?W=<the T16 worktree>}; SET=${SET:-main}
cd "$W" || exit 1
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) mem=$(free -g | awk '/Mem/{print $2}')G set=$SET shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
unset CUVEIN_STRONG_LDST CUVEIN_GATE CUVEIN_GATE_POLICY
.env/bin/python eval/baselines/t16_rescore.py oracle --set $SET --shard $K/$N --timeout ${TMO:-14400} \
    --mem-gb ${MEMGB:-110} ${FORCE:+--force}
echo "== done $(date -Is)"

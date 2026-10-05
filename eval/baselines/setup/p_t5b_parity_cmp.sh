#!/usr/bin/env bash
#SBATCH --job-name=t5b-parity-cmp
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --array=0-7
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# T5b acceptance: HbClock == specification on the t5b_parity_ids.txt programs recorded with the T5b
# runtime (p_t5b_timeout.sh with TAG=t5b-final-parity); CPU only (setup/t5b_parity.py compare).
#   sbatch --dependency=afterany:<recording job> -o <W>/build_logs/t5b-parity-cmp-%A_%a.log \
#       eval/baselines/setup/p_t5b_parity_cmp.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}
TAG=${TAG:-t5b-final-parity}
cd $W || exit 1
mkdir -p eval/baselines/setup/t5b_parity/$TAG
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD)"
.env/bin/python eval/baselines/setup/t5b_parity.py compare --store /mnt/beegfs/$USER/cuvein_traces/$TAG \
    --out eval/baselines/setup/t5b_parity/$TAG/shard${SLURM_ARRAY_TASK_ID}.json --cap ${CAP:-5400} \
    --shard ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT}
echo "== done $(date -Is)"

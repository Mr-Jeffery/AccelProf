#!/usr/bin/env bash
#SBATCH --job-name=t4-parity-cmp
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --array=0-7
# T4 parity (design/no_dump.md section 6): hb_sync_pass / hb_rmw_points / the verdicts from the
# aggregates against the records of the same recording, over a store recorded with the T4
# runtime and the default dump (p_t5b_timeout.sh with W=<T4 worktree> TAG=t4-parity
# IDS=setup/t5b_parity_ids.txt BASELINE_MODES=vector-clock,scalar-clock). CPU only.
#   W=/home/fzheng4/wt-T4 TAG=t4-parity sbatch --dependency=afterany:<recording job> \
#       -o <W>/build_logs/t4-parity-cmp-%A_%a.log eval/baselines/setup/p_t4_parity_cmp.sh
W=${W:-/home/fzheng4/wt-T4}
TAG=${TAG:-t4-parity}
cd $W || exit 1
mkdir -p eval/baselines/setup/t4_parity/$TAG
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD)"
.env/bin/python eval/baselines/setup/t4_parity.py compare --store /mnt/beegfs/$USER/cuvein_traces/$TAG \
    --out eval/baselines/setup/t4_parity/$TAG/shard${SLURM_ARRAY_TASK_ID}.json --cap ${CAP:-3600} \
    --shard ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT}
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=pi-cuvein
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pi-cuvein-%A_%a.log
# cuVein (current detector revision, setup/cuvein_rev.status), both modes, over PI.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
# node-local scratch; c2 ships /mnt/local root-owned (no user dirs) -> fall back to its /tmp (752 GB)
T=/mnt/local/$USER/cvtraces; mkdir -p $T 2>/dev/null || T=/tmp/$USER/cvtraces; mkdir -p $T
export BASELINE_TRACE_DIR=$T
$PY eval/baselines/parallel.py run --pset PI --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag pi \
    --analysis-timeout 3600 \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 100

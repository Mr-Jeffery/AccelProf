#!/usr/bin/env bash
#SBATCH --job-name=full-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fullrun-%A_%a.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/local/$USER/cvtraces
$PY eval/baselines/parallel.py run --pset P1,P2,P3,P7 --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm

#!/usr/bin/env bash
#SBATCH --job-name=cv-collect
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pcollect-%A_%a.log
# GPU node (sm_89): collect cuVein traces for one shard.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/parallel.py collect --pset P4,P5,P6,P3 --shard ${SLURM_ARRAY_TASK_ID}/16

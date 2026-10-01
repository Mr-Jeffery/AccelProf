#!/usr/bin/env bash
#SBATCH --job-name=cv-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=01:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/panalyze-%A_%a.log
# CPU node: sync_dominance analysis of one shard's saved traces.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/parallel.py analyze --pset P4,P5,P6,P3 --shard ${SLURM_ARRAY_TASK_ID}/16 --confirm

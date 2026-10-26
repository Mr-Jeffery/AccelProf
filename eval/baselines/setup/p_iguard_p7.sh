#!/usr/bin/env bash
#SBATCH --job-name=iguard-p7
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-3
#SBATCH --exclude=c0,c1,c22,c34
#SBATCH --output=/home/fzheng4/wt-iguard-p7/eval/baselines/setup/build_logs/iguard-p7-%A_%a.log
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# iGUARD on the P7 HeCBench overhead set (14 apps, never run before), 3 reps,
# 4 shards -> eval/results/baselines-iguard-shardp7_{k}_4.csv
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY eval/baselines/run_iguard.py --pset P7 --shard ${SLURM_ARRAY_TASK_ID}/4 \
    --out eval/results/baselines-iguard-shardp7_${SLURM_ARRAY_TASK_ID}_4.csv

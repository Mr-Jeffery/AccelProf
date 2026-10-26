#!/usr/bin/env bash
#SBATCH --job-name=t21b-iguard-amrex
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --array=0-1
#SBATCH --exclude=c0,c1,c22,c34
#SBATCH --output=/home/fzheng4/wt-t21b/eval/realworld/logs/iguard-amrex-%A_%a.log
# amrex-1 timed out at the 120 s derived cap in 321057; rerun with the 1200 s cap
# cuVein had. Task 0 = buggy, 1 = fixed.
cd /home/fzheng4/wt-t21b || exit 1
export CUDA_HOME=/usr/local/cuda-13.4
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/realworld_t21b/iguard_logs_cap1200
V=$([ "$SLURM_ARRAY_TASK_ID" = 0 ] && echo buggy || echo fixed)
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY eval/baselines/run_iguard.py --manifest eval/realworld/manifest_t21b.csv \
    --id amrex-1-$V --reps 3 --timeout 1200 --out eval/results/realworld/iguard-amrex-$V.csv

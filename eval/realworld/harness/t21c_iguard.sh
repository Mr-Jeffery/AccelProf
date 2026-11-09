#!/usr/bin/env bash
#SBATCH --job-name=t21c-iguard
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --exclude=c0,c1,c22,c34
#SBATCH --output=/home/fzheng4/wt-t21c/eval/realworld/candidates/logs/iguard-%j.log
# iGUARD (global memory only) on the T21c candidates whose oracle race is not in
# shared memory: llmc-new-1 (cross-block hand-off via global scratch). 3 reps.
cd /home/fzheng4/wt-t21c || exit 1
export CUDA_HOME=/usr/local/cuda-13.4
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/realworld_t21c/iguard_logs
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY eval/baselines/run_iguard.py --manifest eval/realworld/manifest_t21c.csv \
    --id llmc-new-1-buggy --reps 3 --out eval/results/realworld_t21c/iguard.csv

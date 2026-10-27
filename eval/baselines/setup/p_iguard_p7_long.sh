#!/usr/bin/env bash
#SBATCH --job-name=iguard-p7-long
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
#SBATCH --array=0-4
#SBATCH --exclude=c0,c1,c22,c34
#SBATCH --output=/home/fzheng4/wt-iguard-p7/eval/baselines/setup/build_logs/iguard-p7-long-%A_%a.log
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# iGUARD on the 5 P7 apps that hit the derived 120 s cap in job 321654, with a
# fixed 5,400 s cap (cuVein's cap for most of them), 1 rep, one app per node.
cd /home/fzheng4/wt-iguard-p7 || exit 1
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
APPS=(haversine heartwall mandelbrot particlefilter stencil1d)
A=${APPS[$SLURM_ARRAY_TASK_ID]}
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY eval/baselines/run_iguard.py --id P7-$A-cuda --reps 1 --timeout 5400 \
    --out eval/results/baselines-iguard-p7long-$A.csv

#!/usr/bin/env bash
#SBATCH --job-name=x8-probe
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-x8/eval/x_logs/x8-probe-%j.log
export ACCEL_PROF_HOME=/home/fzheng4/wt-x8
cd /home/fzheng4/wt-x8 || exit 1
source eval/baselines/gpu_env.sh
export PY=/home/fzheng4/AccelProf/.env/bin/python SINGULARITY_BIND=/mnt/beegfs
$PY eval/baselines/x8_native_probe.py --out /home/fzheng4/wt-x8/eval/x_logs/x8_native_probe.csv

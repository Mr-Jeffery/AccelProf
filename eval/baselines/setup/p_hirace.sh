#!/usr/bin/env bash
#SBATCH --job-name=hirace
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/hirace-%j.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
rm -f eval/results/baselines-hirace.csv
$PY eval/baselines/run_hirace.py --reps 3
echo "hirace done"

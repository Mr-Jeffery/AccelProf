#!/usr/bin/env bash
#SBATCH --job-name=cv-racecheck
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pracecheck-%j.log
# GPU node: compute-sanitizer racecheck over shared-mem rows (fast, single job).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
rm -f eval/results/baselines-racecheck.csv
$PY eval/baselines/run_racecheck.py --pset P4,P5,P6

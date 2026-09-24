#!/usr/bin/env bash
#SBATCH --job-name=pi-hirace
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pi-hirace-%A_%a.log
# HiRace: the artifact's 590 instrumented twins, per PI manifest row (same graph+launch).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_hirace.py --pset PI --shard ${SLURM_ARRAY_TASK_ID}/16 \
    --out /home/fzheng4/AccelProf/eval/results/baselines-hirace-shardpi${SLURM_ARRAY_TASK_ID}_16.csv

#!/usr/bin/env bash
#SBATCH --job-name=pi-sc
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --array=0-3
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pi-sc-%A_%a.log
# SuperCollider: only PI's sc-subset rows (its 99 pre-instrumented tests on its own input).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_supercollider.py --pset PI --shard ${SLURM_ARRAY_TASK_ID}/4 \
    --out /home/fzheng4/AccelProf/eval/results/baselines-supercollider-shardpi${SLURM_ARRAY_TASK_ID}_4.csv

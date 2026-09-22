#!/usr/bin/env bash
#SBATCH --job-name=pi-iguard
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pi-iguard-%A_%a.log
# iGUARD (NVBit 1.8 build) over PI.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_iguard.py --pset PI --shard ${SLURM_ARRAY_TASK_ID}/32 \
    --out /home/fzheng4/AccelProf/eval/results/baselines-iguard-shardpi${SLURM_ARRAY_TASK_ID}_32.csv

#!/usr/bin/env bash
#SBATCH --job-name=cs-family
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/sanitizer-%A_%a.log
# compute-sanitizer memcheck/racecheck/synccheck/initcheck over all manifest rows,
# sharded over (row, tool) pairs -> eval/results/baselines-sanitizer-shard{k}_32.csv
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_sanitizer.py --shard ${SLURM_ARRAY_TASK_ID}/32

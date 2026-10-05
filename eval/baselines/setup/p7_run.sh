#!/usr/bin/env bash
#SBATCH --job-name=p7-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --time=01:30:00 --array=0-3
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/p7run-%A_%a.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/p7   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --pset P7 --shard ${SLURM_ARRAY_TASK_ID}/4 --confirm

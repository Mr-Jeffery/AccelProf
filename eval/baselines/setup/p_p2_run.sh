#!/usr/bin/env bash
#SBATCH --job-name=p2-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --array=0-7
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/p2run-%A_%a.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/p2   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --pset P2 --shard ${SLURM_ARRAY_TASK_ID}/8 --confirm

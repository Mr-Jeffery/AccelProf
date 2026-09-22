#!/usr/bin/env bash
#SBATCH --job-name=cv-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/prun-%A_%a.log
# GPU node (sm_89): lean combined collect+analyze+delete for one shard (no trace
# persistence -> no disk blowup). Writes a per-shard cuvein CSV.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/local/$USER/cvtraces
$PY eval/baselines/parallel.py run --pset P4,P5,P6 --shard ${SLURM_ARRAY_TASK_ID}/16 --confirm

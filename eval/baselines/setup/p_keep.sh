#!/usr/bin/env bash
#SBATCH --job-name=cv-keep
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/keep-%A_%a.log
# Re-collect the FP/FN programs (label != verdict in either mode) plus the
# vector-clock-only TIMEOUT/ERROR programs, keeping their traces under
# eval/baselines/traces_keep/<id>/ (TP/TN traces are deleted as always). Rows are
# merged as extra reps (shard tag 'keep').
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/keep   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --id-file eval/baselines/setup/keep_all_ids.txt \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag keep \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300

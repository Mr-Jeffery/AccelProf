#!/usr/bin/env bash
#SBATCH --job-name=cv-rerun-p9
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-9
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/rerun-p9-%A_%a.log
# cuVein re-run of P9 (SuperCollider's 10 HeCBench apps) on the current detector
# revision, both modes, with the same 20-minute cap ("10x native OR 20 min") the
# pre-fix P9 rows used (job 282807, tag sc9) so the matched-set comparison stays
# like-for-like. One app per array task.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/rerun-p9   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --id-file eval/baselines/setup/p9_ids.txt \
    --shard ${SLURM_ARRAY_TASK_ID}/10 --confirm --tag p9 --timeout-floor 1200 --analysis-timeout 3600 \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300

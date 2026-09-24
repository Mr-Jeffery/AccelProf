#!/usr/bin/env bash
#SBATCH --job-name=cv-fpfixeng
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fpfixeng-%A_%a.log
# Post-fix re-run (eval/FP_DIAGNOSIS.md: coherent load/store model, barrier-ordered
# class, exact pair matching, per-kernel sidecar) of the labelled sets P1-P6, kept
# APART from the merged baseline: shard csvs -> eval/results/fpfix/, confirmation
# details -> eval/baselines/confirm_fpfix/, mismatch traces -> traces_keep_fpfix/.
# Compare with:  python3 eval/baselines/compare_fpfix.py
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_MODES=vector-clock
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/fpfix-eng   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --pset P1,P2,P3,P4,P5,P6 \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag fpfix \
    --results-dir /home/fzheng4/AccelProf/eval/results/fpfix \
    --confirm-dir /home/fzheng4/AccelProf/eval/baselines/confirm_fpfix \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep_fpfix --keep-cap-mb 100

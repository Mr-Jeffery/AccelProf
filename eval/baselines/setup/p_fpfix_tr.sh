#!/usr/bin/env bash
#SBATCH --job-name=cv-fpfixtr
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fpfixtr-%A_%a.log
# Post-fix re-run (eval/FP_DIAGNOSIS.md: coherent load/store model, barrier-ordered
# class, exact pair matching, per-kernel sidecar) of the labelled sets P1-P6, kept
# APART from the merged baseline: shard csvs -> eval/results/fpfix_tr/, confirmation
# details -> eval/baselines/confirm_fpfix_tr/, mismatch traces -> traces_keep_fpfix_tr/.
# TRACE-ONLY re-run. Compare with:
#   python3 eval/baselines/compare_fpfix.py --after-glob 'eval/results/fpfix_tr/baselines-cuvein-shard*.csv'
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_MODES=trace-only   # static leg + offline barrier-only pass
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/fpfix-tr   # BeeGFS, every trace kept (eval/STORAGE.md)
$PY eval/baselines/parallel.py run --pset P1,P2,P3,P4,P5,P6 \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag fpfixtr \
    --results-dir /home/fzheng4/AccelProf/eval/results/fpfix_tr \
    --confirm-dir /home/fzheng4/AccelProf/eval/baselines/confirm_fpfix_tr \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep_fpfix_tr --keep-cap-mb 100

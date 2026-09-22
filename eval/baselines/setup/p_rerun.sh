#!/usr/bin/env bash
#SBATCH --job-name=cv-rerun
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/rerun-%A_%a.log
# cuVein re-run on the current detector revision (setup/cuvein_rev.status), both
# modes, every labelled/overhead set except P9 (20-min-cap protocol: p_rerun_p9.sh).
# Same protocol as the original sweep: 3 reps, 120 s floor, confirmation details,
# FP/FN/ERROR/TIMEOUT traces kept (TP/TN deleted). Pre-fix rows were moved to
# eval/results/prefix_fe694b5/ by supersede_prefix.sh before this array started.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
T=/mnt/local/$USER/cvtraces; mkdir -p $T 2>/dev/null || T=/tmp/$USER/cvtraces; mkdir -p $T   # c2: /mnt/local is root-owned
export BASELINE_TRACE_DIR=$T
$PY eval/baselines/parallel.py run --pset P1,P2,P3,P4,P5,P6,P7,P8 \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300

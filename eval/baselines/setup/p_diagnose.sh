#!/usr/bin/env bash
#SBATCH --job-name=cv-diag
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-22
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/diag-%A_%a.log
# Root-cause run for the trace-only ERROR/TIMEOUT residuals + all of P7: same
# collector, but with the 20-minute floor ("10x native OR 20 min"), native rc +
# stderr and the accelprof stderr/dump size captured into the notes, and the
# traces kept under traces_keep/. classify_residuals.py turns the rows into
# eval/results/baselines-diagnose.csv (cause per id). One id per array task:
# submit with  sbatch --array=0-$((N-1)) p_diagnose.sh  where N = lines in
# residual_ids.txt (setup/mk_followup_ids.py prints it); the shard count follows.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
T=/mnt/local/$USER/cvtraces; mkdir -p $T 2>/dev/null || T=/tmp/$USER/cvtraces; mkdir -p $T   # c2: /mnt/local is root-owned
export BASELINE_TRACE_DIR=$T
$PY eval/baselines/parallel.py run --id-file eval/baselines/setup/residual_ids.txt \
    --shard ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT:-23} --confirm --tag resid --timeout-floor 1200 \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300

#!/usr/bin/env bash
#SBATCH --job-name=cv-full
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/full-%A_%a.log
# T0 step 6: (re-)collect programs into an UNCAPPED BeeGFS store, both modes, every
# trace kept, a timed-out rep's partial dump kept under <id>/<mode>-partial-rep<k>/
# (eval/STORAGE.md). First use: the programs whose traces earlier sweeps dropped
# (setup/t0_full_ids_{p79,rest}.txt, from store_inventory.py), store full-2026-09-22:
#   IDFILE=eval/baselines/setup/t0_full_ids_p79.txt FLOOR=1200 sbatch --array=0-N p_full_store.sh  # P7/P9: 20-min cap, 1 id/task
#   IDFILE=eval/baselines/setup/t0_full_ids_rest.txt sbatch -p rtx4060ti16g,rtx4060ti8g --array=0-15 p_full_store.sh
# (P1-P6 may also use the 8g nodes -- the script pins the sm_89 GPU there; P7/P9 stay on 16g:
#  their 20-minute budgets and 16 GB VRAM must match the earlier rows)
# Variables: TAG (store name, default full-<today>), IDFILE, PSET, FLOOR (tool timeout
# floor s, default 120), REPS (default 1: a store wants the trace, not timing reps),
# ACAP (offline analysis cap s, default 3600), MANIFEST, CV (checkout whose harness
# runs; the runtime -- bin/accelprof, lib/, python/ -- is always $ACCEL_PROF_HOME).
CV=${CV:-/home/fzheng4/AccelProf}
cd "$CV" || exit 1
source eval/baselines/gpu_env.sh
# dual-GPU rtx4060ti8g nodes (4060 Ti + 2060/2080 Super): expose only the sm_89 device
[ "${SLURM_JOB_PARTITION:-}" = rtx4060ti8g ] && source eval/baselines/setup/pin8g.sh
TAG=${TAG:-full-$(date +%F)}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
SEL=()
[ -n "${PSET:-}" ] && SEL+=(--pset "$PSET")
[ -n "${IDFILE:-}" ] && SEL+=(--id-file "$IDFILE")
echo "host=$(hostname) store=$BASELINE_TRACE_DIR shard=$K/$N floor=${FLOOR:-120} reps=${REPS:-1} cv=$CV"
df -h /mnt/beegfs | tail -1
$PY eval/baselines/parallel.py run --manifest "${MANIFEST:-eval/baselines/setup/manifest.evcand.csv}" "${SEL[@]}" \
    --shard $K/$N --confirm --tag "$TAG" --reps "${REPS:-1}" --timeout-floor "${FLOOR:-120}" \
    --analysis-timeout "${ACAP:-3600}" \
    --results-dir "$CV/eval/results/$TAG" --confirm-dir "$CV/eval/baselines/confirm_$TAG"

#!/usr/bin/env bash
#SBATCH --job-name=cv-analyze-cpu
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --array=0-31
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/analyze-cpu-%A_%a.log
# CPU-only re-score of a kept BeeGFS trace store (T0, eval/STORAGE.md): `parallel.py
# analyze` reads <store>/<id>/{meta.json,dots/,<mode>/kernel_*.json} and runs
# sync_dominance -- it never calls blib.resolve_cuda_home(), so it runs on the
# `normal`/`max` partitions, where BeeGFS is mounted like on every compute node.
# One shard per array task; the shard count is the array size, so use the SAME
# --array as the collecting sweep (or any size: analyze shards over the manifest
# order, a program that is not in the store gets an ERROR no-trace-collected row).
#
#   TAG=<store tag under /mnt/beegfs/$USER/cuvein_traces/>   (required)
#   OUT=<name>          shard csvs -> eval/results/<OUT>/, details -> eval/baselines/confirm_<OUT>/
#                       (default: rescore-<TAG>)
#   PSET=P1,...         and/or IDFILE=<path>   which programs (default: every manifest row)
#   MANIFEST=<csv>      (default eval/baselines/manifest.csv; the evcand store was sharded
#                       with eval/baselines/setup/manifest.evcand.csv)
#   MODES=vector-clock,scalar-clock   $BASELINE_MODES for the store (default both)
#   EXTRA="--analysis-timeout 3600"   anything else for parallel.py analyze
#   CV=<checkout>       whose eval/baselines/parallel.py runs (default the main checkout)
#
#   TAG=full-2026-09-22 OUT=full-2026-09-22-cpu sbatch --array=0-7 eval/baselines/setup/p_analyze_cpu.sh
CV=${CV:-/home/fzheng4/AccelProf}   # checkout whose harness runs (a task worktree while unmerged)
cd "$CV" || exit 1
source eval/baselines/gpu_env.sh
: "${TAG:?set TAG=<store tag>}"
OUT=${OUT:-rescore-$TAG}
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_MODES=${MODES:-vector-clock,scalar-clock}
SEL=()
[ -n "${PSET:-}" ] && SEL+=(--pset "$PSET")
[ -n "${IDFILE:-}" ] && SEL+=(--id-file "$IDFILE")
echo "host=$(hostname) store=$BASELINE_TRACE_DIR shard=$K/$N out=$OUT modes=$BASELINE_MODES"
$PY eval/baselines/parallel.py analyze --manifest "${MANIFEST:-eval/baselines/manifest.csv}" "${SEL[@]}" \
    --shard $K/$N --confirm --tag "$OUT" \
    --results-dir "$CV/eval/results/$OUT" \
    --confirm-dir "$CV/eval/baselines/confirm_$OUT" ${EXTRA:-}

#!/usr/bin/env bash
#SBATCH --job-name=t3b-oldstore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-T3b/eval/baselines/setup/build_logs/t3b-oldstore-%A_%a.log
# T3b step 4 (eval/CRS_CUDA_TRIAGE.md §"Fix"): a pre-T3b trace store -- no exit records, no
# hb_exits marker -- re-scored from the same dumps by the base detector (wt-T3b-base, 0251780)
# and by the T3b detector, shard by shard. Exit-aware assembly and the end-of-kernel check
# apply only to dumps with exit records / the marker, so every (id, mode) row must agree.
# CPU only. Compare afterwards with setup/t3b_oldstore_cmp.py.
#   TAG=evcand MANIFEST=eval/baselines/setup/manifest.evcand.csv sbatch --array=0-31 eval/baselines/setup/t3b_oldstore.sh
#   TAG=full-2026-09-22 ID=P9-crs-cuda sbatch eval/baselines/setup/t3b_oldstore.sh
set -u
W=/home/fzheng4/wt-T3b; B=/home/fzheng4/wt-T3b-base; TAG=${TAG:-evcand}
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_MODES=vector-clock,scalar-clock
echo "host=$(hostname) store=$BASELINE_TRACE_DIR shard=$K/$N date=$(date -Is)"
for side in base t3b; do
  CV=$W; [ $side = base ] && CV=$B
  OUT=$W/eval/results/t3b-oldstore-$TAG-$side
  ( cd $CV && export ACCEL_PROF_HOME=$CV && source eval/baselines/gpu_env.sh && \
    echo "== $side: $CV at $(git -C $CV rev-parse --short HEAD), python/ diff $(git -C $CV diff HEAD -- python | sha256sum | cut -c1-12)" && \
    $PY eval/baselines/parallel.py analyze --manifest ${MANIFEST:-eval/baselines/manifest.csv} \
        ${ID:+--id $ID} --shard $K/$N --confirm --tag t3b-oldstore-$TAG-$side --results-dir $OUT \
        --confirm-dir $W/eval/baselines/confirm_t3b-oldstore-$TAG-$side 2>&1 | tail -1 )
done
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=merge-oldstore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/merge-oldstore-%A_%a.log
# T3b+T9 merge check (CLAUDE.md status 2026-09-28, "Merge and install"): the evcand store --
# no exit records, no hb_exits marker -- re-scored shard by shard by the T9 detector
# (CODE9 = `git archive b1a6408 python eval`) and by the merged detector (this checkout).
# The merge adds T3b's exit handling, which applies only to dumps with exit records, so
# every (id, mode, rep) row must agree. CPU only. Compare with
#   setup/t3b_oldstore_cmp.py merge-evcand   (side "base" = T9, side "t3b" = merged)
#   sbatch --export=ALL,CODE9=<tree> --array=0-31 eval/baselines/setup/merge_oldstore.sh
set -u
A=/home/fzheng4/AccelProf; TAG=evcand
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_MODES=vector-clock,scalar-clock
echo "host=$(hostname) store=$BASELINE_TRACE_DIR shard=$K/$N date=$(date -Is) merged=$(git -C $A rev-parse --short HEAD)"
for side in base t3b; do
  CV=$A; [ $side = base ] && CV=${CODE9:?}
  OUT=$A/eval/results/t3b-oldstore-merge-$TAG-$side
  ( cd $CV && export ACCEL_PROF_HOME=$CV CUVEIN_HOME=$CV && echo "== $side: $CV" && \
    $A/.env/bin/python eval/baselines/parallel.py analyze \
        --manifest $A/eval/baselines/setup/manifest.evcand.csv \
        --shard $K/$N --confirm --tag merge-oldstore-$TAG-$side --results-dir $OUT \
        --confirm-dir $A/eval/baselines/confirm_merge-oldstore-$TAG-$side 2>&1 | tail -1 )
done
echo "== done $(date -Is)"

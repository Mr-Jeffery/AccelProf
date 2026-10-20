#!/usr/bin/env bash
#SBATCH --job-name=t22-diag
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
# T22 design diagnostic (not step C): programs in scalar-clock mode, no dump, HB_STATS, a short cap,
# at several shard counts, one after another on one node, with the worktree's private runtime --
# to read where a drain's time goes (hb_stats.hb_clock.sharded: drain_s, route_s, wait_s, busy_s)
# and how many kernels each configuration completes under the cap. Partial dumps are kept.
#   RUNS="P7-heartwall-cuda:8 P7-heartwall-cuda:1" CAP=900 TAG=t22-diag \
#     sbatch -p <gpu partition> -w <node> -o <log> eval/baselines/setup/t22_diag.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) nproc=$(nproc) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
for run in $RUNS; do
  id=${run%%:*}; n=${run##*:}
  T=${TAG:-t22-diag}-${id}-n$n
  echo "==== $id YOSEMITE_HB_SHARDS=$n cap ${CAP:-900} $(date -Is)"
  rm -rf /mnt/beegfs/$USER/cuvein_traces/$T $W/eval/results/$T
  mkdir -p $W/eval/results/$T /mnt/beegfs/$USER/cuvein_traces/$T
  env BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$T BASELINE_MODES=scalar-clock BASELINE_HB_DUMP=0 \
      YOSEMITE_HB_STATS=1 YOSEMITE_HB_SHARDS=$n \
      $PY eval/baselines/parallel.py run --id $id --reps 1 --keep-all \
      --timeout-floor ${CAP:-900} --timeout-cap ${CAP:-900} --analysis-timeout 3600 --tag $T \
      --results-dir $W/eval/results/$T --confirm-dir $W/eval/baselines/confirm_$T 2>&1 | tail -4
  cut -d, -f1,7,9,13,14,15,17 $W/eval/results/$T/*.csv | tail -1 | cut -c1-300
  $PY $W/eval/baselines/setup/t22_kstats.py /mnt/beegfs/$USER/cuvein_traces/$T 2>&1 | grep -v "^  buckets" | tail -12
  ls -l --time-style=+%s /mnt/beegfs/$USER/cuvein_traces/$T/$id/*/kernel_*.json 2>/dev/null | awk '{print $6, $7}' | sort -n | head -40
done
echo "== done $(date -Is)"

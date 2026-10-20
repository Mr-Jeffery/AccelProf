#!/usr/bin/env bash
#SBATCH --job-name=t22-perf
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
# T22 step C / D: programs in scalar-clock mode with the worktree's private runtime, the X1 protocol
# (no dump, HB_STATS, the harness's own timing), one configuration after the other on one node:
#   RUNS="<id>:<N>[:<reps>] ..."  N = YOSEMITE_HB_SHARDS (1 = the serial pass)
#   CAP=<s>                       tool cap (floor = cap, as X1's long passes; default 86400)
#   TAG=<tag>                     results eval/results/<tag>-<id>-n<N>, store cuvein_traces/<same>
#   sbatch -p <gpu partition> -w <node> -o <log> eval/baselines/setup/t22_perf.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
unset YOSEMITE_HB_SHARDS YOSEMITE_HB_SHARD_INLINE_MAX YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_NO_ENGINE
echo "host=$(hostname) nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G $(lscpu | grep 'Model name' | sed 's/  */ /g') $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
for run in $RUNS; do
  IFS=: read -r id n reps <<< "$run"
  T=${TAG:-t22-perf}-${id}-n$n
  echo "==== $id YOSEMITE_HB_SHARDS=$n reps ${reps:-1} cap ${CAP:-86400} $(date -Is)"
  rm -rf /mnt/beegfs/$USER/cuvein_traces/$T $W/eval/results/$T
  mkdir -p $W/eval/results/$T /mnt/beegfs/$USER/cuvein_traces/$T
  env BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$T BASELINE_MODES=scalar-clock BASELINE_HB_DUMP=0 \
      YOSEMITE_HB_STATS=1 YOSEMITE_HB_SHARDS=$n \
      $PY eval/baselines/parallel.py run --id $id --reps ${reps:-1} --keep-all \
      --timeout-floor ${CAP:-86400} --timeout-cap ${CAP:-86400} --analysis-timeout 14400 --tag $T \
      --results-dir $W/eval/results/$T --confirm-dir $W/eval/baselines/confirm_$T 2>&1 | tail -3
  cut -d, -f1,7,8,9,10,13,14,15,17 $W/eval/results/$T/*.csv | tail -n +2 | cut -c1-300
done
echo "== done $(date -Is)"

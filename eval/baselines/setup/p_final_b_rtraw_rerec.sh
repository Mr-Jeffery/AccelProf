#!/usr/bin/env bash
#SBATCH --job-name=x1b-rtraw-rerec
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclusive --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/x1b/rtraw-rerec/rerec-%j.log
# X1b P5 lock_rtraw triage (eval/results/final-b/triage_rtraw.md), Jeffery 10-25: re-record
# P5-race_interblock_none-lock_rtraw on one node with the INSTALLED runtime (f551ca0: libsanalyzer 5a20fd14,
# collector b746b4dd, fatbin a2d7368b; exit 99 on a mismatch), to tell node from runtime as the cause of
# the A2-inverted lock hand-off X1b recorded on c79 in 6 of 6.
#   A. X1b's harness as p_final.sh runs it (same environment and parallel.py flags), one rep per
#      invocation, NA invocations, each into its own store directory so every recording is kept.
#   B. X4's recorder (final_rtraw.py record: lossless dump, YOSEMITE_HB_STATS=0), NB vector-clock runs,
#      label x1b-rerec, so the schedules compare with FINAL_RTRAW.md's per node.
# Outputs: eval/results/final-b/rtraw-rerec/{x1b-harness,x4-recorder}/ (X4's eval/results/final-rtraw/ is not touched).
#   sbatch -w <node> eval/baselines/setup/p_final_b_rtraw_rerec.sh
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d not readable"; exit 2; }; done
W=/home/fzheng4/wt-x1b; RT=/home/fzheng4/AccelProf; H=$(hostname)
NA=${NA:-10}; NB=${NB:-30}; K0=${K0:-1}   # K0: first run number (append runs to an earlier set); SKIP_B=1 skips part B
ID=P5-race_interblock_none-lock_rtraw
BASE=/mnt/beegfs/fzheng4/cuvein_traces/x1b-rtraw-rerec
OUT=$W/eval/results/final-b/rtraw-rerec
LOG=/home/fzheng4/x1b/rtraw-rerec
source $W/eval/baselines/setup/home_quota_guard.sh
cd $RT || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
PY=${PY:-$RT/.env/bin/python}
h() { sha256sum "$1" | cut -c1-16; }
SAN=$(ldd $RT/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
[ "$(h $SAN)" = 5a20fd14ab6c6806 ] && [ "$(h $RT/lib/libcompute_sanitizer.so)" = b746b4dd23e90f46 ] \
    && [ "$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)" = a2d7368bc1c61986 ] \
    || { echo "RUNTIME MISMATCH: $(h $SAN) $(h $RT/lib/libcompute_sanitizer.so)"; exit 99; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $H: GPU [$gpu]"; exit 2;; esac
echo "host=$H gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] mem=$(free -g | awk '/Mem:/{print $2}')G runtime=$(git -C $RT rev-parse --short=12 HEAD) harness=$(git -C $W rev-parse --short=12 HEAD) job=${SLURM_JOB_ID:-} $(date -Is)"
# A: X1b's harness (p_final.sh's knobs: no dump, hb_stats on, scalar-clock at 16 shards)
export BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16
mkdir -p $OUT/x1b-harness/$H $LOG
for k in $(seq $K0 $((K0 + NA - 1))); do
  export BASELINE_TRACE_DIR=$BASE/x1b-harness/$H/run$k
  mkdir -p $BASELINE_TRACE_DIR $LOG/confirm/$H/run$k
  $PY $W/eval/baselines/parallel.py run --id $ID --shard 0/1 --reps 1 --confirm --keep-all \
      --timeout-floor 1200 --timeout-cap 1200 --analysis-timeout 14400 --tag rerec-$H-$k \
      --results-dir $OUT/x1b-harness/$H --confirm-dir $LOG/confirm/$H/run$k > $LOG/A-$H-$k.out 2>&1
  echo "A run $k rc=$? $(date -Is)"
done
unset BASELINE_TRACE_DIR BASELINE_HB_DUMP YOSEMITE_HB_STATS BASELINE_HB_SHARDS
[ "${SKIP_B:-0}" = 1 ] && { echo "B skipped; == done $(date -Is)"; exit 0; }
# B: X4's recorder, as p_final_rtraw.sh's scor-recorded label runs it
$PY $W/eval/baselines/final_rtraw.py record --store $BASE/x4-recorder \
    --exe $RT/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw --label x1b-rerec --runs $NB > $LOG/B-$H.out 2>&1
echo "B rc=$? $(date -Is)"
rm -rf $OUT/x4-recorder/x1b-rerec/$H; mkdir -p $OUT/x4-recorder/x1b-rerec
cp -r $BASE/x4-recorder/x1b-rerec/$H $OUT/x4-recorder/x1b-rerec/$H
echo "== done $(date -Is)"

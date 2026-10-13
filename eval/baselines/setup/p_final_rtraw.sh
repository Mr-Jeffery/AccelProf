#!/usr/bin/env bash
#SBATCH --job-name=x4-rtraw
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2,c21,c37
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/x4-rtraw-%j.log
# X4 (eval/FINAL_RTRAW.md): on one rtx4060ti16g node, with the INSTALLED runtime (ACCEL_PROF_HOME =
# the main checkout; d38d057: libsanalyzer 2201fcb7, collector ee78cb89, fatbin a2d7368b):
#   scor-recorded        RUNS  (50) vector-clock recordings of ScoR race_interblock_none-lock_rtraw
#   scor-certain         CRUNS (10) the same under YOSEMITE_HB_GATE_POLICY=certain
#   forced-vector-clock  FRUNS  (5) python/testdata/write_after_unlock_other_schedule.cu, vector-clock
#   forced-scalar-clock  FRUNS  (5) the same binary build, scalar-clock
#   scor-scalar-clock    SRUNS (50) the ScoR kernel in scalar-clock mode (only if named in LABELS)
# LABELS selects (default: the first four). Each with BASELINE_HB_DUMP=1 (the lossless dump) and YOSEMITE_HB_STATS=0, no other knob
# (final_rtraw.py record). The store is BeeGFS (T0); the small dumps are then copied into the
# worktree's eval/results/final-rtraw/<label>/<node>/.
#   W=<worktree> sbatch -w <node> eval/baselines/setup/p_final_rtraw.sh
set -u
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x4}
A=/home/fzheng4/AccelProf
export ACCEL_PROF_HOME=$A
export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
source $A/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
STORE=${STORE:-/mnt/beegfs/$USER/cuvein_traces/final-rtraw}
OUT=${OUT:-$W/eval/results/final-rtraw}
SCOR=$A/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw
FORCED=$W/python/testdata/write_after_unlock_other_schedule.cu
X="$A/.env/bin/python $W/eval/baselines/final_rtraw.py record --store $STORE"
H=$(hostname)
echo "host=$H $(date -Is) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader)"
LABELS=${LABELS:-scor-recorded scor-certain forced-vector-clock forced-scalar-clock}
for lab in $LABELS; do
  case $lab in
    scor-recorded)       $X --exe $SCOR --label $lab --runs ${RUNS:-50} ;;
    scor-certain)        $X --exe $SCOR --label $lab --policy certain --runs ${CRUNS:-10} ;;
    scor-scalar-clock)   $X --exe $SCOR --label $lab --mode scalar-clock --runs ${SRUNS:-50} ;;
    forced-vector-clock) $X --src $FORCED --label $lab --runs ${FRUNS:-5} ;;
    forced-scalar-clock) $X --src $FORCED --label $lab --mode scalar-clock --runs ${FRUNS:-5} ;;
  esac
done
for lab in $LABELS; do
  [ -d $STORE/$lab/$H ] || continue
  rm -rf $OUT/$lab/$H; mkdir -p $OUT/$lab
  cp -r $STORE/$lab/$H $OUT/$lab/$H
  rm -f $OUT/$lab/$H/cfg/write_after_unlock_other_schedule     # the built binary
done
echo "== done $(date -Is)"

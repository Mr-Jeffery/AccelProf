#!/usr/bin/env bash
#SBATCH --job-name=t19-time
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
# T19 step 5: wall time before (the installed runtime, d67ed41: node-based buckets) and after
# (the worktree's private runtime: flat buckets), one after the other on ONE node, no-dump mode
# (YOSEMITE_HB_DUMP=0: HbClock's cost without the serialiser), HB_STATS at kernel end only:
#   T5a's three (tiled_gemm N=256, reduction-norace large, Indigo3 CC push 1296n) in vector-clock
#   mode through t5a_stats.py; P7-hotspot in vector-clock and P9-fpc in scalar-clock mode (T4's
#   regression) through t19_long.sh with a CAP-second limit.
#   W=<worktree> sbatch -w <node> -o <log> eval/baselines/setup/t19_time.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}; A=/home/fzheng4/AccelProf
cd $W || exit 1
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
export BASELINE_HB_DUMP=0
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') HEAD=$(git -C $W rev-parse --short HEAD)"
EV=$W/eval/baselines/setup/t19_time; mkdir -p $EV
B=/mnt/beegfs/$USER/t19_bin; mkdir -p $B
nvcc -arch=sm_89 -lineinfo --cudart shared -o $B/tiled_gemm python/testdata/scale/tiled_gemm.cu
CC=CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug
echo P7-hotspot-cuda > $EV/hotspot.txt; echo P9-fpc-cuda > $EV/fpc.txt
for rt in ${RUNTIMES:-before after}; do
  R=$A; [ $rt = after ] && R=$W
  export ACCEL_PROF_HOME=$R
  echo "== $rt: collector $(sha256sum $R/lib/libcompute_sanitizer.so | cut -c1-16) -> libsanalyzer $(sha256sum $(ldd $R/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16) $(date -Is)"
  S="$PY $W/eval/baselines/setup/t5a_stats.py --out $EV --mode vector-clock"
  $S --label tiled_gemm-256-$rt --exe $B/tiled_gemm --args 256 --cap 900
  $S --label reduction-norace-large-$rt --exe $A/eval/baselines/bin/P4/reduction_norace \
     --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
  $S --label cc-push-1296n-$rt --exe $A/eval/baselines/bin/P1/${CC}__slower_atomic \
     --args "$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect4dim_rand_torus_1296n_10368e.egr 1 0 1" --cap 600
  RT=$R OUTDIR=t19-time-$rt IDS=$EV/hotspot.txt MODES=vector-clock CAP=${HOT_CAP:-2400} EVERY=0 \
     bash eval/baselines/setup/t19_long.sh 2>&1 | /usr/bin/grep -v "^host=" | sed "s/^/[hotspot $rt] /"
  RT=$R OUTDIR=t19-time-$rt IDS=$EV/fpc.txt MODES=scalar-clock CAP=${FPC_CAP:-3600} EVERY=0 \
     bash eval/baselines/setup/t19_long.sh 2>&1 | /usr/bin/grep -v "^host=" | sed "s/^/[fpc $rt] /"
done
echo "== done $(date -Is)"

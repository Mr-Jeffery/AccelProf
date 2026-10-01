#!/usr/bin/env bash
#SBATCH --job-name=t5b-stats
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# T5b (eval/MEMORY_FOOTPRINT.md "After the fix"): YOSEMITE_HB_STATS on T5a's three programs
# in vector-clock mode, with the live runtime (before: full clocks) and the T5b worktree
# runtime (after: shared-base main clock), one after the other on the same node --
# tiled_gemm N=256 (barriers only), the ScoR app reduction (large input; atomics across
# blocks) and the Indigo3 CC push 1296n program (OOM at 186 GB in T5a), each under T5a's cap.
# Needs a 188 GB node (c70, c73).
#   W=<worktree> sbatch -p rtx4060ti16g -w c70 -o <W>/build_logs/t5b-stats-%j.log \
#       eval/baselines/setup/t5b_stats.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}; A=/home/fzheng4/AccelProf
cd $W || exit 1
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G"
EV=$W/eval/baselines/setup/t5b_stats; mkdir -p $EV
B=/mnt/beegfs/$USER/t5b_bin; mkdir -p $B
nvcc -arch=sm_89 -lineinfo --cudart shared -o $B/tiled_gemm python/testdata/scale/tiled_gemm.cu
CC=CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug
for rt in ${RUNTIMES:-main t5b}; do
  R=$A; [ $rt = t5b ] && R=$W
  export ACCEL_PROF_HOME=$R
  echo "== $rt: collector $(sha256sum $R/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}') $(sha256sum $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}') | cut -c1-16)"
  S="$PY $W/eval/baselines/setup/t5a_stats.py --out $EV --mode vector-clock"
  $S --label tiled_gemm-256-$rt --exe $B/tiled_gemm --args 256 --cap 900
  $S --label reduction-norace-large-$rt --exe $A/eval/baselines/bin/P4/reduction_norace \
     --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
  $S --label cc-push-1296n-$rt --exe $A/eval/baselines/bin/P1/${CC}__slower_atomic \
     --args "$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect4dim_rand_torus_1296n_10368e.egr 1 0 1" \
     --cap ${CC_CAP:-300} --every 1000
done
echo "== done $(date -Is)"

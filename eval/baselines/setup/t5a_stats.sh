#!/usr/bin/env bash
#SBATCH --job-name=t5a-stats
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t5a-stats-%j.log
# T5a step 2 (eval/MEMORY_FOOTPRINT.md): YOSEMITE_HB_STATS attribution runs with the T5a
# worktree runtime -- tiled_gemm N=256 (the exact oracle needed 8.23 GB, HARDENING_REPORT
# Phase 4), the ScoR app reduction (large input; vector-clock 6.6 GB vs scalar-clock 0.9 GB
# in the baselines), and the Indigo3 CC push 1296n program that reached 113-127 GB
# (FP_DIAGNOSIS.md addendum), under a 300 s cap with mid-kernel snapshots. Each also once
# in scalar-clock mode (the buffered hb_events alone). Needs a 188 GB node (c70, c73).
#   sbatch -p rtx4060ti16g -w c70 eval/baselines/setup/t5a_stats.sh
set -u
W=/home/fzheng4/wt-T5a; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G"
EV=$W/eval/baselines/setup/t5a_stats; mkdir -p $EV
B=/mnt/beegfs/$USER/t5a_bin; mkdir -p $B
nvcc -arch=sm_89 -lineinfo --cudart shared -o $B/tiled_gemm python/testdata/scale/tiled_gemm.cu
S="$PY eval/baselines/setup/t5a_stats.py --out $EV"
CC=CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug
# ONLY=<label> reruns one case. cc-push-1296n: one buffer drain holds a whole kernel (198,617
# records), so snapshots are counted per record at 1000, 2000, 4000, ... (a 2M-record and a
# per-buffer 20k interval left no usable snapshot, jobs 287931 and 287953)
for m in vector-clock scalar-clock; do
  sfx=""; [ $m = scalar-clock ] && sfx="-sc"
  [ -z "${ONLY:-}" ] && $S --mode $m --label tiled_gemm-256$sfx --exe $B/tiled_gemm --args 256 --cap 900
  [ -z "${ONLY:-}" ] && $S --mode $m --label reduction-norace-large$sfx --exe $A/eval/baselines/bin/P4/reduction_norace \
     --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
  [ -n "${ONLY:-}" ] && [ "$ONLY$sfx" != "cc-push-1296n$sfx" -o $m = scalar-clock ] && continue
  $S --mode $m --label cc-push-1296n$sfx --exe $A/eval/baselines/bin/P1/${CC}__slower_atomic \
     --args "$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect4dim_rand_torus_1296n_10368e.egr 1 0 1" \
     --cap 300 --every 1000
done
echo "== done $(date -Is)"

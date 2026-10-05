#!/usr/bin/env bash
#SBATCH --job-name=t12-measure
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/.claude/worktrees/feat-instance-gate/build_logs/t12-measure-%j.log
# T12 step 4 (CLAUDE.md section C): YOSEMITE_HB_STATS on T5a's three programs with the T12 runtime,
# under the instance gate (default) and the trusting gate (YOSEMITE_HB_GATE=trusting), same node,
# same helper as T5a/T9 (eval/baselines/setup/t5a_stats.py): unfenced RMWs no longer publish or
# join, so the released/vc terms may shrink. tiled_gemm has no atomics (barrier-only: the gate is
# moot, a control); reduction-norace-large and Indigo3 CC push 1296n (300 s cap) have RMWs.
#   sbatch -p rtx4060ti16g -w c70 eval/baselines/setup/t12_measure.sh     (a 188 GB node)
set -u
W=/home/fzheng4/AccelProf/.claude/worktrees/feat-instance-gate; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) HEAD=$(git -C $W rev-parse --short HEAD)"
EV=$W/eval/results/${STATS_DIR:-t12-stats}; mkdir -p $EV
B=/mnt/beegfs/$USER/t12_bin; mkdir -p $B
nvcc -arch=sm_89 -lineinfo --cudart shared -o $B/tiled_gemm python/testdata/scale/tiled_gemm.cu
S="$PY eval/baselines/setup/t5a_stats.py --out $EV"
CC=CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug
for gate in instance trusting; do
  if [ $gate = trusting ]; then export YOSEMITE_HB_GATE=trusting; else unset YOSEMITE_HB_GATE; fi
  echo "== gate=$gate"
  $S --mode vector-clock --label t12-$gate-tiled_gemm-256 --exe $B/tiled_gemm --args 256 --cap 900
  $S --mode vector-clock --label t12-$gate-reduction-norace-large --exe $A/eval/baselines/bin/P4/reduction_norace \
     --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
  $S --mode vector-clock --label t12-$gate-cc-push-1296n --exe $A/eval/baselines/bin/P1/${CC}__slower_atomic \
     --args "$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect4dim_rand_torus_1296n_10368e.egr 1 0 1" \
     --cap 300 --every 1000
done
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=t6-probe
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/wt-T6/eval/baselines/setup/build_logs/t6-probe-%j.log
# T6 (c): build and trace the I1 / I2 / I5 test kernels (python/testdata) and the P5 canary
# with getall.sh (vector-clock mode, the installed runtime) into t6_runs/, and record the
# Sanitizer's barrier-callback documentation.   sbatch -p rtx4060ti16g -x c54,c2 t6_probe.sh
set -u
W=${W:-/home/fzheng4/wt-T6}
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1)"
echo "collector $(sha256sum lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"
H=$CUDA_HOME/compute-sanitizer/include/sanitizer_patching.h
echo "== $H"; grep -n -i -B2 -A12 "SanitizerCallbackBarrier\b\|typedef.*Barrier" $H | head -60
grep -n -i "BARRIER" $H | head -30
nvcc --version | tail -2
R=$W/t6_runs; rm -rf $R; mkdir -p $R
for src in python/testdata/write_after_unlock_other_schedule.cu python/testdata/strong_stores_barrier_weak_load.cu \
           python/testdata/local_mem_blocks.cu canary_pc_level_false_negative.cu; do
  b=$(basename $src .cu); mkdir -p $R/$b
  nvcc -arch=native -lineinfo --cudart shared $src -o $R/$b/$b || { echo "BUILD FAIL $b"; continue; }
  cuobjdump -sass $R/$b/$b > $R/$b/$b.sass 2>&1
  ( bash getall.sh $R/$b/$b > $R/$b/getall.out 2>&1 ); echo "$b getall rc=$?"
  ls $R/$b/dependency_*/ 2>/dev/null | head -3
done
echo "== done $(date -Is)"

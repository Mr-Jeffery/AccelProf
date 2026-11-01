#!/bin/bash
#SBATCH --job-name=x9-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --exclusive
#SBATCH --time=23:00:00
#SBATCH --exclude=c0,c1,c2,c13,c21,c22,c23,c34,c37,c46,c54
#SBATCH --output=/home/fzheng4/x9-logs/x9-build-%j.log
# X9 step 1-2: extract CUTLASS v4.8.1 to BeeGFS (once), configure for sm_89, list test targets, build TARGETS.
#   TARGETS="t1 t2" sbatch x9_build.sh
set -u
B=/mnt/beegfs/fzheng4/cutlass; SRC=$B/src/cutlass-v4.8.1; BLD=$B/build
timeout 10 ls /mnt/beegfs/fzheng4 >/dev/null || { echo "NODE-PROBLEM $(hostname): no BeeGFS"; exit 97; }
export CUDA_HOME=/usr/local/cuda-13.3 PATH=/usr/local/cuda-13.3/bin:$PATH
export PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
command -v nvcc >/dev/null || { echo "NODE-PROBLEM $(hostname): no nvcc"; exit 96; }
echo "host=$(hostname) job=${SLURM_JOB_ID:-} $(date -Is) nvcc=$(nvcc --version | tail -1) gcc=$(gcc -dumpfullversion) cmake=$(cmake --version | head -1)"
mkdir -p $B/src $BLD
if [ ! -f $SRC/CMakeLists.txt ]; then
  tar -C $B/src -xf /home/fzheng4/incoming/cutlass-v4.8.1.tar && echo "extracted $(date -Is)"
fi
if [ ! -f $BLD/CMakeCache.txt ]; then
  ( cd $BLD && cmake $SRC -DCMAKE_BUILD_TYPE=Release -DCUTLASS_NVCC_ARCHS=89 -DCUTLASS_ENABLE_TESTS=ON \
      -DCUTLASS_UNITY_BUILD_ENABLED=ON -DCMAKE_CUDA_FLAGS=-lineinfo -DCUTLASS_NVCC_EMBED_PTX=OFF \
      -DCUTLASS_ENABLE_LIBRARY=OFF -DCUTLASS_ENABLE_PROFILER=OFF -DCUTLASS_ENABLE_EXAMPLES=OFF \
      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_CUDA_COMPILER=$CUDA_HOME/bin/nvcc \
      -DCMAKE_C_COMPILER=$(command -v gcc) -DCMAKE_CXX_COMPILER=$(command -v g++) > $B/cmake-configure.log 2>&1 )
  echo "configure rc=$? $(date -Is)"; tail -5 $B/cmake-configure.log
  ( cd $BLD && cmake --build . --target help | grep -o 'cutlass_test_unit_[A-Za-z0-9_]*' | sort -u > $B/test_targets.txt )
  echo "targets: $(wc -l < $B/test_targets.txt)"
fi
for t in ${TARGETS:-}; do
  s=$(date +%s)
  ( cd $BLD && cmake --build . --target $t -j 16 > $B/build-$t.log 2>&1 ); rc=$?
  echo "build $t rc=$rc wall=$(( $(date +%s) - s ))s $(date -Is)"; [ $rc = 0 ] || tail -20 $B/build-$t.log
done
echo "== done $(date -Is)"

# ginkgo_build.sh -- sourced by target.sh (ginkgo-1, ginkgo-5).  R1 with a DIRECT LAUNCH driver (the cheaper legitimate variant the
# record names): the project's own CMake CONFIGURE step (no build of the Ginkgo libraries) generates include/ginkgo/config.hpp and the
# CUDA backend's compile flags; the driver is compiled with exactly those flags (cuda/CMakeFiles/ginkgo_cuda.dir/flags.make: CUDA_DEFINES,
# CUDA_FLAGS, include list) plus $RW_LINEINFO, against the checked-out revision's headers/sources.
#   ginkgo_build <driver.cu> [extra nvcc args...]     cwd = $OUT, sources in $SRC (whole ginkgo tree of the commit)
ginkgo_build() {
  local drv=$1; shift
  local cc
  cc=$(printf '%s' "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  cmake -S "$SRC" -B cfg -DCMAKE_BUILD_TYPE=Release -DGINKGO_BUILD_CUDA=ON -DGINKGO_BUILD_OMP=OFF -DGINKGO_BUILD_HIP=OFF -DGINKGO_BUILD_SYCL=OFF \
    -DGINKGO_BUILD_MPI=OFF -DGINKGO_BUILD_TESTS=OFF -DGINKGO_BUILD_EXAMPLES=OFF -DGINKGO_BUILD_BENCHMARKS=OFF -DGINKGO_BUILD_DOC=OFF \
    -DCMAKE_CUDA_ARCHITECTURES=$cc > cmake.log 2>&1 || { tail -30 cmake.log; return 1; }
  local fl=cfg/cuda/CMakeFiles/ginkgo_cuda.dir/flags.make
  local defs flags rsp gcclib
  gcclib=$(dirname "$(readlink -f "$(g++ -print-file-name=libstdc++.so)")")
  defs=$(sed -n 's/^CUDA_DEFINES = //p' $fl)
  flags=$(sed -n 's/^CUDA_FLAGS = //p' $fl)
  rsp=cfg/cuda/CMakeFiles/ginkgo_cuda.dir/includes_CUDA.rsp
  [ -n "$flags" ] && [ -s "$rsp" ] || { echo "ginkgo_build: no CUDA flags in $fl"; return 1; }
  # the project's flags: -O3 -DNDEBUG -std=c++17 --generate-code=arch=compute_$cc,code=[compute_$cc,sm_$cc] ... (exact SASS for sm_$cc plus PTX)
  echo "nvcc $defs $flags $RW_LINEINFO --options-file $rsp -Xlinker=-rpath,$gcclib $* -o driver $drv" | tee nvcc_cmd.txt
  set -f
  nvcc $defs $flags $RW_LINEINFO --options-file "$rsp" -Xlinker=-rpath,$gcclib "$@" -o driver "$drv" > nvcc.log 2>&1
  local rc=$?
  set +f
  [ $rc -eq 0 ] || { grep -n -E "error|Error" nvcc.log | head -30; tail -5 nvcc.log; return 1; }
  return 0
}

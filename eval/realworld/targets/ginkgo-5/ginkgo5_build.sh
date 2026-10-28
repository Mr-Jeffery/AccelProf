# ginkgo5_build.sh -- sourced by target.sh.  R1 (direct-launch variant): the project's own CMake CONFIGURE step, then ONLY the
# translation units needed to create a CudaExecutor and run compute_lookup_small/large are compiled, each with the compile command
# CMake generated for it (compile_commands.json: the project's flags/defines/includes, -O3 -DNDEBUG, CUDA arch from $RW_NVCC_FLAGS),
# and linked with the driver.  The full Ginkgo libraries (hundreds of heavy template TUs) are NOT built.
# cwd = $OUT, sources in $SRC (whole ginkgo tree), $RW_NVCC_FLAGS $RW_LINEINFO $NJOBS honoured.
GK5_CORE="core/base/array.cpp core/base/executor.cpp core/base/memory.cpp core/base/timer.cpp core/base/version.cpp core/log/logger.cpp"
GK5_CUDA="cuda/base/device.cpp cuda/base/exception.cpp cuda/base/executor.cpp cuda/base/memory.cpp cuda/base/nvtx.cpp cuda/base/scoped_device_id.cpp cuda/base/stream.cpp cuda/base/timer.cpp cuda/base/version.cpp"
GK5_DEV="devices/machine_topology.cpp devices/device.cpp devices/cuda/executor.cpp devices/omp/executor.cpp devices/hip/executor.cpp devices/dpcpp/executor.cpp devices/reference/dummy.cpp core/device_hooks/dpcpp_hooks.cpp core/device_hooks/hip_hooks.cpp core/device_hooks/omp_hooks.cpp core/device_hooks/reference_hooks.cpp"
GK5_KERNELS="common/unified/components/range_minimum_query_kernels.cpp common/unified/components/reduce_array_kernels.cpp common/unified/components/precision_conversion_kernels.cpp"

ginkgo5_build() {
  local drv=$1
  local cc gcclib
  cc=$(printf '%s' "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  gcclib=$(dirname "$(readlink -f "$(g++ -print-file-name=libstdc++.so)")")
  cp "$TDIR/rw_cuda13_compat.h" "$PWD/rw_cuda13_compat.h"
  cmake -S "$SRC" -B cfg -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DGINKGO_BUILD_CUDA=ON -DGINKGO_BUILD_OMP=OFF -DGINKGO_BUILD_HIP=OFF \
    -DGINKGO_BUILD_SYCL=OFF -DGINKGO_BUILD_REFERENCE=OFF -DGINKGO_BUILD_MPI=OFF -DGINKGO_BUILD_TESTS=OFF -DGINKGO_BUILD_EXAMPLES=OFF \
    -DGINKGO_BUILD_BENCHMARKS=OFF -DGINKGO_BUILD_DOC=OFF -DCMAKE_CUDA_ARCHITECTURES=$cc > cmake.log 2>&1 || { tail -30 cmake.log; return 1; }
  # extra flags, identical for both variants: -fpermissive (gcc 12.4 rejects a duplicate explicit instantiation in core/base/array.cpp),
  # section flags (so the linker can drop the unused array<T>::fill instantiations, whose kernels are in a TU nvcc 13 rejects),
  # the cuFFT enumerator compat pre-include; -lineinfo for the CUDA-language TUs.
  local xcxx="-fpermissive -ffunction-sections -fdata-sections -include $PWD/rw_cuda13_compat.h"
  local xnvcc="${RW_LINEINFO:--}"
  python3 "$TDIR/gk_subset.py" cfg/compile_commands.json "$SRC" objs "$xcxx" "$xnvcc" $GK5_CORE $GK5_CUDA $GK5_DEV $GK5_KERNELS > subset.log 2>&1
  local rc=$?
  cat subset.log | grep -v "rc=0" | head -20
  [ $rc -eq 0 ] || { for f in objs/*.err; do [ -e "$f" ] && { echo "== $f"; grep -E "error" "$f" | head -5 | cut -c1-300; }; done; return 1; }
  # the driver: host code compiled like a core translation unit
  local fl=cfg/core/CMakeFiles/ginkgo.dir/flags.make defs inc cxxf
  defs=$(sed -n 's/^CXX_DEFINES = //p' $fl); inc=$(sed -n 's/^CXX_INCLUDES = //p' $fl); cxxf=$(sed -n 's/^CXX_FLAGS = //p' $fl)
  echo "g++ $defs $inc $cxxf -fpermissive -I$CUDA_HOME/include -c driver.cpp" | tee driver_cmd.txt
  g++ $defs $inc $cxxf -fpermissive -I"$CUDA_HOME/include" -c "$drv" -o objs/zz_driver.o > driver_compile.log 2>&1 || { grep -E "error" driver_compile.log | head -20 | cut -c1-300; return 1; }
  echo "nvcc -o driver objs/*.o -Xlinker --gc-sections -Xlinker -rpath,$CUDA_HOME/lib64 -Xlinker -rpath,$gcclib -lcublas -lcusparse -lcurand -lcufft" | tee -a driver_cmd.txt
  nvcc -o driver objs/*.o -Xlinker --gc-sections -Xlinker -rpath,"$CUDA_HOME/lib64" -Xlinker -rpath,"$gcclib" -lcublas -lcusparse -lcurand -lcufft > link.log 2>&1 \
    || { grep -E "undefined|error" link.log | head -20 | cut -c1-300; return 1; }
  # record the compile command of the kernel TU
  python3 - > kernel_tu_cmd.txt <<PYEOF
import json, os
src = os.path.realpath("$SRC")
for e in json.load(open("cfg/compile_commands.json")):
    if os.path.realpath(e["file"]).endswith("common/unified/components/range_minimum_query_kernels.cpp"):
        print(e["command"])
PYEOF
  return 0
}

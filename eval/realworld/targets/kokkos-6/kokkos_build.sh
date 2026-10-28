# kokkos_build.sh -- sourced by target.sh.  R1: the project's own CMake build of Kokkos (CUDA backend), in-tree via
# add_subdirectory (Kokkos' documented way to embed it), plus ONE driver executable linked to Kokkos::kokkoscore.
# cwd = $OUT (node-local), sources in $SRC (whole kokkos tree of the commit).  Honours $RW_NVCC_FLAGS $RW_LINEINFO $NJOBS.
#   kokkos_build <driver.cpp> [extra cmake args...]
# Arch: neither Kokkos revision used by T21a (3.6.99 db1a77d/8741579, 3.7.99 af65233/7176188) has the ADA89 keyword
# (Ada support came with Kokkos 4.0).  Kokkos' own recommendation for Ada before that is Kokkos_ARCH_AMPERE86; that keyword
# makes the build emit -arch=sm_86, which the CXX wrapper below rewrites to the arch of $RW_NVCC_FLAGS (sm_89, or sm_75 for
# the smoke build), so the flags are identical for both variants and the result is exact SASS for the target arch.
kokkos_build() {
  local drv=$1; shift
  local cc kw
  cc=$(printf '%s' "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  case $cc in
    75) kw=TURING75 ;;
    80) kw=AMPERE80 ;;
    86|89) kw=AMPERE86 ;;
    *) echo "kokkos_build: no Kokkos arch keyword for sm_$cc"; return 2 ;;
  esac
  mkdir -p wrap proj
  cat > wrap/nvcc_wrapper <<EOF
#!/bin/bash
# T21a: replaces the -arch=sm_86 that Kokkos_ARCH_$kw emits by -arch=sm_$cc (see kokkos_build.sh)
# nvcc_wrapper hard-codes -arch=sm_35 when no -arch is given (CMake's compiler try-compile), which nvcc 13 rejects: give it the target arch
a=(); have=0
for x in "\$@"; do case "\$x" in -arch=*|-arch|-gencode*) have=1;; esac; a+=("\${x//sm_86/sm_$cc}"); done
[ \$have = 1 ] || a+=("-arch=sm_$cc")
exec "$SRC/bin/nvcc_wrapper" "\${a[@]}"
EOF
  chmod +x wrap/nvcc_wrapper
  cp "$drv" proj/driver.cpp
  cat > proj/CMakeLists.txt <<EOF
cmake_minimum_required(VERSION 3.18)
project(rwdriver CXX)
add_subdirectory($SRC kokkos)
add_executable(driver driver.cpp)
target_link_libraries(driver Kokkos::kokkoscore)
EOF
  export NVCC_WRAPPER_DEFAULT_COMPILER=$(command -v g++)
  # toolkit-compat pre-include (CUDA >= 12.2 vs. Kokkos 3.6/3.7 half-conversion header), see rw_cuda_compat.h.  nvcc_wrapper
  # forwards unknown flags only to the host compiler, so use nvcc's own NVCC_APPEND_FLAGS (applies to every nvcc call).
  cp "$TDIR/rw_cuda_compat.h" "$PWD/rw_cuda_compat.h"
  export NVCC_APPEND_FLAGS="-include $PWD/rw_cuda_compat.h"
  local args="-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=$PWD/wrap/nvcc_wrapper -DCMAKE_CXX_FLAGS=$RW_LINEINFO
 -DKokkos_ENABLE_CUDA=ON -DKokkos_ARCH_$kw=ON -DKokkos_ENABLE_SERIAL=ON -DKokkos_ENABLE_TESTS=OFF -DKokkos_ENABLE_EXAMPLES=OFF"
  echo "cmake args: $args $*  (host g++ $NVCC_WRAPPER_DEFAULT_COMPILER, nvcc $(nvcc --version | tail -1), NVCC_APPEND_FLAGS=$NVCC_APPEND_FLAGS)" | tee cmake_args.txt
  cmake -S proj -B bld $args "$@" > cmake.log 2>&1 || { tail -30 cmake.log; return 1; }
  make -C bld -j"${NJOBS:-8}" driver > make.log 2>&1 || { grep -n -E "error|Error" make.log | head -30; tail -15 make.log; return 1; }
  # relocatable: Kokkos' CMake links the shared libcudart.so.13 and sets no rpath; relink the driver with the static CUDA runtime
  # (nvcc adds -lcudart_static itself once the .so is dropped) and an rpath to the gcc-12.4 libstdc++ dir; needs only libcuda.so.1 + system libs.
  local gcclib; gcclib=$(dirname "$(readlink -f "$(g++ -print-file-name=libstdc++.so)")")
  ( cd bld && sed -E "s# [^ ]*/libcudart\.so##; s#\$# -Wl,-rpath,$gcclib#" CMakeFiles/driver.dir/link.txt > relink.sh && sh relink.sh ) > relink.log 2>&1 \
    || { echo "relink failed"; cat relink.log | tail -20; return 1; }
  cp bld/driver driver
  { echo "# compile and link commands of the driver target"; cat bld/CMakeFiles/driver.dir/flags.make bld/CMakeFiles/driver.dir/link.txt; echo "# relink actually used (static cudart, rpath to gcc libstdc++):"; cat bld/relink.sh; echo "# note: -arch=sm_86 above is rewritten to -arch=sm_$cc by wrap/nvcc_wrapper (cc from RW_NVCC_FLAGS)"; } > build_flags.txt
  return 0
}

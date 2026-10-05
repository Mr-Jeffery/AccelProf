#!/usr/bin/env bash
#SBATCH --job-name=t2-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t2-build-%j.log
# T2 private runtime: the worktree changes the collector (nv-compute) AND sanalyzer, so
# both are rebuilt -- sanalyzer into <W>/sanalyzer/wt_install, the collector into
# <W>/wt_nvc_lib (the Makefile's LIB_DIR overridden: the worktree's nv-compute/lib is a
# symlink to the main checkout's objects, which must not be overwritten) -- and <W>/lib
# then points at <W>/wt_rt_lib holding that collector. The gpu_patch fatbins still come
# from $ACCEL_PROF_HOME/nv-compute/lib/gpu_patch (unchanged device code). Toolchain as the
# live library: GCC 12.4.0 /opt/ohpc, -g -O3 -mtune=znver4.
#   sbatch -p normal eval/baselines/setup/t2_build.sh
set -e
W=${W:-/home/fzheng4/wt-T2}
A=/home/fzheng4/AccelProf
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -- sanalyzer nv-compute | wc -l) $($GXX --version | head -1)"
cd "$W/sanalyzer"
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$A/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$W/sanalyzer/wt_install 2>&1 | grep -v "^\s*$" | tail -4
cd "$W/nv-compute"
make -j16 DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX LIB_DIR=$W/wt_nvc_lib \
    SANALYZER_DIR=$W/sanalyzer/wt_install TORCH_SCOPE_DIR=$A/build/tensor_scope \
    PATCH_SRC_DIR=$W/nv-compute/gpu_src dirs $W/wt_nvc_lib/libcompute_sanitizer.so 2>&1 | tail -4
mkdir -p "$W/wt_rt_lib"
cp "$W/wt_nvc_lib/libcompute_sanitizer.so" "$W/wt_rt_lib/"
[ -L "$W/lib" ] && ln -sfn "$W/wt_rt_lib" "$W/lib"
echo "lib -> $(readlink $W/lib)"
readelf -d $W/wt_rt_lib/libcompute_sanitizer.so | grep -i "rpath"
echo "collector sha256[:16] $(sha256sum $W/wt_rt_lib/libcompute_sanitizer.so | cut -c1-16)  libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
strings $W/wt_rt_lib/libcompute_sanitizer.so | grep -c YOSEMITE_HB_HOST_MEMCPY

#!/usr/bin/env bash
#SBATCH --job-name=t12-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/.claude/worktrees/feat-instance-gate/build_logs/t12-build-%j.log
# T12 private runtime (T9 recipe; T12 changes no gpu_src):
# sanalyzer -> <W>/sanalyzer/wt_install; the collector, compiled from <W>/nv-compute with its
# RPATH at that libsanalyzer -> <W>/wt_rt_lib, and <W>/lib (a private directory, not a
# symlink) gets it. nv-compute/lib (fatbins) stays the main checkout's. Nothing in the main
# checkout's build/ or lib/ is written.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t12_build.sh
set -e
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/feat-instance-gate}; A=/home/fzheng4/AccelProf
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
cd "$W/sanalyzer"
make -j8 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$W/sanalyzer/wt_install 2>&1 | grep -v "^\s*$" | tail -5
L=$W/wt_nvc_build; mkdir -p $L
cd "$W/nv-compute"
make -j8 DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX CUDA_PATH=$CUDA_PATH LIB_DIR=$L \
    SANALYZER_DIR=$W/sanalyzer/wt_install TORCH_SCOPE_DIR=$A/build/tensor_scope \
    PATCH_SRC_DIR=$W/nv-compute/gpu_src dirs $L/libcompute_sanitizer.so 2>&1 | tail -3
mkdir -p "$W/wt_rt_lib"; cp "$L/libcompute_sanitizer.so" "$W/wt_rt_lib/"
cp "$L/libcompute_sanitizer.so" "$W/lib/libcompute_sanitizer.so"
readelf -d $W/lib/libcompute_sanitizer.so | grep -i "rpath\|runpath"
echo "collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"

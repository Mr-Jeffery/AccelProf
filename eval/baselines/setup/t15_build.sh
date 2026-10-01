#!/usr/bin/env bash
#SBATCH --job-name=t15-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=00:40:00
# T15 private runtime (eval/LATE_SEQ.md), after t1a_build.sh: sanalyzer -> <W>/sanalyzer/wt_install;
# the collector AND the pc_dependency device patch (gpu_src changed: the late key) ->
# <W>/wt_nvc_lib (the other tools' fatbins are copied from the main checkout: their device
# code is unchanged and gpu_patch.h only appends tracker fields they never read);
# <W>/nv-compute/lib -> wt_nvc_lib and <W>/lib -> wt_rt_lib. nvcc 13.3: run on a GPU node.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t15-build-%j.log \
#       eval/baselines/setup/t15_build.sh
set -e
W=${W:?set W=<task worktree>}; A=/home/fzheng4/AccelProf
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) $(nvcc --version | tail -1)"
cd "$W/sanalyzer"
make -j8 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$W/sanalyzer/wt_install 2>&1 | grep -E "error|warning: unused|Error" | head -20 || true
test -f $W/sanalyzer/wt_install/lib/libsanalyzer.so
L=$W/wt_nvc_lib; mkdir -p $L/gpu_patch
cp -n $A/nv-compute/lib/gpu_patch/*.fatbin $L/gpu_patch/
rm -f $L/gpu_patch/gpu_patch_pc_dependency.fatbin $L/libcompute_sanitizer.so
cd "$W/nv-compute"
make -j8 DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX CUDA_PATH=$CUDA_PATH LIB_DIR=$L \
    SANALYZER_DIR=$W/sanalyzer/wt_install TORCH_SCOPE_DIR=$A/build/tensor_scope \
    PATCH_SRC_DIR=$W/nv-compute/gpu_src dirs $L/libcompute_sanitizer.so \
    $L/gpu_patch/gpu_patch_pc_dependency.fatbin 2>&1 | grep -E "error|Error" | head -20 || true
test -f $L/libcompute_sanitizer.so && test -f $L/gpu_patch/gpu_patch_pc_dependency.fatbin
mkdir -p "$W/wt_rt_lib"; cp "$L/libcompute_sanitizer.so" "$W/wt_rt_lib/"
ln -sfn "$W/wt_rt_lib" "$W/lib"
ln -sfn "$L" "$W/nv-compute/lib"
echo "lib -> $(readlink $W/lib); nv-compute/lib -> $(readlink $W/nv-compute/lib)"
echo "collector $(sha256sum $W/wt_rt_lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) fatbin $(sha256sum $L/gpu_patch/gpu_patch_pc_dependency.fatbin | cut -c1-16)"

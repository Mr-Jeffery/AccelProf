#!/usr/bin/env bash
#SBATCH --job-name=t18-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t18-build-%j.log
# T18: build BOTH runtime components from the worktree W (sanalyzer + collector + the two
# pc_dependency device-patch fatbins: default, no late-key code; _late, HB_LATE_SEQ) into a
# stage directory S, and, with INSTALL=1, install them over the live runtime with backups
# (<file>.pre-t18-<sha16>), as t17_install.sh did.
#   W=/home/fzheng4/wt-t18 [INSTALL=1] sbatch -p rtx4060ti8g -x c21,c22,c34,c54,c2 eval/baselines/setup/t18_build.sh
set -e
W=${W:?set W=<worktree>}; A=/home/fzheng4/AccelProf; S=/home/fzheng4/t18-stage
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
h() { sha256sum "$1" | cut -c1-16; }
LS=$A/build/sanalyzer/lib/libsanalyzer.so; LC=$A/lib/libcompute_sanitizer.so
LF=$A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin; LL=${LF%.fatbin}_late.fatbin
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) $(nvcc --version | tail -1)"
echo "before: libsanalyzer $(h $LS) collector $(h $LC) fatbin $(h $LF)"
rm -rf $S; mkdir -p $S
cd $W/sanalyzer
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX OBJ_DIR=$S/san-obj LIB_DIR=$S/san-lib \
    SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$S/san-install > $S/san.log 2>&1 || { tail -30 $S/san.log; exit 1; }
cd $W/nv-compute
make -j16 DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX CUDA_PATH=$CUDA_PATH LIB_DIR=$S/nvc \
    SANALYZER_DIR=$S/san-install TORCH_SCOPE_DIR=$A/build/tensor_scope \
    PATCH_SRC_DIR=$W/nv-compute/gpu_src dirs $S/nvc/libcompute_sanitizer.so \
    $S/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin \
    $S/nvc/gpu_patch/gpu_patch_pc_dependency_late.fatbin > $S/nvc.log 2>&1 || { tail -30 $S/nvc.log; exit 1; }
echo "built: libsanalyzer $(h $S/san-install/lib/libsanalyzer.so) collector $(h $S/nvc/libcompute_sanitizer.so) fatbin $(h $S/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin) late $(h $S/nvc/gpu_patch/gpu_patch_pc_dependency_late.fatbin)"
[ "${INSTALL:-0}" = 1 ] || exit 0
for f in $LS $LC $LF; do cp -p $f $f.pre-t18-$(h $f); done
cp $S/san-install/lib/libsanalyzer.so $LS.new && mv $LS.new $LS
cp $S/san-install/include/sanalyzer.h $A/build/sanalyzer/include/sanalyzer.h
# relink the collector against the INSTALLED library (RPATH build/sanalyzer/lib, not the stage)
$GXX -L$CUDA_PATH/compute-sanitizer -L$A/build/sanalyzer/lib -Wl,-rpath=$A/build/sanalyzer/lib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $LC.new $S/nvc/obj/*.o -lsanitizer-public -lsanalyzer -ltorch_scope
mv $LC.new $LC
cp $S/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin $LF.new && mv $LF.new $LF
cp $S/nvc/gpu_patch/gpu_patch_pc_dependency_late.fatbin $LL
echo "after: libsanalyzer $(h $LS) collector $(h $LC) fatbin $(h $LF) late $(h $LL)"
readelf -d $LC | grep -i rpath; ldd $LC | grep sanalyzer

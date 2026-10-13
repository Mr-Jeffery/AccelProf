#!/usr/bin/env bash
#SBATCH --job-name=t17-install
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t17-install-%j.log
# T17 merge (cuVein b6c9055 = T15 late-seq + T17 rename): rebuild BOTH runtime components from
# the merged tree and install them over the live runtime. T15 changed the device patch and
# the collector, so the T12-era collector 7bafac9f / fatbin a2d7368b are stale.
#  0. previous runtime kept as a private mirror at $P (a detached worktree): its
#     libsanalyzer (copy of the live e527875d), the live gpu_patch fatbins, and the T1a
#     collector objects the live 7bafac9f was linked from, relinked with RPATH -> $P/sanlib;
#  1. backups <file>.pre-t17-<sha16> beside each live file;
#  2. sanalyzer, fresh objects, `make install` into build/sanalyzer (lib + sanalyzer.h);
#  3. collector + pc_dependency fatbin (nvcc), fresh objects in $S, linked against the
#     installed libsanalyzer (RPATH build/sanalyzer/lib), copied over lib/ and
#     nv-compute/lib/gpu_patch/ (the other tools' fatbins unchanged, as in T15).
#   sbatch -p rtx4060ti8g -x c21,c22,c34,c54,c2 eval/baselines/setup/t17_install.sh
set -e
A=/home/fzheng4/AccelProf; P=/home/fzheng4/rt-prev-e527875d; S=/home/fzheng4/t17-stage
OBJ=/home/fzheng4/wt-T1a-review/install_stage/obj
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
h() { sha256sum "$1" | cut -c1-16; }
LS=$A/build/sanalyzer/lib/libsanalyzer.so; LC=$A/lib/libcompute_sanitizer.so
LF=$A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin; LH=$A/build/sanalyzer/include/sanalyzer.h
echo "host=$(hostname) HEAD=$(git -C $A rev-parse --short HEAD) dirty=$(git -C $A status --porcelain -uno | wc -l) $(nvcc --version | tail -1)"
echo "before: libsanalyzer $(h $LS) collector $(h $LC) fatbin $(h $LF) sanalyzer.h $(h $LH)"

# 0. previous-runtime mirror
mkdir -p $P/sanlib $P/lib $P/nv-compute/lib
cp -p $LS $P/sanlib/libsanalyzer.so
cp -a $A/nv-compute/lib/gpu_patch $P/nv-compute/lib/
$GXX -L$CUDA_PATH/compute-sanitizer -L$P/sanlib -Wl,-rpath=$P/sanlib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $P/lib/libcompute_sanitizer.so $OBJ/compute_sanitizer.o $OBJ/sanitizer_helper.o \
    -lsanitizer-public -lsanalyzer -ltorch_scope
echo "prev mirror: libsanalyzer $(h $P/sanlib/libsanalyzer.so) collector(relinked) $(h $P/lib/libcompute_sanitizer.so) fatbin $(h $P/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"

# 1. backups
for f in $LS $LC $LF $LH; do cp -p $f $f.pre-t17-$(h $f); done

# 2. sanalyzer
rm -rf $S; mkdir -p $S
cd $A/sanalyzer
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX OBJ_DIR=$S/san-obj LIB_DIR=$S/san-lib \
    SANITIZER_TOOL_DIR=$A/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$A/build/sanalyzer > $S/san.log 2>&1 || { tail -30 $S/san.log; exit 1; }
grep -E "error|warning" $S/san.log | head -10 || true

# 3. collector + device patch
cd $A/nv-compute
make -j16 DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX CUDA_PATH=$CUDA_PATH LIB_DIR=$S/nvc \
    SANALYZER_DIR=$A/build/sanalyzer TORCH_SCOPE_DIR=$A/build/tensor_scope \
    PATCH_SRC_DIR=$A/nv-compute/gpu_src dirs $S/nvc/libcompute_sanitizer.so \
    $S/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin > $S/nvc.log 2>&1 || { tail -30 $S/nvc.log; exit 1; }
grep -E "error|warning" $S/nvc.log | head -10 || true
cp $S/nvc/libcompute_sanitizer.so $LC.new && mv $LC.new $LC
cp $S/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin $LF.new && mv $LF.new $LF
echo "after: libsanalyzer $(h $LS) collector $(h $LC) fatbin $(h $LF) sanalyzer.h $(h $LH)"
readelf -d $LC | grep -i rpath
ldd $LC | grep sanalyzer

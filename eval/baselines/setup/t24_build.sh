#!/usr/bin/env bash
#SBATCH --job-name=t24-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=01:00:00
# T24 private runtime (T22's pattern: install_merged.sh with INSTALL=0 for the library, t22c_build.sh's
# relink for the collector): libsanalyzer from the worktree W into the stage S, and the collector
# relinked from the installed build's objects (stage-t22t23-59a98aa/nvc/obj: nothing under
# nv-compute/ changes in T24) with RPATH to S's library, into S/rt-lib. W/lib -> S/rt-lib makes W
# the runtime (ACCEL_PROF_HOME=W). Nothing installed is written: build/sanalyzer/lib, lib/ and
# nv-compute/lib of the main checkout are only read.
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-build-%j.log <W>/eval/baselines/setup/t24_build.sh
set -e
W=${W:-/home/fzheng4/wt-t24}; A=/home/fzheng4/AccelProf; S=${S:-/home/fzheng4/stage-t24}
OBJ=/home/fzheng4/stage-t22t23-59a98aa/nvc/obj
for d in $A /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($GXX --version | head -1) $(date -Is)"
echo "installed (read only): libsanalyzer $(h $A/build/sanalyzer/lib/libsanalyzer.so) collector $(h $A/lib/libcompute_sanitizer.so)"
rm -rf $S/san-obj $S/san-lib $S/san-install $S/rt-lib; mkdir -p $S
cd $W/sanalyzer
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX OBJ_DIR=$S/san-obj LIB_DIR=$S/san-lib \
    SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$S/san-install > $S/san.log 2>&1 || { grep -E " error|Error" $S/san.log | head -30; exit 1; }
grep -E " error|warning:" $S/san.log | head -10 || true
mkdir -p $S/rt-lib
( cd $A/nv-compute && $GXX -L$CUDA_PATH/compute-sanitizer -L$S/san-install/lib -Wl,-rpath=$S/san-install/lib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $S/rt-lib/libcompute_sanitizer.so $OBJ/*.o -lsanitizer-public -lsanalyzer -ltorch_scope )
echo "built: libsanalyzer $(h $S/san-install/lib/libsanalyzer.so) collector $(h $S/rt-lib/libcompute_sanitizer.so)"
readelf -d $S/rt-lib/libcompute_sanitizer.so | grep -i rpath
ldd $S/rt-lib/libcompute_sanitizer.so | grep sanalyzer
echo "installed after (unchanged): libsanalyzer $(h $A/build/sanalyzer/lib/libsanalyzer.so) collector $(h $A/lib/libcompute_sanitizer.so)"
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=t26-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=01:00:00
# T26 private runtime (t24_build.sh's pattern): libsanalyzer from the worktree W into the stage S, and
# the collector relinked from the installed build's objects (stage-t24-e0e6431/nvc/obj: nothing under
# nv-compute/ changes in T26) with RPATH to S's library, into S/rt-lib. W/lib -> S/rt-lib makes W the
# runtime (ACCEL_PROF_HOME=W). Also the parity tools (t26_parity/): the capture shim (a libsanalyzer.so
# that records every yosemite_* call and forwards it to CAP_REAL_LIB) with a collector relinked against
# it (S/cap-rt-lib), and the replay driver. Nothing installed is written: build/sanalyzer/lib, lib/ and
# nv-compute/lib of the main checkout are only read.
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t26-build-%j.log <W>/eval/baselines/setup/t26_build.sh
set -e
W=${W:-/home/fzheng4/wt/sharded-pcdep}; A=/home/fzheng4/AccelProf; S=${S:-/home/fzheng4/stage-t26}
OBJ=/home/fzheng4/stage-t24-e0e6431/nvc/obj
P=$W/eval/baselines/setup/t26_parity
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($GXX --version | head -1) $(date -Is)"
echo "installed (read only): libsanalyzer $(h $A/build/sanalyzer/lib/libsanalyzer.so) collector $(h $A/lib/libcompute_sanitizer.so)"
link_collector() {   # $1 = dir holding the libsanalyzer.so to link, $2 = output dir
  ( cd $A/nv-compute && $GXX -L$CUDA_PATH/compute-sanitizer -L$1 -Wl,-rpath=$1 \
      -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
      -fPIC -shared -o $2/libcompute_sanitizer.so $OBJ/*.o -lsanitizer-public -lsanalyzer -ltorch_scope )
}
if [ -z "${CAP_ONLY:-}" ]; then   # CAP_ONLY=1: rebuild the parity tools only, the library stays
  rm -rf $S/san-obj $S/san-lib $S/san-install $S/rt-lib $S/cap-lib $S/cap-rt-lib $S/bin; mkdir -p $S
  cd $W/sanalyzer
  make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX OBJ_DIR=$S/san-obj LIB_DIR=$S/san-lib \
      SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
      CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
      INSTALL_DIR=$S/san-install > $S/san.log 2>&1 || { grep -E " error|Error" $S/san.log | head -30; exit 1; }
  grep -E " error|warning:" $S/san.log | head -20 || true
  mkdir -p $S/rt-lib
  link_collector $S/san-install/lib $S/rt-lib
fi
mkdir -p $S/cap-lib $S/cap-rt-lib $S/bin
# parity tools: the shim is named libsanalyzer.so so the relinked collector's RPATH loads it
$GXX -std=c++17 -O2 -fPIC -shared -I$W/sanalyzer/include -o $S/cap-lib/libsanalyzer.so $P/capture_shim.cpp -ldl -lpthread
link_collector $S/cap-lib $S/cap-rt-lib
# the replay driver links libsanalyzer without an RPATH: LD_LIBRARY_PATH picks the library under test
$GXX -std=c++17 -O2 -I$W/sanalyzer/include -I$W/nv-compute/gpu_src/include -o $S/bin/${REPLAY_OUT:-t26_replay} $P/replay.cpp \
    -L$S/san-install/lib -lsanalyzer
echo "built: libsanalyzer $(h $S/san-install/lib/libsanalyzer.so) collector $(h $S/rt-lib/libcompute_sanitizer.so)"
echo "parity: shim $(h $S/cap-lib/libsanalyzer.so) capture collector $(h $S/cap-rt-lib/libcompute_sanitizer.so) replay $(h $S/bin/${REPLAY_OUT:-t26_replay})"
readelf -d $S/rt-lib/libcompute_sanitizer.so | grep -i rpath
ldd $S/rt-lib/libcompute_sanitizer.so | grep sanalyzer
ldd $S/cap-rt-lib/libcompute_sanitizer.so | grep sanalyzer
echo "installed after (unchanged): libsanalyzer $(h $A/build/sanalyzer/lib/libsanalyzer.so) collector $(h $A/lib/libcompute_sanitizer.so)"
echo "== done $(date -Is)"

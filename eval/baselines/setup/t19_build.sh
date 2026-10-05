#!/usr/bin/env bash
#SBATCH --job-name=t19-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t19-build-%j.log
# T19 (flat buckets): private runtime for the worktree W -- its sanalyzer into
# <W>/sanalyzer/wt_install and a private collector relinked from the objects the INSTALLED
# collector was linked from (d67ed41 install: /home/fzheng4/stage-merge-d67ed41/nvc/obj,
# collector 1c896ce0) with RPATH -> the private library, so ACCEL_PROF_HOME=<W> with <W>/lib ->
# <W>/wt_rt_lib runs the worktree's analyzer with the installed fatbins; the shared
# build/sanalyzer/lib stays untouched. T19 changes no collector or device source (as t4_build.sh).
#   W=<worktree> sbatch -p rtx4060ti8g -x c21,c22,c34,c54,c2 eval/baselines/setup/t19_build.sh
set -e
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}
A=/home/fzheng4/AccelProf
OBJ=${OBJ:-/home/fzheng4/stage-merge-d67ed41/nvc/obj}
INSTALL=${INSTALL:-$W/sanalyzer/wt_install}
RTLIB=${RTLIB:-$W/wt_rt_lib}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
CUDA=/usr/local/cuda
echo "host=$(hostname) W=$W OBJ=$OBJ HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($GXX --version | head -1)"
cd "$W/sanalyzer"
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$INSTALL 2>&1 | grep -E "error|warning|Error" | head -20 || true
[ -f $INSTALL/lib/libsanalyzer.so ] || { echo "no libsanalyzer built"; exit 1; }
mkdir -p "$RTLIB"
cd "$A/nv-compute"
$GXX -L$CUDA/compute-sanitizer \
    -L$INSTALL/lib -Wl,-rpath=$INSTALL/lib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $RTLIB/libcompute_sanitizer.so $OBJ/*.o \
    -lsanitizer-public -lsanalyzer -ltorch_scope
echo "lib -> $(readlink $W/lib)"
readelf -d $RTLIB/libcompute_sanitizer.so | grep -i "rpath"
echo "libsanalyzer sha256[:16] $(sha256sum $INSTALL/lib/libsanalyzer.so | cut -c1-16)  live: $(sha256sum $A/build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"
echo "collector sha256[:16] $(sha256sum $RTLIB/libcompute_sanitizer.so | cut -c1-16)  live: $(sha256sum $A/lib/libcompute_sanitizer.so | cut -c1-16)"
echo "== done $(date -Is)"

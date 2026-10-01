#!/usr/bin/env bash
#SBATCH --job-name=t4-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/wt-T4/build_logs/t4-build-%j.log
# T4 (no-dump mode): private runtime for the worktree W -- its sanalyzer into
# <W>/sanalyzer/wt_install and a private collector relinked from the objects the INSTALLED
# collector was linked from (T18: /home/fzheng4/t18-stage/nvc/obj, collector c9b862f9) with
# RPATH -> the private library, so ACCEL_PROF_HOME=<W> runs the worktree's analyzer with the
# installed fatbins (<W>/nv-compute/lib/gpu_patch -> the main checkout's) and the shared
# build/sanalyzer/lib stays untouched. T4 changes no collector source. Toolchain of the live
# library: GCC 12.4.0 /opt/ohpc, -g -O3 -mtune=znver4 (eval/MODE_RENAME.md section 3.1).
#   W=/home/fzheng4/wt-T4 sbatch -p normal eval/baselines/setup/t4_build.sh
set -e
W=${W:-/home/fzheng4/wt-T4}
A=/home/fzheng4/AccelProf
OBJ=${OBJ:-/home/fzheng4/t18-stage/nvc/obj}
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

#!/usr/bin/env bash
#SBATCH --job-name=wt-runtime
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/wt-runtime-%j.log
# Private detector runtime for a task worktree: build the worktree's sanalyzer into
# <W>/sanalyzer/wt_install and relink a PRIVATE copy of the collector
# (libcompute_sanitizer.so, from the main checkout's nv-compute objects, exactly as
# nv-compute/Makefile links it) whose RPATH points there; <W>/lib then points at that
# copy, so ACCEL_PROF_HOME=<W> runs the worktree's detector while the shared
# build/sanalyzer/lib stays untouched (replacing that is the user's call). Toolchain and
# flags of the live library (eval/MODE_RENAME.md section 3.1): GCC 12.4.0 /opt/ohpc,
# -g -O3 -mtune=znver4. The worktree's nv-nvbit submodule is empty, so the headers come
# from the main checkout. Collector (nv-compute) source changes need their own rebuild.
#   W=/home/fzheng4/wt-<task> sbatch -p normal eval/baselines/setup/wt_runtime.sh
set -e
W=${W:?set W=<task worktree>}
A=/home/fzheng4/AccelProf
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
CUDA=/usr/local/cuda
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) $($GXX --version | head -1)"
cd "$W/sanalyzer"
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$A/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$W/sanalyzer/wt_install 2>&1 | tail -5
mkdir -p "$W/wt_rt_lib"
cd "$A/nv-compute"
$GXX -L$CUDA/compute-sanitizer \
    -L$W/sanalyzer/wt_install/lib -Wl,-rpath=$W/sanalyzer/wt_install/lib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $W/wt_rt_lib/libcompute_sanitizer.so lib/obj/compute_sanitizer.o lib/obj/sanitizer_helper.o \
    -lsanitizer-public -lsanalyzer -ltorch_scope
[ -L "$W/lib" ] && ln -sfn "$W/wt_rt_lib" "$W/lib"
echo "lib -> $(readlink $W/lib)"
readelf -d $W/wt_rt_lib/libcompute_sanitizer.so | grep -i "rpath"
readelf -d $W/sanalyzer/wt_install/lib/libsanalyzer.so | grep -i "rpath"
echo "libsanalyzer sha256[:16] $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)  live: $(sha256sum $A/build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"

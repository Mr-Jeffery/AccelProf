#!/usr/bin/env bash
#SBATCH --job-name=t3b-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/wt-T3b/eval/baselines/setup/build_logs/t3b-build-%j.log
# T3b private runtime. Only libsanalyzer changes (pc_dependency_analysis.cpp: exit records
# serialized, exit-aware barrier assembly, TV-barrier-pending-at-end); the device code does
# not (BlockExitCallback already emits the records), so the live fatbins stay in use.
#   libsanalyzer  -> <W>/sanalyzer/wt_install/lib
#   collector     -> <W>/wt_rt_lib/libcompute_sanitizer.so, relinked from the objects of the
#                    installed collector (wt-T1a-review/install_stage/obj = live 7bafac9f) with
#                    its RPATH on the private libsanalyzer; <W>/lib -> wt_rt_lib.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t3b_build.sh
set -e
W=${W:-/home/fzheng4/wt-T3b}; A=/home/fzheng4/AccelProf
OBJ=/home/fzheng4/wt-T1a-review/install_stage/obj
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export CUDA_PATH=/usr/local/cuda-13.3; export PATH=$CUDA_PATH/bin:$PATH
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -- sanalyzer | wc -l)"
cd "$W/sanalyzer"
make -j8 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
    SANITIZER_TOOL_DIR=$A/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
    CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
    INSTALL_DIR=$W/sanalyzer/wt_install 2>&1 | grep -v "^\s*$" | tail -3
mkdir -p "$W/wt_rt_lib"
$GXX -L$CUDA_PATH/compute-sanitizer \
    -L$W/sanalyzer/wt_install/lib -Wl,-rpath=$W/sanalyzer/wt_install/lib \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $W/wt_rt_lib/libcompute_sanitizer.so $OBJ/compute_sanitizer.o $OBJ/sanitizer_helper.o \
    -lsanitizer-public -lsanalyzer -ltorch_scope
ln -sfn "$W/wt_rt_lib" "$W/lib"
readelf -d $W/wt_rt_lib/libcompute_sanitizer.so | grep -i "rpath"
T=$(mktemp -d)
readelf -d $A/lib/libcompute_sanitizer.so | grep NEEDED > $T/n_live; readelf -d $W/wt_rt_lib/libcompute_sanitizer.so | grep NEEDED > $T/n_new
diff $T/n_live $T/n_new && echo "NEEDED lists identical"
nm -D --defined-only $A/lib/libcompute_sanitizer.so | awk '{print $3}' | sort > $T/s_live
nm -D --defined-only $W/wt_rt_lib/libcompute_sanitizer.so | awk '{print $3}' | sort > $T/s_new
diff $T/s_live $T/s_new && echo "collector exported symbols identical"
nm -D --defined-only $A/build/sanalyzer/lib/libsanalyzer.so | awk '{print $3}' | sort > $T/l_live
nm -D --defined-only $W/sanalyzer/wt_install/lib/libsanalyzer.so | awk '{print $3}' | sort > $T/l_new
diff $T/l_live $T/l_new && echo "libsanalyzer exported symbols identical"
rm -rf $T
echo "collector $(sha256sum $W/wt_rt_lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"

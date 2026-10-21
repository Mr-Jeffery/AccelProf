#!/usr/bin/env bash
#SBATCH --job-name=t22c-build
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=01:30:00
# T22 cont. (Fix 1 adaptive tail, Fix 2 scalar-clock early exit): three private runtimes of the
# worktree W, each a libsanalyzer plus a collector relinked from the d67ed41 objects with RPATH to it
# (as t22_build.sh), and a runtime mirror per extra build (every top-level entry of W symlinked,
# lib -> that build's collector), so the harness runs it with ACCEL_PROF_HOME / W = the mirror:
#   old    libsanalyzer of b6a615e (the T22 build before the fixes), kept from wt_install before the
#          rebuild: wt_install_b6a615e + wt_rt_lib_b6a615e, mirror $M/rt-old
#   tune   this tree with -DHB_TAIL_TUNE (the tail rule read from YOSEMITE_HB_TAIL_C/_MAX):
#          wt_install_tune + wt_rt_lib_tune, mirror $M/rt-tune
#   final  this tree: wt_install + wt_rt_lib (W itself)
#   sbatch -p normal -o <W>/eval/baselines/setup/build_logs/t22c-build-%j.log eval/baselines/setup/t22c_build.sh
set -e
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
A=/home/fzheng4/AccelProf
OBJ=/home/fzheng4/stage-merge-d67ed41/nvc/obj
M=${M:-/mnt/beegfs/$USER/t22c}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
CUDA=/usr/local/cuda
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($GXX --version | head -1) $(date -Is)"
relink() {   # <install dir> <rt lib dir>
  mkdir -p "$2"
  ( cd "$A/nv-compute" && $GXX -L$CUDA/compute-sanitizer \
      -L$1/lib -Wl,-rpath=$1/lib \
      -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
      -fPIC -shared -o $2/libcompute_sanitizer.so $OBJ/*.o \
      -lsanitizer-public -lsanalyzer -ltorch_scope )
  echo "  $2/libcompute_sanitizer.so $(h $2/libcompute_sanitizer.so) rpath: $(readelf -d $2/libcompute_sanitizer.so | grep -i rpath | sed 's/.*\[//; s/\].*//')"
}
build() {    # <install dir> <extra flags>
  cd "$W/sanalyzer"
  rm -f obj/pc_dependency_analysis.o lib/libsanalyzer.so
  make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4 $2" CXX=$GXX \
      SANITIZER_TOOL_DIR=$W/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
      CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
      INSTALL_DIR=$1 > $W/eval/baselines/setup/build_logs/t22c-make-$(basename $1).log 2>&1 \
      || { grep -E " error|Error" $W/eval/baselines/setup/build_logs/t22c-make-$(basename $1).log | head -30; exit 1; }
  echo "  $1/lib/libsanalyzer.so $(h $1/lib/libsanalyzer.so) flags '$2'"
}
mirror() {   # <dir> <rt lib dir>
  rm -rf "$1"; mkdir -p "$1"
  for e in $(ls -A $W); do
    case $e in .git|lib) ;; *) ln -s $W/$e $1/$e ;; esac
  done
  ln -s $2 $1/lib
  echo "  mirror $1: lib -> $(readlink $1/lib)"
}
echo "== old (b6a615e)"
if [ ! -f $W/sanalyzer/wt_install_b6a615e/lib/libsanalyzer.so ]; then
  mkdir -p $W/sanalyzer/wt_install_b6a615e/lib
  cp -p $W/sanalyzer/wt_install/lib/libsanalyzer.so $W/sanalyzer/wt_install_b6a615e/lib/
fi
echo "  libsanalyzer $(h $W/sanalyzer/wt_install_b6a615e/lib/libsanalyzer.so) (expected d9c16d82d2465602)"
relink $W/sanalyzer/wt_install_b6a615e $W/wt_rt_lib_b6a615e
echo "== tune"
build $W/sanalyzer/wt_install_tune -DHB_TAIL_TUNE
relink $W/sanalyzer/wt_install_tune $W/wt_rt_lib_tune
echo "== final"
build $W/sanalyzer/wt_install ""
relink $W/sanalyzer/wt_install $W/wt_rt_lib
echo "== mirrors"
mirror $M/rt-old $W/wt_rt_lib_b6a615e
mirror $M/rt-tune $W/wt_rt_lib_tune
echo "installed libsanalyzer (not touched) $(h $A/build/sanalyzer/lib/libsanalyzer.so)"
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=x1f-bisect
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c[0-3],c[23-24],c37,c[39-40],c[50-56],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/x1f-bisect-%j.log
# X1-follow Part 2 (eval/X1_FOLLOW.md section 2): the bfs regression. For every merge on cuVein's
# first-parent history from the Sept-22 runtime (b7d463e) to the current one (ba99486, installed by
# d38d057; X0 4094187 changes no file under sanalyzer/ nv-compute/ bin/) that changes sanalyzer/,
# nv-compute/ or bin/: git archive of those trees (+ python/ for the candidate's own sidecar) into
# the BeeGFS scratch prefix S/<commit>/, both components built there with install_merged.sh's
# recipe (GCC 12.4, CUDA 13.3, -g -mtune=znver4) and NEVER installed; a private runtime S/<commit>/rt
# (bin/accelprof, lib/libcompute_sanitizer.so with RPATH -> S/<commit>/san-install/lib, the built
# gpu_patch_pc_dependency.fatbin, the installed runtime's other fatbins by symlink). Then P7-bfs-cuda
# scalar-clock at a 600 s cap, then vector-clock at the same cap (x1f_run.py; mode knob
# YOSEMITE_HB_NO_ENGINE=1 where the candidate has no YOSEMITE_HB_MODE, YOSEMITE_HB_DUMP=0 where it
# has the switch, YOSEMITE_HB_STATS=1 everywhere -- X1's configuration where the candidate has it).
# Culprit = the first candidate whose scalar-clock bfs run takes >= 60 s or hits the cap; then
# P7-nbody-cuda scalar-clock at 600 s on the culprit and on its predecessor. Also recorded: the first
# candidate whose vector-clock bfs run hits the 600 s cap, and nbody vector-clock at 600 s on it and on
# its predecessor (pre-T4 scalar-clock mode only dumps the trace, so the two crossings can differ). Controls on the
# installed runtime itself: bfs both modes, and bfs scalar-clock without YOSEMITE_HB_STATS.
# Same node for every run (c60-c72, EPYC 8124P, the hosts of X1's knn and nbody rows).
#   sbatch eval/baselines/setup/x1f_bisect.sh          (CANDS="<c> ..." to override the list)
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
RT=/home/fzheng4/AccelProf; A=$RT
source $W/eval/baselines/setup/home_quota_guard.sh
cd $RT || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_HB_DUMP
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
h() { sha256sum "$1" | cut -c1-16; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
[ -d /mnt/beegfs/$USER ] || { echo "NODE-PROBLEM $(hostname): BeeGFS not mounted"; exit 2; }
S=/mnt/beegfs/$USER/x1_follow/bisect; OUT=$W/eval/x1_follow/bisect
mkdir -p $S $OUT
echo "host=$(hostname) gpu=[$gpu] mem=$(free -g | awk '/Mem:/{print $2}')G cpu=[$(lscpu | sed -n 's/^Model name: *//p')] job=${SLURM_JOB_ID:-} $(date -Is)"
echo "harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l); installed: libsanalyzer $(h $RT/build/sanalyzer/lib/libsanalyzer.so) collector $(h $RT/lib/libcompute_sanitizer.so) fatbin $(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin); $($GXX --version | head -1); $(nvcc --version | tail -1)"
CANDS=${CANDS:-"b7d463e 1a45653 6d843e3 07d2798 bc32a1f 3331d35 0b64d34 ebc464f 870dbb6 33a985c be82754 b3bfdf3 7849a70 de565c0 b6c9055 0a25f7d d67ed41 3c7eefd d3f1e98 ba99486"}

build() {   # $1 = commit -> S/$1/rt, or return 1
  local c=$1 D=$S/$1 t0=$(date +%s)
  rm -rf $D; mkdir -p $D/src
  git -C $W archive $c sanalyzer nv-compute bin python | tar -x -C $D/src || return 1
  (cd $D/src/sanalyzer && make -j$(nproc) install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX \
      OBJ_DIR=$D/san-obj LIB_DIR=$D/san-lib SANITIZER_TOOL_DIR=$D/src/nv-compute NV_NVBIT_DIR=$A/nv-nvbit \
      CPP_TRACE_DIR=$A/build/sanalyzer/cpp_trace PY_FRAME_DIR=$A/build/sanalyzer/py_frame \
      INSTALL_DIR=$D/san-install > $D/san.log 2>&1) || { echo "BUILD-FAIL sanalyzer $c"; tail -20 $D/san.log; return 1; }
  (cd $D/src/nv-compute && make -j$(nproc) DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=$GXX CUDA_PATH=$CUDA_HOME \
      LIB_DIR=$D/nvc SANALYZER_DIR=$D/san-install TORCH_SCOPE_DIR=$A/build/tensor_scope \
      PATCH_SRC_DIR=$D/src/nv-compute/gpu_src dirs $D/nvc/libcompute_sanitizer.so \
      $D/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin > $D/nvc.log 2>&1) || { echo "BUILD-FAIL nv-compute $c"; tail -20 $D/nvc.log; return 1; }
  local R=$D/rt
  mkdir -p $R/bin $R/lib $R/nv-compute/lib/gpu_patch
  cp $D/src/bin/accelprof $R/bin/
  cp $D/nvc/libcompute_sanitizer.so $R/lib/
  for f in $A/nv-compute/lib/gpu_patch/*.fatbin; do ln -s $f $R/nv-compute/lib/gpu_patch/; done
  rm -f $R/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin
  cp $D/nvc/gpu_patch/gpu_patch_pc_dependency.fatbin $R/nv-compute/lib/gpu_patch/
  local san=$(ldd $R/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
  [ "$san" = "$D/san-install/lib/libsanalyzer.so" ] || { echo "BUILD-FAIL rpath $c -> [$san]"; return 1; }
  echo "BUILT $c $(git -C $W log -1 --format='%ad %s' --date=short $c | cut -c1-70) in $(( $(date +%s) - t0 )) s:" \
       "libsanalyzer $(h $san) collector $(h $R/lib/libcompute_sanitizer.so) fatbin $(h $R/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"
}

flags() {   # $1 = commit -> the x1f_run.py knob flags the candidate supports
  local c=$1 k="--hb-stats"
  git -C $W grep -q YOSEMITE_HB_MODE $c -- sanalyzer/src/tools/pc_dependency_analysis.cpp || k="$k --mode-knob no-engine"
  git -C $W grep -q YOSEMITE_HB_DUMP $c -- sanalyzer/src/tools/pc_dependency_analysis.cpp && k="$k --no-dump"
  echo "$k"
}

run() {   # id mode commit|installed name cap [extra x1f_run flags]
  local id=$1 mode=$2 c=$3 name=$4 cap=$5; shift 5
  if [ $c = installed ]; then rtd=$RT; fl="--no-dump"; sc=""
  else rtd=$S/$c/rt; fl=$(flags $c); sc="--sidecar-py $S/$c/src/python/atomic_scope_sidecar.py"; fi
  echo "== $name: $id $mode runtime=$rtd flags=[$fl $*] cap=${cap}s $(date -Is)"
  $PY $W/eval/baselines/setup/x1f_run.py --id $id --config $mode --workers 1 --cap $cap --runtime $rtd \
      $fl $sc "$@" --native-reps 3 --name $name --out $OUT --work $S/runs > $OUT/$name.driver.txt 2>&1
  tail -1 $OUT/$name.driver.txt
}

slow() {  # $1 = summary json, $2 = threshold (s) -> exit 0 if wall >= threshold or timed out
  $PY -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if (d['timed_out'] or (isinstance(d['wall'],(int,float)) and d['wall']>=float(sys.argv[2]))) else 1)" "$1" "$2"
}

run P7-bfs-cuda scalar-clock installed bfs-sc-installed 600 --hb-stats
run P7-bfs-cuda vector-clock installed bfs-vc-installed 600 --hb-stats
run P7-bfs-cuda scalar-clock installed bfs-sc-installed-nostats 600
prev=""; culprit=""; before=""; vculprit=""; vbefore=""
for c in $CANDS; do
  build $c || { echo "SKIP $c (build failed)"; continue; }
  run P7-bfs-cuda scalar-clock $c bfs-sc-$c 600
  run P7-bfs-cuda vector-clock $c bfs-vc-$c 600
  if [ -z "$culprit" ] && [ -f $OUT/bfs-sc-$c.json ] && slow $OUT/bfs-sc-$c.json 60; then culprit=$c; before=$prev; fi
  if [ -z "$vculprit" ] && [ -f $OUT/bfs-vc-$c.json ] && slow $OUT/bfs-vc-$c.json 600; then vculprit=$c; vbefore=$prev; fi
  prev=$c
done
echo "== culprit (first scalar-clock bfs run >= 60 s or capped): [${culprit}] predecessor [${before}]"
echo "== vector-clock: first bfs run at the 600 s cap: [${vculprit}] predecessor [${vbefore}]"
for c in $culprit $before; do
  [ -n "$c" ] && run P7-nbody-cuda scalar-clock $c nbody-sc-$c 600
done
for c in $vculprit $vbefore; do
  [ -n "$c" ] && run P7-nbody-cuda vector-clock $c nbody-vc-$c 600
done
echo "== done $(date -Is)"

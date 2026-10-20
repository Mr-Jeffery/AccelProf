#!/usr/bin/env bash
# T22: the synthetic traces of synth.py through the replay driver at YOSEMITE_HB_SHARDS=1 (the
# reference: the serial pass) and at each N of NS, with drains threaded (YOSEMITE_HB_SHARD_INLINE_MAX=0)
# and inline; every output compared with N=1's (cmp.py). CPU only, seconds; no GPU, no BeeGFS.
#   OUT=<dir> NS="2 8 32" bash eval/baselines/setup/t22_replay/synth_run.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
R=$W/eval/baselines/setup/t22_replay
OUT=${OUT:?set OUT}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) $(date -Is)"
rm -rf $OUT; mkdir -p $OUT
$GXX -std=c++17 -O2 -I$W/sanalyzer/include -I$W/nv-compute/gpu_src/include -o $OUT/replay $R/replay.cpp \
    -L$W/sanalyzer/wt_install/lib -Wl,-rpath=$W/sanalyzer/wt_install/lib -lsanalyzer || exit 1
python3 $R/synth.py $OUT/in --seeds ${SEEDS:-20}
one() {   # <bin> <tag> <N> [inline_max]
  local d=$OUT/run/$2/$3${4:+i$4}; mkdir -p $d
  ( cd $d && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_WORKER_COUNT=1 \
      YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
      YOSEMITE_ATOMIC_SCOPE_FILE=$OUT/in/atomic_scope.txt YOSEMITE_HB_SHARDS=$3 \
      ${4:+YOSEMITE_HB_SHARD_INLINE_MAX=$4} $OUT/replay $1 > replay.out 2> replay.err )
  ls $d/dependency_*/kernel_0.json
}
rc=0
for f in $OUT/in/*.bin; do
  tag=$(basename $f .bin)
  ref=$(one $f $tag 1)
  outs=""
  for n in ${NS:-2 8 32}; do outs="$outs $(one $f $tag $n 0) $(one $f $tag $n)"; done
  python3 $R/cmp.py $ref $outs > $OUT/run/$tag.cmp; r=$?
  [ $r -ne 0 ] && rc=1
  echo "$tag: $(head -1 $OUT/run/$tag.cmp | sed 's|^ref [^:]*: ||') -> $(grep -c EQUAL $OUT/run/$tag.cmp) EQUAL, $(grep -c DIFF $OUT/run/$tag.cmp) DIFF"
done
echo "== done rc=$rc $(date -Is)"

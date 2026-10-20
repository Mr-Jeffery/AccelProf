#!/usr/bin/env bash
#SBATCH --job-name=t22c-synth
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# T22 cont., parity on the synthetic traces of t22_replay/synth.py (CPU only): the 105 of T22 (5
# trace-validity cases + 100 random seeds) plus DENSE dense and BCAST broadcast/flag traces (the
# shapes the fixes act on). Per trace, through replay.cpp:
#   (a) the fixes against the pass before them: the b6a615e library (wt_install_b6a615e) at N=1 is
#       the reference; this tree's library at N=1 and at N = 2, 8, 32, every drain threaded
#       (YOSEMITE_HB_SHARD_INLINE_MAX=0) and inline -- cmp.py --le (hb_sync_pass equal but each
#       count 1 <= new <= old; every other field equal);
#   (b) this tree's six configurations against its own N=1 -- cmp.py, exact (counts included);
#   (c) vector-clock mode, N=1, old against new: the kernel JSONs byte for byte.
#   OUT=<dir> sbatch -p normal -o <log> eval/baselines/setup/t22c_synth.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
R=$W/eval/baselines/setup/t22_replay
OUT=${OUT:?set OUT}
OLD=$W/sanalyzer/wt_install_b6a615e/lib
NEW=$W/sanalyzer/wt_install/lib
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) nproc=$(nproc) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) old $(h $OLD/libsanalyzer.so) new $(h $NEW/libsanalyzer.so) $(date -Is)"
rm -rf $OUT; mkdir -p $OUT
for v in old new; do
  L=$OLD; [ $v = new ] && L=$NEW
  $GXX -std=c++17 -O2 -I$W/sanalyzer/include -I$W/nv-compute/gpu_src/include -o $OUT/replay_$v $R/replay.cpp \
      -L$L -Wl,-rpath=$L -lsanalyzer || exit 1
done
python3 $R/synth.py $OUT/in --seeds ${SEEDS:-100} --dense ${DENSE:-40} --bcast ${BCAST:-5}
one() {   # <bin> <tag> <old|new> <mode> <N> [inline_max]
  local d=$OUT/run/$2/$3-$4-$5${6:+i$6}; mkdir -p $d
  ( cd $d && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_WORKER_COUNT=1 \
      YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$4 YOSEMITE_HB_DUMP=0 \
      YOSEMITE_ATOMIC_SCOPE_FILE=$OUT/in/atomic_scope.txt YOSEMITE_HB_SHARDS=$5 \
      ${6:+YOSEMITE_HB_SHARD_INLINE_MAX=$6} $OUT/replay_$3 $1 > replay.out 2> replay.err )
  ls $d/dependency_*/kernel_0.json
}
rc=0; na=0; nb=0; nc=0; fa=0; fb=0; fc=0
for f in $OUT/in/*.bin; do
  tag=$(basename $f .bin)
  ref=$(one $f $tag old scalar-clock 1)
  new1=$(one $f $tag new scalar-clock 1)
  six=""
  for n in 2 8 32; do six="$six $(one $f $tag new scalar-clock $n 0) $(one $f $tag new scalar-clock $n)"; done
  python3 $R/cmp.py --le $ref $new1 $six > $OUT/run/$tag.le; ra=$?
  python3 $R/cmp.py $new1 $six > $OUT/run/$tag.eq; rb=$?
  vo=$(one $f $tag old vector-clock 1); vn=$(one $f $tag new vector-clock 1)
  cmp -s $vo $vn; rcv=$?
  na=$((na + 7)); nb=$((nb + 6)); nc=$((nc + 1))
  fa=$((fa + $(grep -c DIFF $OUT/run/$tag.le))); fb=$((fb + $(grep -c DIFF $OUT/run/$tag.eq))); fc=$((fc + (rcv != 0)))
  [ $ra -ne 0 ] || [ $rb -ne 0 ] || [ $rcv -ne 0 ] && rc=1
  echo "$tag: $(head -1 $OUT/run/$tag.le | sed 's|^ref [^:]*: ||') | new N=1 $(sed -n 2p $OUT/run/$tag.le | grep -o 'count [0-9]*') | (a) $(grep -c EQUAL $OUT/run/$tag.le)/7 (b) $(grep -c EQUAL $OUT/run/$tag.eq)/6 (c) vc $([ $rcv -eq 0 ] && echo identical || echo DIFFERENT)"
done
echo "TOTAL (a) $((na - fa))/$na equal-le, (b) $((nb - fb))/$nb equal, (c) $((nc - fc))/$nc vector-clock identical"
echo "== done rc=$rc $(date -Is)"

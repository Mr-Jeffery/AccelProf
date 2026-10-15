#!/usr/bin/env bash
#SBATCH --job-name=t22-replay
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
# T22 verification B, cross-N: one recorded scalar-clock trace through the worktree's libsanalyzer at
# several shard counts (replay.cpp), each output compared with the recording's own aggregates
# (cmp.py). CPU only; BeeGFS for the store.
#   STORE=<store dir> KERNELS="<id>/scalar-clock/kernel_3.json ..." NS="1 2 8 32" \
#     sbatch -p <cpu partition> -o <log> eval/baselines/setup/t22_replay/replay_run.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}; A=/home/fzheng4/AccelProf
R=$W/eval/baselines/setup/t22_replay
OUT=${OUT:-/mnt/beegfs/$USER/t22-replay}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) nproc=$(nproc) HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) $(date -Is)"
mkdir -p $OUT
$GXX -std=c++17 -O2 -I$W/sanalyzer/include -I$W/nv-compute/gpu_src/include -o $OUT/replay $R/replay.cpp \
    -L$W/sanalyzer/wt_install/lib -Wl,-rpath=$W/sanalyzer/wt_install/lib -lsanalyzer || exit 1
rc=0
for kj in $KERNELS; do
  id=${kj%%/*}; tag=$(echo $kj | tr '/' '_' | sed 's/\.json$//')
  D=$OUT/$tag; rm -rf $D; mkdir -p $D
  $W/.env/bin/python $W/python/atomic_scope_sidecar.py $STORE/$id/dots/*.dot -o $D/atomic_scope.txt > /dev/null
  $W/.env/bin/python $R/pack.py $STORE/$kj $D/k.bin || { rc=1; continue; }
  outs=""
  for n in ${NS:-1 2 8 32}; do
    mkdir -p $D/n$n
    ( cd $D/n$n && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_WORKER_COUNT=1 \
        YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
        YOSEMITE_ATOMIC_SCOPE_FILE=$D/atomic_scope.txt YOSEMITE_HB_SHARDS=$n \
        ${INLINE0:+YOSEMITE_HB_SHARD_INLINE_MAX=0} \
        $OUT/replay $D/k.bin > replay.out 2> replay.err; echo "rc=$?" >> replay.err )
    grep -h "\[replay\]\|rc=" $D/n$n/replay.err | sed "s|^|  n=$n |"
    outs="$outs $(ls $D/n$n/dependency_*/kernel_0.json)"
  done
  $W/.env/bin/python $R/cmp.py $STORE/$kj $outs || rc=1
done
echo "== done rc=$rc $(date -Is)"

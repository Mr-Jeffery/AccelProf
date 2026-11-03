#!/usr/bin/env bash
# C6 step 3: the ids of cmds.txt that have no attribution yet, smallest first, P at a time (the main run's queue is blocked behind its long ids).
set -u
. /home/fzheng4/c6-step3/env.sh
RWH=/home/fzheng4/c6rw; RWR=$S3/rw; P=${P:-2}; LIM=${LIM:-12h}
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-} RW_MODES=collector-only
rw1() {
  set=$1; id=$2
  case $set in
    t21b) H=$RWH/t21b; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-co;      M=$W/eval/realworld/manifest_t21b.csv; RES=$RWR/realworld ;;
    t21c) H=$RWH/t21c; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c-co; M=$W/eval/realworld/manifest_t21c.csv; RES=$RWR/realworld_t21c ;;
  esac
  [ -e $RES/attrib/$id.json ] && return 0
  mkdir -p /tmp/c6rws-$id; export TMPDIR=/tmp/c6rws-$id; t0=$(date +%s)
  timeout $LIM $PY $H/eval/realworld/harness/rw_attribute.py --id $id --store $S0 --manifest $M --out $RES/attrib/$id.json > $RWR/attrib-$id.small.out 2>&1
  echo "$(date -Is) small attribute $set $id rc=$? wall=$(( $(date +%s) - t0 ))s"; rm -rf /tmp/c6rws-$id
}
export -f rw1; export RWH RWR W PY LIM
tac $RWR/cmds.txt | xargs -P $P -L 1 bash -c 'rw1 "$@"' _
echo "small done $(date -Is)"

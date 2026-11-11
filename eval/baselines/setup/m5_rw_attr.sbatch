#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 20:00:00
#SBATCH -J m5-rw
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/rw-%j.log
# M5: C6's real-world attribution (rw_attribute.py, one id at a time) of the C2 recordings at S2 with CUVEIN_CHAIN_ATOMIC_HOP=1 and =0,
# heaviest first, P tasks at a time over both settings. amrex-1 (both builds) and colmap-new-1 are not attributed (known gaps).
W=/home/fzheng4/wt-m5; PY=/home/fzheng4/AccelProf/.env/bin/python
RWH=/home/fzheng4/m5rw; R=$W/eval/results/closure-atomic-hop/rw
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "${CUDA_HOME:-}" ] || { echo "no nvdisasm on $(hostname)"; exit 96; }
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-} RW_MODES=collector-only
echo "host=$(hostname) model=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p') cuda=$CUDA_HOME rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
for sw in 1 0; do mkdir -p $R/sw$sw/realworld/attrib $R/sw$sw/realworld_t21c/attrib; done
P=${P:-14}; LIM=${LIM:-14h}
rw1() {
  sw=$1; set=$2; id=$3
  case $set in
    t21b) H=$RWH/t21b; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-co;      M=$W/eval/realworld/manifest_t21b.csv; RES=$R/sw$sw/realworld ;;
    t21c) H=$RWH/t21c; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c-co; M=$W/eval/realworld/manifest_t21c.csv; RES=$R/sw$sw/realworld_t21c ;;
  esac
  [ -e $RES/attrib/$id.json ] && return 0
  mkdir -p /tmp/m5rw-$sw-$id; export TMPDIR=/tmp/m5rw-$sw-$id CUVEIN_CHAIN_ATOMIC_HOP=$sw
  t0=$(date +%s)
  timeout $LIM $PY $H/eval/realworld/harness/rw_attribute.py --id $id --store $S0 --manifest $M --out $RES/attrib/$id.json > $RES/attrib-$id.out 2>&1
  echo "$(date -Is) attribute sw$sw $set $id rc=$? wall=$(( $(date +%s) - t0 ))s"
  rm -rf /tmp/m5rw-$sw-$id
}
export -f rw1; export RWH R W PY LIM
# heaviest first, the two settings of one id adjacent
while read set id; do echo "1 $set $id"; echo "0 $set $id"; done < $S/m5_rw_cmds.txt | xargs -P $P -L 1 bash -c 'rw1 "$@"' _
echo "== attribution done $(date -Is)"

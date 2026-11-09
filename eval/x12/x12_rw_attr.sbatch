#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=24:00:00
# X12 real-world attribution + scoring. MODE=std|chain SET=recall|cand ; ids in ~/x12rw/$MODE/$SET.cmds (heaviest first)
set -u
MODE=${MODE:?}; SET=${SET:?}; P=${P:-8}; LIM=${LIM:-23h}
X=$HOME/x12rw/$MODE; PY=$HOME/AccelProf/.env/bin/python; B=/mnt/beegfs/fzheng4/cuvein_traces; C=$HOME/wt-x11-cochain; W=$HOME/wt/x12
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export CUVEIN_HOME=$C ACCEL_PROF_HOME=$C RW_MODES=collector-only
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "${CUDA_HOME:-}" ] || { echo "no nvdisasm on $(hostname)"; exit 96; }
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
if [ $SET = recall ]; then S=t21b; STORE=$B/realworld-2026-11-co-sh; RES=$X/res/realworld; else S=t21c; STORE=$B/realworld-2026-11-t21c-co-sh; RES=$X/res/realworld_t21c; fi
M=$W/eval/realworld/manifest_$S.csv; H=$X/$S
echo "host=$(hostname) mode=$MODE set=$SET cuda=$CUDA_HOME ids=$(wc -l < $X/$SET.cmds) $(date -Is)"
rw1() {
  id=$1; mkdir -p /tmp/x12rw-$id; export TMPDIR=/tmp/x12rw-$id; t0=$(date +%s)
  timeout $LIM $PY $H/eval/realworld/harness/rw_attribute.py --id $id --store $STORE --manifest $M --out $RES/attrib/$id.json > $X/attrib-$SET-$id.out 2>&1
  echo "$(date -Is) attribute $id rc=$? wall=$(( $(date +%s) - t0 ))s: $(tail -1 $X/attrib-$SET-$id.out | cut -c1-160)"
  rm -rf /tmp/x12rw-$id
}
export -f rw1; export H X SET STORE M RES PY LIM
xargs -P $P -L 1 bash -c 'rw1 "$@"' _ < $X/$SET.cmds
echo "== attribution done $(date -Is)"
EX=""; [ $SET = cand ] && EX="--exclude lightgbm-new-1,lightgbm-new-2,llamacpp-open-2"
$PY $H/eval/realworld/harness/rw_score.py --results $RES --manifest $M --pairs $H/eval/realworld/recall_pairs.json $EX --write > $X/score_$SET.out 2>&1; echo "score rc=$?"
echo "== all done $(date -Is)"

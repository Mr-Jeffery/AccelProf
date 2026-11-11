#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 20:00:00
#SBATCH -J m5-prod
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/prod-%j.log
# M5: the C2 production recordings (realworld-2026-10-co = T21b recall set, realworld-2026-10-t21c-co = T21c candidate set) analysed at S2
# (--chain-closure --co-async --co-r3 off) with CUVEIN_CHAIN_ATOMIC_HOP=1 (after) and =0 (before: no S2 result exists for these stores),
# CUVEIN_DOT_PREFILTER=1, one shard after the other on this one node (analysis_s uncontended); then merged per setting.
#   SWS="1 0"; KS="0 1 .."
W=/home/fzheng4/wt-m5
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=$W/eval/results/closure-atomic-hop/prod
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W CUVEIN_DOT_PREFILTER=1
HOST=$(hostname); MODEL=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p')
echo "host=$HOST nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
echo "lscpu model name: $MODEL"
run() {   # run <sw> <manifest> <store> <results dir> <tag> <selector...>
  local sw=$1 man=$2 store=$3 res=$4 tag=$5; shift 5
  local d=$O/sw$sw/$res; mkdir -p $d
  local f=$d/baselines-cuvein-shard$tag.csv
  [ -s $f ] && { echo "skip sw$sw $res $tag"; return; }
  echo "== sw$sw $res $tag $(date -Is)"
  local t=$d/.tmp$tag; rm -rf $t; mkdir -p $t
  CUVEIN_CHAIN_ATOMIC_HOP=$sw BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze --manifest $man "$@" \
      --tag "$tag" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure --co-async --co-r3 off \
      --analysis-timeout 14400 --analysis-workers 16 > $d/shard$tag.log 2>&1
  local rc=$?
  tail -1 $d/shard$tag.log
  local g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
    $PY $S/c6b_anode.py "$g" $HOST
    printf 'host=%s\nmodel=%s\nshard=%s\njob=%s\nrev=%s\nsw=%s\n' "$HOST" "$MODEL" "$tag" "$SLURM_JOB_ID" "$(git rev-parse --short=12 HEAD)" "$sw" > $d/cpu-$tag.txt
    mkdir -p $d/confirm
    mv $t/chain-kernels-*.jsonl $d/ 2>/dev/null
    [ -d $t/confirm ] && mv $t/confirm/* $d/confirm/ 2>/dev/null
    mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc sw$sw $res $tag"; fi
}
for sw in ${SWS:-1 0}; do
  for k in ${KS:-$(seq 0 15)}; do
    run $sw eval/realworld/manifest_t21b.csv realworld-2026-10-co c2-recall ${k}_16 --pset RW --shard $k/16
  done
  for k in ${KS:-$(seq 0 15)}; do
    run $sw eval/realworld/manifest_t21c.csv realworld-2026-10-t21c-co c2-cand ${k}_16 --id-file $S/c6_c2_cand_ids.txt --shard $k/16
  done
  for r in c2-recall c2-cand; do
    $PY eval/baselines/parallel.py merge --tool cuvein --results-dir $O/sw$sw/$r --out-dir $O/sw$sw/merged-$r > $O/sw$sw/merge-$r.log 2>&1; echo "merge sw$sw $r rc=$?"
  done
done
echo "end $(date -Is)"

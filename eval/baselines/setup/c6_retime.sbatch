#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 04:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-c6/eval/x_logs/c6-retime-%x-%j.log
# C6 step 2 re-time: one sample (c6_retime_select.py: VERDICT_PARALLEL.md section 6's 40 programs + every finished
# P7/P9 id), four configurations, all on this node, --analysis-workers 16, one program at a time, each configuration
# twice in a row (pass 1 cold, pass 2 warm page cache):
#   vc      final-2026-11     vector-clock    closure off
#   sc      final-2026-11     scalar-clock    closure off
#   co-off  final-2026-11-co  collector-only  closure off
#   co-on   final-2026-11-co  collector-only  closure on (--chain-closure)
# Results: eval/results/co-chain/retime/<host>/<cfg>-p<pass>/ (shard csv with analysis_s in notes, chain-kernels jsonl).
W=/home/fzheng4/wt-c6
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
HOST=$(hostname)
O=$W/eval/results/co-chain/retime/$HOST
mkdir -p $O
echo "host=$HOST nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
lscpu | grep -E "^(Model name|Socket|Core|Thread|CPU MHz|CPU max MHz)"
$PY $S/c6_retime_select.py $W $O/ids.txt
cfg() { # name store mode extra...
  local name=$1 store=$2 mode=$3; shift 3
  for p in 1 2; do
    local d=$O/$name-p$p; rm -rf $d; mkdir -p $d
    echo "== $name pass $p $(date -Is)"
    BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=$mode $PY eval/baselines/parallel.py analyze \
      --manifest eval/baselines/manifest.csv --id-file $O/ids.txt --tag rt --results-dir $d \
      --analysis-timeout 14400 --analysis-workers 16 "$@" > $d/run.log 2>&1
    echo "rc=$? $(tail -1 $d/run.log)"
    $PY $S/c6_anode.py $d/baselines-cuvein-shardrtall.csv $HOST
  done
}
cfg vc final-2026-11 vector-clock
cfg sc final-2026-11 scalar-clock
cfg co-off final-2026-11-co collector-only
cfg co-on final-2026-11-co collector-only --chain-closure
echo "end $(date -Is)"

#!/bin/bash
#SBATCH -p skylake
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 04:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J c6b-retime
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-retime-%x-%j.log
# C6b step 4 re-time on ONE Xeon Silver 4110 node (lscpu-checked): the 47-program sample of C6's re-time (c6_retime_select.py), five configurations,
# --analysis-workers 16, one program at a time, each twice in a row (pass 1 cold, pass 2 warm):
#   vc      final-2026-11     vector-clock   (no flags)
#   sc      final-2026-11     scalar-clock   (no flags)
#   co-off  final-2026-11-co  collector-only, --confirm only      (C1's rules)
#   co-s1   final-2026-11-co  collector-only, --confirm --chain-closure --co-async --co-r3 strict   (S1)
#   co-s2   final-2026-11-co  collector-only, --confirm --chain-closure --co-async --co-r3 off      (S2)
# Purpose: the analysis_s of the clock modes, C1's rules, S1 and S2 on one node, to separate the host from the rules in the step-2 figures.
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
HOST=$(hostname)
MODEL=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p')
echo "host=$HOST nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
echo "lscpu model name: $MODEL"; lscpu | grep -E "^(Socket|Core|Thread|CPU MHz|CPU max MHz)"
case "$MODEL" in *"Xeon"*"Silver 4110"*) ;; *) echo "NOT A XEON SILVER 4110 NODE ($HOST: $MODEL); aborting, nothing run"; exit 3;; esac
O=$W/eval/results/co-chain-b/step4/retime/$HOST
mkdir -p $O
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
    $PY $S/c6b_anode.py $(ls $d/baselines-cuvein-shard*.csv | head -1) $HOST
    rm -rf $d/confirm
  done
}
cfg vc final-2026-11 vector-clock
cfg sc final-2026-11 scalar-clock
cfg co-off final-2026-11-co collector-only --confirm --confirm-dir $O/_confirm
cfg co-s1 final-2026-11-co collector-only --confirm --confirm-dir $O/_confirm --chain-closure --co-async --co-r3 strict
cfg co-s2 final-2026-11-co collector-only --confirm --confirm-dir $O/_confirm --chain-closure --co-async --co-r3 off
rm -rf $O/_confirm
echo "end $(date -Is)"

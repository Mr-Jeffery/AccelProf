#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# X12 parity gate for ONE program: every kept rep's kernel JSONs of the new recording against X11's -n 1 collector-only recordings
# (same SuperCollider binary; x11-co-r1 = the primary baseline, r2 and r3 reported as well), kernel index to kernel index, with
# co_json_diff.py (T26). Also the baseline against itself (r1 vs r2, r1 vs r3): a program whose own -n 1 recordings differ cannot pass.
# Exit 0 iff 0 differences of every rep against r1. Output: $W/eval/results/$RES/parity/<app>.txt and per-pair JSON.
#   APP=crs W=... [STORE=final-2026-11-co-sh] [RES=co-sharded] sbatch -J x12-gate-crs --dependency=afterok:<rec> x12_gate.sbatch
set -u
APP=${APP:?}; W=${W:?}; STORE=${STORE:-final-2026-11-co-sh}; RES=${RES:-co-sharded}
B=/mnt/beegfs/fzheng4/cuvein_traces; PY=/home/fzheng4/AccelProf/.env/bin/python; D=$W/eval/baselines/setup/co_json_diff.py
OUT=$W/eval/results/$RES/parity; mkdir -p $OUT
base() { if [ $APP = atomicCAS ]; then echo $B/x11-co-r$1/X11-$APP/collector-only; else echo $B/x11-co-r$1-$APP/X11-$APP/collector-only; fi; }
new=$B/$STORE/X11-$APP
rc=0; : > $OUT/$APP.txt
echo "host=$(hostname) $(date -Is) app=$APP store=$STORE" | tee -a $OUT/$APP.txt
for j in 2 3; do $PY -I $D $(base 1) $(base $j) --label "BASE r1-vs-r$j" --json $OUT/$APP.base-r1-r$j.json --max-list 3 | tee -a $OUT/$APP.txt; done
for d in $new/collector-only-rep*; do
  k=${d##*-rep}
  for j in 1 2 3; do
    $PY -I $D $(base $j) $d --label "NEW rep$k vs x11-r$j" --json $OUT/$APP.rep$k-r$j.json --max-list 3 | tee -a $OUT/$APP.txt
    s=${PIPESTATUS[0]}; [ $j = 1 ] && [ $s != 0 ] && rc=1
  done
done
[ -d $new/collector-only-rep1 ] || { echo "NO-REPS: $new has no collector-only-rep dirs" | tee -a $OUT/$APP.txt; rc=2; }
echo "GATE $APP rc=$rc" | tee -a $OUT/$APP.txt
exit $rc

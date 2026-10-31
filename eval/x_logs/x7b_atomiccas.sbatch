#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 24:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7b-co-acas
#SBATCH -o /home/fzheng4/wt-x7b/eval/x_logs/x7b-co-acas-%j.log
# X7b B1: cuRace collector-only P9-atomicCAS-cuda re-analysed from the stored kernel JSONs with Part A's code (N=16, cap 84600)
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=/home/fzheng4/wt-x7b/eval/results/cap84600/co-atomicCAS
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
for s in final-2026-11-co final-2026-11-co-long final-2026-11-co-24h; do
  echo "store $s: $(ls -d $B/$s/P9-atomicCAS-cuda* 2>&1 | head -3)"; ls $B/$s/P9-atomicCAS-cuda* 2>/dev/null | head; du -sh $B/$s/P9-atomicCAS-cuda* 2>/dev/null
done
for s in final-2026-11-co final-2026-11-co-long final-2026-11-co-24h; do
  [ -d $B/$s/P9-atomicCAS-cuda ] || continue
  mkdir -p $O/$s
  /usr/bin/time -v env BASELINE_TRACE_DIR=$B/$s BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv --id-file /home/fzheng4/wt-x7b/eval/x_logs/x7b_atomiccas_id.txt --tag x7b-acas --results-dir $O/$s --analysis-timeout 84600 --analysis-workers 16 > $O/$s/run.log 2> $O/$s/time.log
  echo "store $s rc=$?"; tail -3 $O/$s/run.log
done
echo "end $(date -Is)"

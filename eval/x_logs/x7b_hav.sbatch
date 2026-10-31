#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 04:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7b-vc-hav
#SBATCH -o /home/fzheng4/wt-x7b/eval/x_logs/x7b-vc-hav-%j.log
# X7b: verdict-step time (analysis_s) of the new cuRace vector-clock P7-haversine recording (store final-2026-11-24h-vc), Part A's code, N=16
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=/home/fzheng4/wt-x7b/eval/results/cap84600/vc-haversine-analysis
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) start=$(date -Is)"
ls $B/final-2026-11-24h-vc/P7-haversine-cuda/vector-clock | head -3; ls $B/final-2026-11-24h-vc/P7-haversine-cuda/vector-clock | wc -l
BASELINE_TRACE_DIR=$B/final-2026-11-24h-vc BASELINE_MODES=vector-clock $PY eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv --id-file /home/fzheng4/wt-x7b/eval/x_logs/x7b_hav_id.txt --tag x7b-hav --results-dir $O --analysis-timeout 84600 --analysis-workers 16
echo "rc=$? end $(date -Is)"

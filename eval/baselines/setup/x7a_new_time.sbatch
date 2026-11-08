#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 06:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-new-time2
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-new-time-%j.log
# X7 step 6, the new-code half of x7a_old_time.sbatch on a second node (same list): this branch at workers=1,
# cache off and cache on.
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
O=$W/eval/results/verdict-timing/old-timing
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
echo "host=$(hostname) nproc=$(nproc) rev=$(git -C $W rev-parse --short=12 HEAD) start=$(date -Is)"
export CUVEIN_HOME=$W ACCEL_PROF_HOME=$W   # the first run (324025) lacked this: sync_dominance came from the default checkout
X=$W/eval/baselines/setup/x7_old.py
$PY $X run --home $W --workers 1 --list $O/list.tsv --out $O/new-cache.csv --jobs 8 --limit 7200
$PY $X run --home $W --workers 1 --no-cache --list $O/list.tsv --out $O/new-nocache.csv --jobs 8 --limit 900
echo "end $(date -Is)"

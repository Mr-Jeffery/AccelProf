#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 12:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-old-time
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-old-time-%j.log
# X7 step 6: the verdict step's time per program, N = 1, cache off. OLD = wt-x7a-base (40b5222, the pre-X7
# code: serial, no cache). NEW = this branch at workers=1, cache on, and workers=1 cache off. 8 programs at a time on a
# whole node (each single-threaded). The sample is x7_old.py select.
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
O=$W/eval/results/verdict-timing/old-timing
mkdir -p $O
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
echo "host=$(hostname) nproc=$(nproc) rev=$(git -C $W rev-parse --short=12 HEAD) start=$(date -Is)"
X=$W/eval/baselines/setup/x7_old.py
$PY $X select --out $O/list.tsv
$PY $X run --home /home/fzheng4/wt-x7a-base --list $O/list.tsv --out $O/old.csv --jobs 8 --limit 7200
echo "old done $(date -Is)"
$PY $X run --home $W --workers 1 --no-cache --list $O/list.tsv --out $O/new-nocache.csv --jobs 8 --limit 7200
$PY $X run --home $W --workers 1 --list $O/list.tsv --out $O/new-cache.csv --jobs 8 --limit 7200
echo "end $(date -Is)"

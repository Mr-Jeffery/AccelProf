#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 14:00:00
#SBATCH -J m5-pairs
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/pairs-%j.log
W=/home/fzheng4/wt-m5; cd $W
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) model=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p') rev=$(git rev-parse --short=12 HEAD) $(date -Is)"
PY=/home/fzheng4/AccelProf/.env/bin/python
$PY eval/baselines/setup/m5_pairs.py run --workers 15
$PY eval/baselines/setup/m5_pairs.py summary
echo end $(date -Is)

#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 01:00:00
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/report-%x-%j.log
# usage: sbatch -J m5-rep-c1 --export=ALL,WHICH=c1 m5_report.sbatch   (WHICH = c1 | prod)
W=/home/fzheng4/wt-m5; cd $W
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) $(date -Is)"
/home/fzheng4/AccelProf/.env/bin/python $W/eval/baselines/setup/m5_report.py ${WHICH:-c1}
echo end

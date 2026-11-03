#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 00:20:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-c6/eval/x_logs/c6-merge-%x-%j.log
# C6 step 2: merge + parity compare (c6_merge_compare.py); WHICH = c1 | c2recall | c2cand
W=/home/fzheng4/wt-c6
echo "host=$(hostname) which=$WHICH"
/home/fzheng4/AccelProf/.env/bin/python $W/eval/baselines/setup/c6_merge_compare.py $W $WHICH

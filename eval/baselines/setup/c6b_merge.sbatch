#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 00:30:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-merge-%x-%j.log
# C6b step 2: merge + parity compare (c6b_merge_compare.py); SET = s1 | s2
W=/home/fzheng4/wt-c6b
echo "host=$(hostname) set=$SET"
/home/fzheng4/AccelProf/.env/bin/python $W/eval/baselines/setup/c6b_merge_compare.py $W $SET

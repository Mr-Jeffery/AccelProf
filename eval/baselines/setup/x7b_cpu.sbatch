#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -c 8
#SBATCH -t 04:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-x7b/eval/x_logs/x7b-cpu-%x-%j.log
# X7 Part B: CPU step on a compute node. CMD is run from the worktree root.
cd /home/fzheng4/wt-x7b || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
echo "host=$(hostname) $(date -Is) CMD=$CMD"
bash -c "$CMD"
echo "rc=$? end $(date -Is)"

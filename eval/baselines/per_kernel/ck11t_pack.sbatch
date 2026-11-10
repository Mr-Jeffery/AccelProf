#!/bin/bash
#SBATCH -J x13-ck11p
#SBATCH -p normal
#SBATCH -c 16
#SBATCH -t 06:00:00
#SBATCH --array=0-4
#SBATCH -o /home/fzheng4/wt-x13/eval/x_logs/x13/ck11p-%A_%a.log
# Packed rerun of ck11t shards killed when their ssh host tasks ended: 23 shards per whole node.
D=/home/fzheng4/wt-x13/eval/baselines/per_kernel
LOG=/home/fzheng4/wt-x13/eval/x_logs/x13
K=23
ids=$(sed -n "$((SLURM_ARRAY_TASK_ID*K+1)),$((SLURM_ARRAY_TASK_ID*K+K))p" $D/ck11t_rerun_ids.txt)
echo "host=$(hostname) ids=$ids"
printf "%s\n" $ids | xargs -P $K -I{} bash -c "$D/ck11t_one.sh {} > $LOG/ck11t-ssh-{}.log 2>&1"
echo "done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=co-pairs
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=06:00:00
#SBATCH --array=0-23
#SBATCH --output=/home/fzheng4/wt-co-tables/eval/x_logs/co-pairs-%A_%a.log
# C3 item 9: per-pair verdict records of X1b's scalar-clock and C1's collector-only recordings (co_pairs_collect.py)
cd /home/fzheng4/wt-co-tables
export CUVEIN_HOME=/home/fzheng4/wt-co-tables
echo "host=$(hostname) $(date -Is) HEAD=$(git rev-parse --short HEAD) task=$SLURM_ARRAY_TASK_ID"
[ -d /mnt/beegfs/fzheng4/cuvein_traces/final-2026-11 ] || { echo "BeeGFS not readable"; exit 2; }
/home/fzheng4/AccelProf/.env/bin/python eval/baselines/setup/co_tables/co_pairs_collect.py $SLURM_ARRAY_TASK_ID/24
echo "== done rc=$? $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=co-pairs-long
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --output=/home/fzheng4/wt-co-tables/eval/x_logs/co-pairs-long-%j.log
# C3 item 9: the recordings whose 900 s analysis cap was reached in the array pass, with a 39,600 s cap
cd /home/fzheng4/wt-co-tables
export CUVEIN_HOME=/home/fzheng4/wt-co-tables PAIRS_ONLY="$1" PAIRS_CAP=39600
echo "host=$(hostname) $(date -Is) ONLY=$PAIRS_ONLY"
/home/fzheng4/AccelProf/.env/bin/python eval/baselines/setup/co_tables/co_pairs_collect.py 0/1
echo "== done rc=$? $(date -Is)"

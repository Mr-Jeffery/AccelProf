#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 00:20:00
#SBATCH -J m5-post
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/post-%j.log
PY=/home/fzheng4/AccelProf/.env/bin/python; S=/home/fzheng4/wt-m5/eval/baselines/setup
echo "host=$(hostname)"
$PY $S/m5_outcomes.py
$PY $S/m5_tables.py
echo end

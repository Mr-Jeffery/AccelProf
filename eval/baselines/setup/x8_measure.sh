#!/usr/bin/env bash
#SBATCH --job-name=x8-omeas
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-x8/eval/x_logs/x8-omeas-%j.log
# X8 step 4: one row's fiber count / time / memory at 256x1024 on the largest of the four graphs.
export ACCEL_PROF_HOME=/home/fzheng4/wt-x8
cd /home/fzheng4/wt-x8 || exit 1
echo "node=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')GB"
PY=/home/fzheng4/AccelProf/.env/bin/python
for id in "$@"; do $PY eval/baselines/oracle_pi/measure_row.py "$id" 0; done

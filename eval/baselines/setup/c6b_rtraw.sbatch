#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:30:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-rtraw-%x-%j.log
# C6b step 0: lock_rtraw explanation. Analysis only (sync_dominance.analyze on the stored recordings, python/ of be325e03 extracted read-only).
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
T=$(mktemp -d); git -C $W archive be325e03 python | tar -x -C $T
export RTRAW_PYHOME=$T
hostname; date -Is
$PY $W/eval/baselines/setup/c6b_rtraw.py
echo end $(date -Is)

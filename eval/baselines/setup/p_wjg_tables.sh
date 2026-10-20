#!/bin/bash
# WARPSYNC join gap, phase 3: rows, tables, moves (wjg_tables.py) and, with COVERAGE=1, X1 coverage
# (wjg_coverage.py), over eval/results/wjg (or R).
#   sbatch eval/baselines/setup/p_wjg_tables.sh      (or: srun --jobid=<running> --overlap bash ...)
#SBATCH -p normal
#SBATCH -J wjg-tables
#SBATCH -t 04:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-warpsync-join-gap/eval/x_logs/wjg-tables-%j.log
W=${W:-/home/fzheng4/wt-warpsync-join-gap}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  [ -d "$d" ] || { echo "PREFLIGHT FAIL $(hostname): $d missing"; exit 3; }
done
cd "$W" || exit 1
unset ACCEL_PROF_HOME
export CUVEIN_HOME=$W
R=${R:-eval/results/wjg}
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD
$PY eval/baselines/setup/wjg_tables.py --dir "$R"
[ -n "$COVERAGE" ] && $PY eval/baselines/setup/wjg_coverage.py --dir "$R" --procs 16
echo "done $(date -Is)"

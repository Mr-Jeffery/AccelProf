#!/usr/bin/env bash
#SBATCH --job-name=x8-oracle
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-x8/eval/x_logs/x8-oracle-%j.log
# X8 step 4: oracle_pi on the 99 shipped codes (X8_BUILD=sc-subset) or all 590 (X8_BUILD=""), one graph per job,
# each row's own launch from the manifest (256 x 1024), no shrinking; unfinished rows -> ORACLE-N/A.
export ACCEL_PROF_HOME=/home/fzheng4/wt-x8
cd /home/fzheng4/wt-x8 || exit 1
echo "node=$(hostname) inputs=$X8_INPUT build=$X8_BUILD"
PY=/home/fzheng4/AccelProf/.env/bin/python
$PY eval/baselines/oracle_pi/oracle_pi.py --inputs "$X8_INPUT" ${X8_BUILD:+--build $X8_BUILD} ${X8_SHARD:+--shard $X8_SHARD} --jobs 16 --timeout ${X8_TMO:-4500} --na \
    --out /home/fzheng4/wt-x8/eval/x_logs/oracle-x8-$X8_TAG.csv

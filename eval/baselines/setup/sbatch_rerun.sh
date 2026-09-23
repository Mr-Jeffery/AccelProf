#!/usr/bin/env bash
#SBATCH --job-name=cuvein-rerun
#SBATCH --partition=rtx3060ti
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/rerun-%j.log
# Re-run cuVein for the present corpora with the fixed sync_dominance call (both
# modes now go through analyze; the earlier run's scalar-clock column was zeroed by
# a TypeError swallowed as CLEAN). racecheck data is unaffected and kept. Then
# classify + rebuild tables. Binaries from the first run are reused (bin/ intact).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
rm -f eval/results/baselines-cuvein.csv
rm -rf eval/baselines/confirm
echo "### smoke: canary + one racy litmus (both modes) ###"
$PY eval/baselines/run_cuvein.py --id P5-canary,P5-race_interblock_blkatom --confirm 2>&1 | tail -3
echo "### full P4,P5,P6 (cuVein both modes) ###"
$PY eval/baselines/run_cuvein.py --pset P4,P5,P6 --confirm
echo "### racecheck (shared-mem rows) ###"
rm -f eval/results/baselines-racecheck.csv
$PY eval/baselines/run_racecheck.py --pset P4,P5,P6
echo "### classify + tables ###"
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "rerun done"

#!/usr/bin/env bash
#SBATCH --job-name=t1-report
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t1-report-%j.log
# After the artifact's verbatim `make table1`: sqlite -> CSV, then regenerate the report
# (adds the "HiRace artifact Table 1, reproduced" section + the runner cross-check). CPU only.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/hirace_table1_to_csv.py && $PY eval/baselines/make_tables.py
sqlite3 eval/baselines/setup/tools/HiRace/results/hirace_correctness_results.sqlite3 "select 'codes in DB', count(distinct code) from hirace"

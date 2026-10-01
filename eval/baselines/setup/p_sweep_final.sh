#!/usr/bin/env bash
#SBATCH --job-name=sw-final
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/swfinal-%j.log
# Merge ALL cuVein shard CSVs (P4/P5/P6 from the earlier run + P1/P3/P7), classify,
# rebuild tables. racecheck reused as-is.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/parallel.py merge
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "sweep final done"

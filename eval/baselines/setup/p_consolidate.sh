#!/usr/bin/env bash
#SBATCH --job-name=consolidate
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/consolidate-%j.log
# Final consolidation after the v3 sweep AND HiRace: merge cuVein shards, select
# P7, classify (now incl. HiRace + iGUARD if present), rebuild all tables.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/select_p7.py
$PY eval/baselines/parallel.py merge
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "consolidate done"

#!/usr/bin/env bash
#SBATCH --job-name=full-final
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fullfinal-%j.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/select_p7.py
$PY eval/baselines/parallel.py merge
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "full final done"

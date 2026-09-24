#!/usr/bin/env bash
#SBATCH --job-name=cv-finalize
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pfinalize-%j.log
# CPU node: merge shard CSVs, classify disagreements, rebuild tables.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/parallel.py merge
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "p_finalize done"

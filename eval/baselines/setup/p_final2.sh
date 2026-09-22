#!/usr/bin/env bash
#SBATCH --job-name=final2
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:40:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/final2-%j.log
# Merge every tool family's shard CSVs, root-cause residuals, classify
# disagreements, regenerate BASELINES.md. CPU only.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/parallel.py merge --tool cuvein,sanitizer,iguard,supercollider,hirace
$PY eval/baselines/classify_residuals.py
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/classify_fp_causes.py
$PY eval/baselines/make_tables.py
echo "final2 done"

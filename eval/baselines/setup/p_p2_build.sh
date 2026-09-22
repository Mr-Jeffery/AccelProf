#!/usr/bin/env bash
#SBATCH --job-name=p2-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/p2build-%j.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
$PY eval/baselines/build_indigo2.py --stage compile 2>&1 | tail -3
$PY eval/baselines/mk_manifest.py

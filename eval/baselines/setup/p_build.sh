#!/usr/bin/env bash
#SBATCH --job-name=cv-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pbuild-%j.log
# CPU node: build all corpora for sm_89 (nvcc runs on CPU), compile P3, regen
# manifest, and reset the parallel work dirs. No GPU used.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
rm -rf eval/results/traces eval/baselines/confirm
rm -f eval/results/baselines-cuvein-shard*.csv eval/results/baselines-cuvein.csv
$PY eval/baselines/build_corpora.py --arch 89 --pset P4,P5,P6 2>&1 | tail -4
$PY eval/baselines/build_indigo.py --stage compile --pset P3 2>&1 | tail -4
$PY eval/baselines/mk_manifest.py
echo "p_build done"

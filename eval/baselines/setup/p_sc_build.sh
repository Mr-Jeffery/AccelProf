#!/usr/bin/env bash
#SBATCH --job-name=sc-build
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/scbuild-%j.log
# Build P8 (SuperCollider's 99 Indigo tests) and P9 (its 10 HeCBench apps) with our
# recipe for the other detectors, then regenerate manifest.csv.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
BASELINE_SM=89 $PY eval/baselines/build_sc_sets.py
$PY eval/baselines/mk_manifest.py

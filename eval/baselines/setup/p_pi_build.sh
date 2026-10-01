#!/usr/bin/env bash
#SBATCH --job-name=pi-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=03:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/pi-build-%j.log
# PI = whole Indigo-original suite (590 IndigoSuite codes + their HiRace twins), then the
# manifest (PI replaces the partial sets P2 and P8). CPU node; nvcc only.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
[ -e eval/baselines/manifest.pre-PI.csv ] || cp eval/baselines/manifest.csv eval/baselines/manifest.pre-PI.csv
$PY eval/baselines/build_indigo_full.py --jobs 16 || exit 1
$PY eval/baselines/mk_manifest.py
echo "pi build done"

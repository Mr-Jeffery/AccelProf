#!/usr/bin/env bash
#SBATCH --job-name=sw-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/swbuild-%j.log
# CPU: generate+compile P1 (Indigo3, 100-sample) & P3 (graph race-free) via the
# suite compiler, build P7 (HeCBench), regenerate the manifest.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
$PY eval/baselines/build_indigo.py --stage compile --pset P1,P3 2>&1 | tail -4
$PY eval/baselines/build_corpora.py --arch 89 --pset P7 --hecbench-apps nbody-cuda,mandelbrot-cuda,bitonic-sort-cuda,heartwall-cuda,bezier-surface-cuda,haversine-cuda 2>&1 | tail -4
$PY eval/baselines/mk_manifest.py
echo "sweep build done"

#!/usr/bin/env bash
#SBATCH --job-name=full-build
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fullbuild-%j.log
# CPU: P1 (default+slower_atomic) + P3(expanded) via suite compiler; P2 (IndigoSuite);
# P7 (broad HeCBench); regenerate manifest. nvcc runs on CPU node.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
# clear stale sweep shards + confirm so the re-run is clean (keep P4/5/6 _16 shards)
rm -f eval/results/baselines-cuvein-shard*_32.csv
$PY eval/baselines/build_indigo.py --stage compile --pset P1,P3 2>&1 | tail -3
$PY eval/baselines/build_indigo2.py --stage compile 2>&1 | tail -3
$PY eval/baselines/build_corpora.py --arch 89 --pset P7 --hecbench-apps nbody-cuda,mandelbrot-cuda,bitonic-sort-cuda,heartwall-cuda,bezier-surface-cuda,haversine-cuda,backprop-cuda,hotspot-cuda,pathfinder-cuda,srad-cuda,particlefilter-cuda,lavaMD-cuda,kmeans-cuda,stencil1d-cuda,bfs-cuda 2>&1 | tail -4
$PY eval/baselines/mk_manifest.py
echo "full build done"

#!/usr/bin/env bash
#SBATCH --job-name=t3-exitproto
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=03:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t3-exitproto-%j.log
# T3 (eval/CRS_CUDA_TRIAGE.md §6): the offline exit-aware re-score of crs-cuda's kept dumps.
#   sbatch eval/baselines/setup/t3_exit_prototype.sh [kernel_N ...]
W=/home/fzheng4/wt-T3
cd $W && export ACCEL_PROF_HOME=$W && source eval/baselines/gpu_env.sh
echo "host=$(hostname) HEAD=$(git -C $W rev-parse --short HEAD) $(date -Is)"
start=$(date +%s)
NPROC=4 $PY eval/baselines/setup/t3_exit_prototype.py "$@"
echo "== done $(( $(date +%s) - start )) s"

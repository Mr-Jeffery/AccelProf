#!/usr/bin/env bash
#SBATCH --job-name=c4-fixtures
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-c4/eval/x_logs/c4-fixtures-%j.log
# C4: record test_collector_only.py's four fixtures (co_straight, co_loop_red, co_loop_tile, co_missing) and run test_co_offline.py + test_collector_only.py
set -u
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=/home/fzheng4/AccelProf CUDA_HOME=/usr/local/cuda-13.4
[ -x $CUDA_HOME/bin/nvcc ] || export CUDA_HOME=/usr/local/cuda-13.3
source /home/fzheng4/wt-c4/eval/baselines/gpu_env.sh
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | head -1) cuda=$CUDA_HOME $(date -Is)"
cd /home/fzheng4/wt-c4 || exit 1
$PY -m pytest python/test_co_offline.py python/test_collector_only.py -v -rs -p no:warnings --tb=short 2>&1 | tail -60
echo "== done $(date -Is)"

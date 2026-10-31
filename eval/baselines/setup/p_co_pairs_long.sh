#!/usr/bin/env bash
#SBATCH --job-name=c4-pairs-long
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --exclusive
#SBATCH --time=14:00:00
#SBATCH --output=/home/fzheng4/wt-c4/eval/x_logs/c4pairslong-%j.log
# C4 pair level: the three recordings whose pair pass hit the 3,600 s cap (P7-srad-cuda, P9-tridiagonal-cuda, P9-mr-cuda), each with
# the rule on and off, cap 16,200 s per half, one process per recording (co_offline_pairs.py with PAIRS_IDS).
set -u
W=/home/fzheng4/wt-c4; PY=/home/fzheng4/AccelProf/.env/bin/python
cd $W || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export CUVEIN_HOME=$W PAIRS_CAP=16200 PAIRS_MEM=28
echo "host=$(hostname) $(date -Is) HEAD=$(git rev-parse --short=12 HEAD)"
for id in P7-srad-cuda P9-tridiagonal-cuda P9-mr-cuda; do
  ( PAIRS_IDS=$id PAIRS_TAG=$id $PY eval/baselines/setup/co_offline/co_offline_pairs.py 0/1 > eval/x_logs/c4pairslong-$id.out 2>&1; echo "$id rc=$? $(date -Is)" ) &
done
wait
echo "== done $(date -Is)"

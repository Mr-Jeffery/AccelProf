#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -t 06:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-mem
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-mem-%j.log
# X7 A4: peak memory (summed RSS and PSS of the analysis' process group) and wall of the
# verdict step at N = 1 and N = 16 (cache on), plus N = 1 uncached where the profile showed
# it is short, on stored recordings; one run at a time on a whole node. Output sha256 per run.
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
T=/mnt/beegfs/fzheng4/cuvein_traces
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export CUVEIN_HOME=$W ACCEL_PROF_HOME=$W
echo "host=$(hostname) nproc=$(nproc) mem=$(free -g | awk '/Mem/{print $2}')G rev=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) start=$(date '+%F %T')"
m() { $PY $W/eval/baselines/setup/x7_mem.py --label "$1" --mode-dir "$2" --dots-dir "$(dirname $2)/dots" --workers "$3" ${4:-}; }
KNN=$T/final-2026-11-24h-sc/P9-knn-cuda/scalar-clock
STEN=$T/final-2026-11-co-24h/P7-stencil1d-cuda/collector-only
HW=$T/final-2026-11-24h-sc/P7-heartwall-cuda/scalar-clock
CAS=$T/final-2026-11-co/P9-atomicCAS-cuda/collector-only
m knn-sc $KNN 16; m knn-sc $KNN 1; m knn-sc $KNN 1 --no-cache
m stencil1d-co $STEN 16; m stencil1d-co $STEN 1; m stencil1d-co $STEN 1 --no-cache
m heartwall-sc $HW 16; m heartwall-sc $HW 1
m atomicCAS-co $CAS 16; m atomicCAS-co $CAS 1
echo "end $(date '+%F %T')"

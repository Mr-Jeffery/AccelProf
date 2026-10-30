#!/usr/bin/env bash
#SBATCH --job-name=c4-co-offline
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --exclusive
#SBATCH --time=1-00:00:00
#SBATCH --array=0-1
#SBATCH --output=/home/fzheng4/wt-c4/eval/x_logs/c4-%A_%a.log
# C4 (eval/CO_OFFLINE.md), steps 2 and 3: X1b's scalar-clock stores re-analysed, every program serially, with
# `parallel.py analyze --both-barrier-orders` (the True half = step 2's parity pass, the False half = CO-R).
# The analysis shards are X1b's own (48 main + 64 PI; long-sc 2; 24h-sc 4 + 2 + 2). Two nodes (the array %2
# rule is the whole budget: array 0-1 = at most 2 nodes), each running $P shards at a time.
#   sbatch eval/baselines/setup/p_co_offline.sh        (commands: setup/co_offline_cmds.txt, shard i -> task i%2)
set -u
W=/home/fzheng4/wt-c4
RT=/home/fzheng4/AccelProf
P=${P:-12}
K=${SLURM_ARRAY_TASK_ID:?}
for d in $W /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
cd $W || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W PY=$RT/.env/bin/python BASELINE_MODES=scalar-clock
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G nproc=$(nproc) task=$K P=$P HEAD=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
awk -v k=$K 'NR%2==k' eval/baselines/setup/co_offline_cmds.txt > /tmp/c4_cmds_$K.txt
wc -l /tmp/c4_cmds_$K.txt
# each line: <results-subdir> <store-tag> <analyze args...>; one process per line, $P at a time
run1() {
  sub=$1; st=$2; shift 2
  mkdir -p $W/eval/results/co-offline/$sub
  echo "start $sub $* $(date -Is)"
  BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$st $PY $W/eval/baselines/parallel.py analyze "$@" \
      --both-barrier-orders --analysis-timeout 84600 --analysis-mem-gb 40 \
      --results-dir $W/eval/results/co-offline/$sub > $W/eval/x_logs/c4-$sub-$(echo "$*" | tr ' /' '__' | cut -c1-80).log 2>&1
  echo "done  $sub $* rc=$? $(date -Is)"
}
export -f run1; export W PY BASELINE_MODES ACCEL_PROF_HOME
mkdir -p $W/eval/x_logs
xargs -P $P -L 1 bash -c 'run1 "$@"' _ < /tmp/c4_cmds_$K.txt
echo "== all done $(date -Is)"

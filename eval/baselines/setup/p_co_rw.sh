#!/usr/bin/env bash
#SBATCH --job-name=c4-co-rw
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --exclusive
#SBATCH --time=1-00:00:00
#SBATCH --array=0-0
#SBATCH --output=/home/fzheng4/wt-c4/eval/x_logs/c4rw-%A_%a.log
# C4 step 3, real-world: the scalar-clock recordings of the recall set (T21b, store realworld-2026-10) and the candidate
# set (T21c, store realworld-2026-10-t21c) re-analysed with CUVEIN_BARRIER_ORDER=0 and attributed (rw_attribute.py), then
# scored by rw_score.py -- the scripts that produced eval/results/realworld/recall.csv and realworld_t21c/recall.csv, run
# from copies of their branches' eval/realworld + eval/baselines (~/c4rw/t21b = study/realworld-recall, ~/c4rw/t21c =
# study/realworld-candidates; the only edit: RW_MODES in rw_attribute.py / rw_score.py, as in C2). The verdict layer is wt-c4's
# python/ (ACCEL_PROF_HOME). One analysis per id, serially; the id lines in setup/co_offline/rw_cmds.txt run $P at a time,
# after them the `pairs K N` lines: the pair-level records of the scalar-clock recordings (co_offline_pairs.py), switch on and off.
set -u
W=/home/fzheng4/wt-c4
RT=/home/fzheng4/AccelProf
P=${P:-16}
for d in $W /mnt/beegfs/fzheng4 /home/fzheng4/c4rw; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
cd $W || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "${CUDA_HOME:-}" ] || { echo "no nvdisasm on $(hostname)"; exit 96; }
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export PY=$RT/.env/bin/python W RT
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G cuda=$CUDA_HOME HEAD=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
OUT=$W/eval/results/co-offline; mkdir -p $OUT/realworld/attrib $OUT/realworld_t21c/attrib $W/eval/x_logs
rw1() {   # <set> <id> <analyze|attrib|both>  |  pairs <K> <N>
  set=$1; id=$2; what=$3
  if [ $set = pairs ]; then
    echo "$(date -Is) pairs $id/$what"; export CUVEIN_HOME=$W
    $PY $W/eval/baselines/setup/co_offline/co_offline_pairs.py $id/$what > $W/eval/x_logs/c4pairs-$id.out 2>&1
    echo "$(date -Is) pairs $id/$what rc=$?"; return
  fi
  case $set in
    t21b) H=/home/fzheng4/c4rw/t21b; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10;      M=$H/eval/realworld/manifest_t21b.csv; RES=$OUT/realworld ;;
    t21c) H=/home/fzheng4/c4rw/t21c; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c; M=$H/eval/realworld/manifest_t21c.csv; RES=$OUT/realworld_t21c ;;
  esac
  export ACCEL_PROF_HOME=$W CUVEIN_BARRIER_ORDER=0 BASELINE_MODES=scalar-clock RW_MODES=scalar-clock BASELINE_TRACE_DIR=$S0
  if [ $what != attrib ]; then
    echo "$(date -Is) analyze $set $id"
    t0=$(date +%s)
    $PY $H/eval/baselines/parallel.py analyze --manifest $M --id $id --analysis-timeout 84600 --analysis-mem-gb 40 \
        --tag "$id-" --results-dir $RES > $W/eval/x_logs/c4rw-analyze-$id.out 2>&1
    echo "$(date -Is) analyze $set $id rc=$? wall=$(( $(date +%s) - t0 ))s"
  fi
  if [ $what != analyze ]; then
    if [ $what = both ] && ! $PY -c "import csv,sys; sys.exit(0 if any(r['verdict'] in ('RACE','CLEAN') for r in csv.DictReader(open('$RES/baselines-cuvein-shard$id-all.csv'))) else 1)" 2>/dev/null; then
      echo "$(date -Is) attribute $set $id skipped: no RACE/CLEAN row"
    else
      t0=$(date +%s)
      $PY $H/eval/realworld/harness/rw_attribute.py --id $id --store $S0 --manifest $M --out $RES/attrib/$id.json > $W/eval/x_logs/c4rw-attrib-$id.out 2>&1
      echo "$(date -Is) attribute $set $id rc=$? wall=$(( $(date +%s) - t0 ))s"
    fi
  fi
}
export -f rw1; export OUT
xargs -P $P -L 1 bash -c 'rw1 "$@"' _ < ${RW_CMDS:-$W/eval/baselines/setup/co_offline/rw_cmds.txt}
echo "== all done $(date -Is)"

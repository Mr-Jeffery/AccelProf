#!/usr/bin/env bash
#SBATCH --job-name=t26-prof
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T26 diagnostic: where a replay at N=16 spends the time outside the pass (perf stat + perf record).
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
source $W/eval/baselines/setup/t26_parity/common.sh
mkcaph; runtime_line
ID=${ID:-P9-crs-cuda}
ROOT=/tmp/$USER-t26-prof-${SLURM_JOB_ID:-x}; mkdir -p $ROOT/cap
env ACCEL_PROF_HOME=$CAPH CUVEIN_HOME=$CAPH BASELINE_MODES=collector-only BASELINE_WORKERS=1 BASELINE_TRACE_DIR=/mnt/beegfs/$USER/t26/prof-${SLURM_JOB_ID:-x} \
    CAP_REAL_LIB=$LIB_INST CAP_DIR=$ROOT/cap $PY $W/eval/baselines/parallel.py collect --id $ID --reps 1 > $ROOT/live.log 2>&1
cap=$(ls -S $ROOT/cap/cap.*.bin | head -1); echo "capture $(stat -c %s $cap)"
which perf
for n in ${NS:-1 16}; do
  d=$ROOT/n$n; mkdir -p $d
  ( cd $d && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_APP_NAME=replay YOSEMITE_WORKER_COUNT=$n \
      LD_LIBRARY_PATH=$S/san-install/lib:$LD_LIBRARY_PATH perf stat -e task-clock,context-switches,cpu-migrations,page-faults \
      ${REPLAY_BIN:-$S/bin/t26_replay2} $cap > out.txt 2> err.txt; tail -14 err.txt | grep -v "^$" )
  ( cd $d && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_APP_NAME=replay YOSEMITE_WORKER_COUNT=$n \
      LD_LIBRARY_PATH=$S/san-install/lib:$LD_LIBRARY_PATH perf record -o perf.data ${REPLAY_BIN:-$S/bin/t26_replay2} $cap > /dev/null 2>&1
    perf report -i perf.data --stdio --no-children --sort dso,symbol 2>/dev/null | grep -v "^#" | grep "%" | head -25
    for sym in "yosemite::PcDependency::gpu_data_analysis" "(anonymous namespace)::pcd_apply"; do
      echo "-- annotate $sym (hottest lines)"
      perf annotate -i perf.data --stdio -s "$sym" 2>/dev/null | grep -E "^ +[0-9]+\.[0-9]+ " | sort -rn | head -25
    done )
done
rm -rf $ROOT

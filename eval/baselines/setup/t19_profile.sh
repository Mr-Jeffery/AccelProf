#!/usr/bin/env bash
#SBATCH --job-name=t19-profile
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
# T19 step 5: where the remaining per-lane-access time goes after the flat buckets -- perf over
# one no-dump run (YOSEMITE_HB_DUMP=0) of P7-hotspot (vector-clock) and P9-fpc (scalar-clock)
# with the worktree runtime (setup/t5b_profile.py, call graphs from DWARF; perf data under
# /mnt/beegfs/$USER/t19_profile, apart from T5b's).
# SPECS="<id>:<mode>:<cap> ..." overrides the two programs.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t19_profile.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}
cd $W || exit 1
export ACCEL_PROF_HOME=${RT:-$W}
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
export BASELINE_HB_DUMP=0
echo "host=$(hostname) $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') runtime $ACCEL_PROF_HOME libsanalyzer $(sha256sum $(ldd $ACCEL_PROF_HOME/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16) perf $(perf --version 2>&1)"
for spec in ${SPECS:-P7-hotspot-cuda:vector-clock:1500 P9-fpc-cuda:scalar-clock:1500}; do
  IFS=: read -r id mode cap <<< "$spec"
  echo "== $id $mode cap ${cap}s $(date -Is)"
  $PY eval/baselines/setup/t5b_profile.py --id $id --mode $mode --cap $cap --freq ${FREQ:-49} --dwarf \
      --work /mnt/beegfs/$USER/t19_profile 2>&1 | head -${LINES_OUT:-120}
done
echo "== done $(date -Is)"

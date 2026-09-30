#!/usr/bin/env bash
#SBATCH --job-name=t5b-stats1
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# T5b: YOSEMITE_HB_STATS (+ mid-kernel snapshots every EVERY records) for one program under
# runtime RT (setup/t5a_stats.py) -> setup/t5b_stats/<LABEL>.json.
#   RT=<checkout> LABEL=<l> EXE=<path> ARGS="..." CAP=<s> EVERY=<n> sbatch -p rtx4060ti16g ... t5b_one_stats.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}
cd $W || exit 1
export ACCEL_PROF_HOME=${RT:-$W}
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G runtime $ACCEL_PROF_HOME libsanalyzer $(sha256sum $(ldd $ACCEL_PROF_HOME/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
$PY eval/baselines/setup/t5a_stats.py --out $W/eval/baselines/setup/t5b_stats --mode ${MODE:-vector-clock} \
    --label ${LABEL:?} --exe ${EXE:?} ${ARGS:+--args "$ARGS"} --cap ${CAP:-600} --every ${EVERY:-0}

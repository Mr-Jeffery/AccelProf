#!/usr/bin/env bash
#SBATCH --job-name=t5b-profile
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
# T5b: perf profile of one vector-clock run with the worktree runtime (setup/t5b_profile.py).
#   ID=<manifest id> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t5b-profile-%j.log eval/baselines/setup/t5b_profile.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
time $PY eval/baselines/setup/t5b_profile.py --id ${ID:-P4-graph-coloring-norace-large} --cap ${CAP:-1200} --freq ${FREQ:-29} ${DWARF---dwarf} 2>&1 | head -${LINES_OUT:-60}

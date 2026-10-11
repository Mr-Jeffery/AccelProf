#!/usr/bin/env bash
#SBATCH --job-name=t19-gate
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=00:30:00
# T19: test_instance_gate.py alone on the artifacts the preceding green-set run left (the T17 /
# T18 protocol: "305 passed, 2 skipped, then 55/55"), with the worktree runtime.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t19_gate.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
$PY -m pytest python/test_instance_gate.py -q -p no:cacheprovider 2>&1 | tail -2

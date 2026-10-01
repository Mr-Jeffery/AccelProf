#!/usr/bin/env bash
#SBATCH --job-name=t1a-skipcheck
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t1a-skipcheck-%j.log
# T1a (eval/CP_ASYNC_REPORT.md): python/test_cp_async.py with the T1a runtime (all pass) and
# with the main checkout's installed, pre-T1a runtime (all skip, with the reason). getall.sh
# traces with the runtime of the checkout the test runs from, so for the second run this
# worktree's lib / nv-compute/lib symlinks point at the main checkout's for the duration.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_skipcheck.sh
set -u
W=/home/fzheng4/wt-T1a; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
L0=$(readlink $W/lib); N0=$(readlink $W/nv-compute/lib)
restore() { ln -sfn "$L0" $W/lib; ln -sfn "$N0" $W/nv-compute/lib; }
trap restore EXIT
t() { echo "== collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) -> libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}') | cut -c1-16)"
      $PY -m pytest python/test_cp_async.py -rs -p no:cacheprovider -W ignore 2>&1 | tail -3; }
t
ln -sfn $A/lib $W/lib; ln -sfn $A/nv-compute/lib $W/nv-compute/lib
t
restore; trap - EXIT
echo "restored: lib -> $(readlink $W/lib), nv-compute/lib -> $(readlink $W/nv-compute/lib)"
echo "== done $(date -Is)"

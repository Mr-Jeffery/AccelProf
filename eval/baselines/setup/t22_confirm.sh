#!/usr/bin/env bash
#SBATCH --job-name=t22-confirm
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T22, verification A's evidence: test_no_dump.py (both modes; its scalar-clock recordings are the
# sync instance under test) with YOSEMITE_HB_SHARDS=8 and every drain threaded, pytest's tmp dirs kept
# in BASETEMP so the recordings' accelprof logs can be searched for the sharded pass's start line.
#   BASETEMP=<dir> sbatch -p <gpu partition> -w <node> -o <log> eval/baselines/setup/t22_confirm.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export YOSEMITE_HB_SHARDS=8 YOSEMITE_HB_SHARD_INLINE_MAX=0
B=${BASETEMP:?set BASETEMP}; rm -rf $B
echo "host=$(hostname) HEAD=$(git rev-parse --short HEAD) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
$PY -m pytest python/test_no_dump.py -q -p no:cacheprovider --basetemp=$B 2>&1 | tail -2
echo "accelprof logs: $(find $B -name '*.accelprof.log' | wc -l)"
echo "  with 'scalar-clock pass sharded by location: 8 shards': $(grep -rl 'scalar-clock pass sharded by location: 8 shards' $B --include='*.accelprof.log' | wc -l)"
echo "  with 'ignored: vector-clock mode': $(grep -rl 'ignored: vector-clock mode' $B --include='*.accelprof.log' | wc -l)"
echo "== done $(date -Is)"

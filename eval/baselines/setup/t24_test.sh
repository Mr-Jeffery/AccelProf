#!/usr/bin/env bash
#SBATCH --job-name=t24-test
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=01:00:00
# T24: python/test_syncwarp.py (synthetic + GPU parts) with the runtime W/lib points at, every trace
# re-recorded; with YOSEMITE_HB_SHARDS=$SHARDS if set. Step 1 runs it on the 38af04e tree with the
# installed runtime (lib -> /home/fzheng4/AccelProf/lib), where it must fail.
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-test-%j.log <W>/eval/baselines/setup/t24_test.sh
set -u
W=${W:-/home/fzheng4/wt-t24}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_DUMP YOSEMITE_HB_NO_ENGINE YOSEMITE_HB_SHARDS YOSEMITE_HB_SHARD_INLINE_MAX YOSEMITE_HB_MODE
[ -n "${SHARDS:-}" ] && export YOSEMITE_HB_SHARDS=$SHARDS
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -uno | wc -l) SHARDS=${YOSEMITE_HB_SHARDS:-unset} $(date -Is)"
echo "runtime: lib -> $(readlink -f lib) collector $(h lib/libcompute_sanitizer.so) libsanalyzer $(h $(ldd lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}'))"
$PY -m pytest python/test_syncwarp.py -rfExXs --tb=line -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -40
echo "== done $(date -Is)"

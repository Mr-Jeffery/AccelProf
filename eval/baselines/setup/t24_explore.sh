#!/usr/bin/env bash
#SBATCH --job-name=t24-explore
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=00:30:00
# T24 step 1 probe: build testdata/syncwarp_diverged_waw.cu (and the FIRST_SYNCWARP=1 control, and
# a variant with the clear inside lane 0's group), print the SASS around the syncwarps, record each
# with the runtime W/lib points at (vector-clock, dump), and print the syncwarp records, the shared
# records of block 0 and the race keys (t24_events.py).
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-explore-%j.log <W>/eval/baselines/setup/t24_explore.sh
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
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_DUMP YOSEMITE_HB_NO_ENGINE YOSEMITE_HB_SHARDS YOSEMITE_HB_MODE
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) $(date -Is)"
echo "runtime: lib -> $(readlink -f lib) collector $(h lib/libcompute_sanitizer.so) libsanalyzer $(h $(ldd lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}'))"
T=$(mktemp -d /tmp/t24-explore-XXXX)
SRC=python/testdata/syncwarp_diverged_waw.cu
sed 's|^  if (lane == 0) updated\[warp\] = false;.*$||; s|      if (lane == 16 \&\& nlab\[v\] >= 0)|      if (lane == 0) updated[warp] = false;\n      if (lane == 16 \&\& nlab[v] >= 0)|' $SRC > $T/inside.cu
for var in race control inside; do
  mkdir -p $T/$var; f=$SRC; flags=""
  [ $var = control ] && flags="-DFIRST_SYNCWARP=1"
  [ $var = inside ] && f=$T/inside.cu
  nvcc -arch=native -lineinfo --cudart shared $flags $f -o $T/$var/cc || { echo "build $var failed"; continue; }
  echo "==== $var: SASS (syncwarp-related lines)"
  cuobjdump -sass $T/$var/cc | grep -E "WARPSYNC|NOP|BRA.CONV|CALL|BSSY|BSYNC|STS|LDS|RET|EXIT" | head -40
  ( cd $W && YOSEMITE_HB_DUMP=1 bash getall.sh $T/$var/cc > $T/$var/getall.log 2>&1 ); echo "getall rc=$?"
  grep -E "cc_vertex_data:|ERROR|rror" $T/$var/getall.log | head -5
  for k in $T/$var/dependency_cc*/kernel_*.json; do
    echo "-- $k"; $PY eval/baselines/setup/t24_events.py $k --blocks 1 --warps 2
  done
done
echo "== done $(date -Is)"

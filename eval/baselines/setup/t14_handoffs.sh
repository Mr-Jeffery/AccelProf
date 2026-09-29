#!/usr/bin/env bash
#SBATCH --job-name=t14-handoffs
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T14: the Sanitizer collector's own A2 inversion rate on the lock idiom
# (python/testdata/lock_contention_a2.cu, kernel kcontend), at T13's contention levels (1x2,
# 1x4, 4x4 warps; ITERS acquisitions per warp; RUNS runs each), with the worktree runtime --
# counted by eval/baselines/a2_window_count.py handoffs.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t14-handoffs-%j.log \
#       eval/baselines/setup/t14_handoffs.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/agent-a132f9279c0d8edd0}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD)"
echo "collector $(sha256sum lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
T=/tmp/$USER-t14-handoffs; rm -rf "$T"; mkdir -p "$T"
for cfg in 1x2 1x4 4x4; do
  nb=${cfg%x*}; nw=${cfg#*x}
  D=$T/$cfg; mkdir -p "$D"
  nvcc -arch=native -lineinfo --cudart shared -DNB=$nb -DNW=$nw -DITERS=${ITERS:-16} \
      python/testdata/lock_contention_a2.cu -o "$D/lock_contention_a2"
  for r in $(seq 1 ${RUNS:-5}); do
    bash getall.sh "$D/lock_contention_a2" > "$D/getall_$r.log" 2>&1
    sleep 1                                   # distinct dependency_* directory names
  done
  echo "== $cfg ($(ls -d $D/dependency_* | wc -l) runs)"
  .env/bin/python eval/baselines/a2_window_count.py handoffs \
      --dots "$D"/lock_contention_a2_extracted_cubins/*.dot -- "$D"/dependency_lock_contention_a2_*/kernel_*.json
done
rm -rf "$T"
echo "== done $(date -Is)"

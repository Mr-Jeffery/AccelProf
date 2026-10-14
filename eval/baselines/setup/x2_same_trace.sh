#!/usr/bin/env bash
#SBATCH --job-name=x2-same
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c21,c37
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/.claude/worktrees/wt-x2/eval/baselines/setup/build_logs/x2-same-%j.log
# X2 (eval/FINAL_CERTAIN.md section 4): setup/x2_same_trace.py on the programs whose two
# recordings differ beyond the policy's own effect, recorded with the lossless dump under both
# policies and replayed by hb_oracle.py under both. Installed runtime (the freeze).
#   W=<worktree> sbatch [-w c74] eval/baselines/setup/x2_same_trace.sh
#   PIN8G=1 sbatch -p rtx4060ti8g -w c26 eval/baselines/setup/x2_same_trace.sh   (an 8g node)
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x2}; REPS=${REPS:-3}
IDS=${IDS:-P4-reduction-norace-small,P4-matrix-multiplication-racy-small,P4-rule-110-racy-small,P4-graph-coloring-racy-large,P4-graph-connectivity-racy-large,P4-uts-racy-small,P4-uts-norace-small,P5-race_interblock_none-lock_rtraw,P5-norace_interblock_lock_waw}
cd $W || exit 1
source eval/baselines/setup/home_quota_guard.sh
export ACCEL_PROF_HOME=$W CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.3}
source eval/baselines/gpu_env.sh
# rtx4060ti8g nodes may carry a second, older GPU: PIN8G=1 exposes only the sm_89 one
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_NO_ENGINE YOSEMITE_HB_GATE YOSEMITE_HB_GATE_POLICY \
      CUVEIN_GATE CUVEIN_GATE_POLICY CUVEIN_PREFER_RECORDS CUVEIN_PREFER_AGGREGATES \
      YOSEMITE_HB_HOST_MEMCPY YOSEMITE_HB_STRICT BASELINE_HB_DUMP YOSEMITE_HB_STATS
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1)" \
     "HEAD=$(git -C $W rev-parse --short HEAD) $(date -Is)"
echo "runtime: libsanalyzer $(h $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}'))" \
     "collector $(h $W/lib/libcompute_sanitizer.so) fatbin $(h $W/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)" \
     "hb_oracle.py $(h python/hb_oracle.py)"
OUT=/mnt/beegfs/$USER/x2-same-trace; mkdir -p $OUT
$PY eval/baselines/setup/x2_same_trace.py --out $OUT --reps $REPS --ids $IDS \
    --watch P4-reduction-norace-small:0xa20-0x1680
echo "== rc=$? $(date -Is)"
cp $OUT/same_trace.json $W/eval/results/final-certain-invariant/same_trace.json

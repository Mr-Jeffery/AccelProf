#!/usr/bin/env bash
#SBATCH --job-name=x2-certain
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c21,c37
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/.claude/worktrees/wt-x2/eval/baselines/setup/build_logs/x2-certain-%j.log
# X2 -- the sound column (eval/FINAL_CERTAIN.md). P4 + P5 (61 programs), vector-clock mode only,
# no-dump (BASELINE_HB_DUMP=0: HbClock's aggregates, verdicts from them since X0), HB_STATS at
# kernel end, 3 reps, confirmation details, recorded TWICE on one node by one job:
#   leg 1  YOSEMITE_HB_GATE_POLICY=certain   (T16: chain edges only between RMWs whose windows
#          do not overlap; the collector reads the knob once at start, blib.base_env passes it)
#          -> store cuvein_traces/final-certain, eval/results/final-certain/,
#             eval/baselines/confirm_final_certain/
#   leg 2  YOSEMITE_HB_GATE_POLICY=recorded  (today's default, set explicitly)
#          -> store cuvein_traces/final-certain-recorded, eval/results/final-certain-recorded/,
#             eval/baselines/confirm_final_certain_recorded/
# so the invariant Rep_certain >= Rep_recorded is checked between two recordings made alike
# (eval/baselines/final_certain.py). The runtime is the installed one (the code freeze, X0): W's
# lib/build/.env/ScoR/cuHadron/nv-compute/lib are symlinks to the main checkout.
# Timeout: --timeout-cap 1200 and --timeout-floor $FLOOR (default 1200). The harness's per-program
# timeout is min(max(10 x native, floor), cap); with the default floor of 120 s the ScoR apps of
# sub-second native time (matrix-multiplication-large, uts-large) would be killed at 120 s, not at
# the 1,200 s cap. FLOOR=120 restores the harness default.
#   W=<worktree> sbatch eval/baselines/setup/p_final_certain.sh
# (passing -x on the sbatch command line REPLACES the --exclude above)
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x2}
FLOOR=${FLOOR:-1200}; REPS=${REPS:-3}; LEGS=${LEGS:-certain recorded}; PSETS=${PSETS:-P4,P5}
cd $W || exit 1
source eval/baselines/setup/home_quota_guard.sh
export ACCEL_PROF_HOME=$W CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.3}
source eval/baselines/gpu_env.sh
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
# nothing inherited may steer the collector or the verdict layer
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_NO_ENGINE YOSEMITE_HB_GATE YOSEMITE_HB_GATE_POLICY \
      CUVEIN_GATE CUVEIN_GATE_POLICY CUVEIN_PREFER_RECORDS CUVEIN_PREFER_AGGREGATES \
      YOSEMITE_HB_HOST_MEMCPY YOSEMITE_HB_STRICT
export BASELINE_MODES=vector-clock BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1)" \
     "mem=$(free -g | awk '/Mem:/{print $2}')G $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g')" \
     "HEAD=$(git -C $W rev-parse --short HEAD) cuda=$(readlink -f $CUDA_HOME) $(date -Is)"
echo "runtime: libsanalyzer $(h $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}'))" \
     "collector $(h $W/lib/libcompute_sanitizer.so) fatbin $(h $W/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"
echo "harness: parallel.py $(h eval/baselines/parallel.py) run_cuvein.py $(h eval/baselines/run_cuvein.py)" \
     "sync_dominance.py $(h python/sync_dominance.py) floor=$FLOOR cap=1200 reps=$REPS psets=$PSETS legs=[$LEGS]"
mkdir -p /mnt/beegfs/$USER/cuvein_traces && chmod 700 /mnt/beegfs/$USER
for leg in $LEGS; do
  case $leg in
    certain)  tag=final-certain;          conf=confirm_final_certain ;;
    recorded) tag=final-certain-recorded; conf=confirm_final_certain_recorded ;;
    *) echo "unknown leg $leg"; exit 2 ;;
  esac
  res=$W/eval/results/$tag; cdir=$W/eval/baselines/$conf
  mkdir -p $res $cdir
  echo "== leg $leg: YOSEMITE_HB_GATE_POLICY=$leg store=/mnt/beegfs/$USER/cuvein_traces/$tag $(date -Is)"
  t0=$(date +%s)
  YOSEMITE_HB_GATE_POLICY=$leg BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$tag \
    $PY eval/baselines/parallel.py run --pset $PSETS --reps $REPS --confirm \
      --timeout-floor $FLOOR --timeout-cap 1200 --tag $tag \
      --results-dir $res --confirm-dir $cdir
  echo "== leg $leg done rc=$? in $(( $(date +%s) - t0 )) s $(date -Is)"
done
# steps 2 and 3 on the node that has BeeGFS mounted (the kernel JSONs live there)
$PY eval/baselines/final_certain.py check --store /mnt/beegfs/$USER/cuvein_traces/final-certain \
    --results eval/results/final-certain --policy certain
$PY eval/baselines/final_certain.py check --store /mnt/beegfs/$USER/cuvein_traces/final-certain-recorded \
    --results eval/results/final-certain-recorded --policy recorded
$PY eval/baselines/final_certain.py invariant \
    --certain-store /mnt/beegfs/$USER/cuvein_traces/final-certain \
    --recorded-store /mnt/beegfs/$USER/cuvein_traces/final-certain-recorded \
    --certain-confirm eval/baselines/confirm_final_certain \
    --recorded-confirm eval/baselines/confirm_final_certain_recorded \
    --certain-results eval/results/final-certain --recorded-results eval/results/final-certain-recorded \
    --out eval/results/final-certain-invariant
echo "== all done $(date -Is)"

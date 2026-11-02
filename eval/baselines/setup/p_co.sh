#!/usr/bin/env bash
#SBATCH --job-name=c1-co
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --array=0-47
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/co-%A_%a.log
# C1 (eval/COLLECTOR_ONLY.md): collector-only mode, the original cuVein configuration: YOSEMITE_HB_TRACE unset, so
# no HbClock, no hb_sync_pass / hb_races / hb_rmw_points / hb_chain; verdicts from the static certificates alone.
# X1b's harness and policy otherwise (p_final.sh of eval/final-sweep-b): ONE mode (BASELINE_MODES=collector-only), the
# native runs of the same program in the same job on the same node, --reps 3, --confirm, --keep-all, tool timeout
# = cap = $CAP for every rep (a TIMEOUT row means "did not finish in CAP s"), offline analysis capped at 14,400 s,
# accelprof -n 1 (parallel.py, unchanged). Differences from p_final.sh: no BASELINE_HB_DUMP / YOSEMITE_HB_STATS /
# BASELINE_HB_SHARDS (all of them knobs of HbClock or of the sync pass; blib.base_env drops them for this mode).
# Stores /mnt/beegfs/$USER/cuvein_traces/final-2026-11-co{,-long,-24h}, results eval/results/collector-only/.
#   main:  sbatch eval/baselines/setup/p_co.sh      PI: PSETS=PI NSHARDS=64 TAG=co-pi sbatch --array=0-63 ...
#   dry run: ID_FILE=eval/baselines/setup/co_dryrun_ids.txt NSHARDS=1 TAG=co-dryrun RES=collector-only-dryrun #            STORE_TAG=final-2026-11-co-dryrun sbatch --array=0 eval/baselines/setup/p_co.sh
set -u
# X1b: node probe before anything else (a node without /home or BeeGFS is not a measurement)
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d not readable"; exit 2; }; done
W=${W:-/home/fzheng4/wt-co}
RT=/home/fzheng4/AccelProf
source $W/eval/baselines/setup/home_quota_guard.sh
PSETS=${PSETS:-P1,P3,P4,P5,P6,P7,P9}; NSHARDS=${NSHARDS:-48}; TAG=${TAG:-co}
K=${SHARD:-${SLURM_ARRAY_TASK_ID:?}}
CAP=${CAP:-1200}; STORE_TAG=${STORE_TAG:-final-2026-11-co}; RES=${RES:-collector-only}
cd $RT || exit 1
# no detector knob from the submitting shell may leak in: defaults only
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export BASELINE_MODES=collector-only
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$STORE_TAG
h() { sha256sum "$1" | cut -c1-16; }
# node problems are not program failures: exit 2 before any row is written (resubmit elsewhere)
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
[ -x $CUDA_HOME/bin/nvdisasm ] && [ -f $CUDA_HOME/compute-sanitizer/libsanitizer-public.so ] \
    || { echo "NODE-PROBLEM $(hostname): no CUDA 13.3 at $CUDA_HOME"; exit 2; }
[ -d /mnt/beegfs/$USER ] || { echo "NODE-PROBLEM $(hostname): BeeGFS not mounted"; exit 2; }
SAN=$(ldd $RT/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
echo "host=$(hostname) gpu=[$gpu] mem=$(free -g | awk '/Mem:/{print $2}')G cpu=[$(lscpu | sed -n 's/^Model name: *//p')]"
SEL=(--pset $PSETS)
[ -n "${IDS:-}" ] && SEL=(--id $IDS)
[ -n "${ID_FILE:-}" ] && SEL=(--id-file $ID_FILE)
echo "no HbClock, no sync pass (hb_shards n/a) nproc=$(nproc) analyzer: accelprof -n 1"
echo "job=${SLURM_JOB_ID:-} array=${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID:-} partition=${SLURM_JOB_PARTITION:-} shard=$K/$NSHARDS select=[${SEL[*]}] tag=$TAG cap=${CAP}s reps=${REPS:-3} modes=$BASELINE_MODES store=$BASELINE_TRACE_DIR $(date -Is)"
echo "runtime $RT HEAD=$(git -C $RT rev-parse --short=12 HEAD) libsanalyzer=$(h $SAN) ($SAN) collector=$(h $RT/lib/libcompute_sanitizer.so) fatbin=$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin) late=$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)"
echo "harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($CUDA_HOME/bin/nvcc --version | tail -1)"
mkdir -p $W/eval/results/$RES $RT/eval/baselines/confirm_$RES
$PY $W/eval/baselines/parallel.py run "${SEL[@]}" --shard $K/$NSHARDS --reps ${REPS:-3} --confirm --keep-all \
    --timeout-floor $CAP --timeout-cap $CAP --analysis-timeout 14400 --tag $TAG \
    --results-dir $W/eval/results/$RES --confirm-dir $RT/eval/baselines/confirm_$RES
echo "== done rc=$? $(date -Is)"

#!/usr/bin/env bash
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
# X12 Table 3 collector-only column at N=BASELINE_WORKERS shards (Jeffery 2026-11-07): collector-only recording of the ids of $PSET
# shards, p_co.sh's policy (C1, eval/collector-only): --reps 3, --confirm, native in the same job, cap 1,200 s, BASELINE_KEEP_REPS=1.
# Baseline for the gate = C1's final-2026-11-co (same builds, accelprof -n 1). Sharded over SLURM_ARRAY_TASK_ID of NSHARDS.
#   PSET=P4 NSHARDS=4 STORE=final-2026-11-co-sh-p4 RES=co-sharded-p4 CAP=84600 W=<harness> RT=<runtime> sbatch --array=0-3 -J x12-p4 -o $W/eval/x_logs/x12-p4-%A_%a.log x12_suite.sbatch
# The tool timeout of every rep is CAP (parallel.py run passes --timeout-floor; collect does not); rows carry cap=<CAP>.
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
W=${W:?}; RT=${RT:?}; PSET=${PSET:-}; IDFILE=${IDFILE:-}; REPS=${REPS:-3}; NSHARDS=${NSHARDS:-8}; K=${SLURM_ARRAY_TASK_ID:-0}; N=${N:-16}
SEL=(--pset $PSET --shard $K/$NSHARDS); [ -n "$IDFILE" ] && SEL=(--id-file $IDFILE)   # IDFILE: one id per line (the -n 1 controls)
STORE=${STORE:?}; RES=${RES:?}; CAP=${CAP:-84600}
MANIFEST=${MANIFEST:-}; CUDAV=${CUDAV:-13.3}; ATO=${ATO:-14400}   # real-world sets: MANIFEST=<manifest_t21b|c.csv> CUDAV=13.4 ATO=3600 (C2's policy)
source $W/eval/baselines/setup/home_quota_guard.sh
cd $RT || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export BASELINE_MODES=collector-only BASELINE_WORKERS=$N BASELINE_KEEP_REPS=1
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-$CUDAV
source /home/fzheng4/AccelProf/eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-$CUDAV/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$STORE
h() { sha256sum "$1" | cut -c1-16; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
SAN=$(ldd $RT/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
echo "host=$(hostname) gpu=[$gpu] nproc=$(nproc) cpu=[$(lscpu | sed -n 's/^Model name: *//p')] job=${SLURM_JOB_ID} shard=$K/$NSHARDS N=$N store=$STORE $(date -Is)"
echo "runtime $RT HEAD=$(git -C $RT rev-parse --short=12 HEAD) libsanalyzer=$(h $SAN) collector=$(h $RT/lib/libcompute_sanitizer.so) harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
mkdir -p $W/eval/results/$RES/confirm
$PY $W/eval/baselines/parallel.py run ${MANIFEST:+--manifest $MANIFEST} "${SEL[@]}" --reps $REPS --confirm --keep-all \
    --timeout-floor $CAP --timeout-cap $CAP --analysis-timeout $ATO --analysis-workers 16 --tag x12${PSET:-ids} \
    --results-dir $W/eval/results/$RES --confirm-dir $W/eval/results/$RES/confirm
echo "== done rc=$? $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=x1b-final
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --array=0-47
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/finalb-%A_%a.log
# X1b (eval/FINAL_SWEEP_B.md): X1's recording repeated on the T22 cont. + T23 + T24 runtime (install f551ca0:
# libsanalyzer 5a20fd14ab6c6806, collector b746b4dd23e90f46, fatbin a2d7368bc1c61986, late e96343121c74ca0a), with ONE
# difference: scalar-clock runs use YOSEMITE_HB_SHARDS=$HB_SHARDS (blib.base_env, via BASELINE_HB_SHARDS; vector-clock
# never sees it). Stores final-2026-11*, results eval/results/final-b*, worktree wt-x1b (branch eval/final-sweep-b).
# Below: X1's header, unchanged.
# X1, the final recording (eval/FINAL_SWEEP.md). Every number in the paper's evaluation comes
# from it: ONE runtime (the T16 + T20 install recorded in d38d057: libsanalyzer 2201fcb7,
# collector ee78cb89, fatbin a2d7368b; the X0 verdict layer of cuVein 4094187) and ONE
# configuration for every row:
#   BASELINE_HB_DUMP=0 (no hb_events, HbClock's aggregates only), YOSEMITE_HB_STATS=1 (hb_stats
#   per kernel JSON), both modes in ONE job per shard (collect_one wipes <store>/<id>; per-mode
#   jobs would clobber each other -- p_evcand.sh), --reps 3, --confirm, --keep-all into
#   /mnt/beegfs/$USER/cuvein_traces/final-2026-10, the tool timeout equal to the cap for every
#   rep (--timeout-floor = --timeout-cap = CAP, 1200 s here; the 10x-native term of
#   min(max(10 x native, floor), cap) never binds, so a TIMEOUT row always means "did not finish
#   in CAP s"), the offline analysis capped at 14,400 s per mode (--analysis-timeout, X0's value; past it a row is
#   ERROR analysis-timeout, never CLEAN).
# The runtime is the main checkout RT (ACCEL_PROF_HOME: the installed libraries, bin/accelprof,
# python/ for the verdict layer, the live manifest's binaries and corpora); the harness is this
# file's checkout W (branch eval/final-sweep). Shard CSVs -> W/eval/results/$RES/, confirmation
# JSONs -> RT/eval/baselines/confirm_$RES/ (untracked, outlives the worktree), logs -> RT's
# build_logs/final-*.log.
#   main (P1,P3,P4,P5,P6,P7,P9, 595 programs):   sbatch eval/baselines/setup/p_final.sh
#   PI (4,130 programs):  PSETS=PI NSHARDS=64 TAG=finalpi sbatch --array=0-63 -J x1-final-pi \
#                           -o <RT>/eval/baselines/setup/build_logs/finalpi-%A_%a.log eval/baselines/setup/p_final.sh
#   one shard again (node failure): the same PSETS/NSHARDS/TAG with --array=k. The shard split is
#     k/NSHARDS, never SLURM_ARRAY_TASK_COUNT (a resubmitted subset would re-split; T20 gotcha).
#     Pass -x on the command line only as the FULL exclude list (it replaces the one above).
#   REPS=<n> (default 3; only the 24 h pass, p_final_24h.sh, sets 1 -- 2026-10-14, Jeffery's choice)
#   dry run (step 1): IDS=<id,id,...> NSHARDS=1 TAG=final-dryrun RES=final-dryrun \
#                     STORE_TAG=final-2026-10-dryrun sbatch --array=0 eval/baselines/setup/p_final.sh
set -u
# X1b: node probe before anything else (a node without /home or BeeGFS is not a measurement)
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d not readable"; exit 2; }; done
W=${W:-/home/fzheng4/wt-x1b}
RT=/home/fzheng4/AccelProf
source $W/eval/baselines/setup/home_quota_guard.sh
PSETS=${PSETS:-P1,P3,P4,P5,P6,P7,P9}; NSHARDS=${NSHARDS:-48}; TAG=${TAG:-final-b}
K=${SHARD:-${SLURM_ARRAY_TASK_ID:?}}
CAP=${CAP:-1200}; STORE_TAG=${STORE_TAG:-final-2026-11}; RES=${RES:-final-b}
HB_SHARDS=${HB_SHARDS:-16}
cd $RT || exit 1
# no detector knob from the submitting shell may leak in: defaults only
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
[ -n "${MODES:-}" ] && export BASELINE_MODES=$MODES
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=$HB_SHARDS
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
echo "hb_shards(scalar-clock)=$HB_SHARDS nproc=$(nproc)"
echo "job=${SLURM_JOB_ID:-} array=${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID:-} partition=${SLURM_JOB_PARTITION:-} shard=$K/$NSHARDS select=[${SEL[*]}] tag=$TAG cap=${CAP}s reps=${REPS:-3} modes=${BASELINE_MODES:-both} store=$BASELINE_TRACE_DIR $(date -Is)"
echo "runtime $RT HEAD=$(git -C $RT rev-parse --short=12 HEAD) libsanalyzer=$(h $SAN) ($SAN) collector=$(h $RT/lib/libcompute_sanitizer.so) fatbin=$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin) late=$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)"
echo "harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $($CUDA_HOME/bin/nvcc --version | tail -1)"
mkdir -p $W/eval/results/$RES $RT/eval/baselines/confirm_$RES
$PY $W/eval/baselines/parallel.py run "${SEL[@]}" --shard $K/$NSHARDS --reps ${REPS:-3} --confirm --keep-all \
    --timeout-floor $CAP --timeout-cap $CAP --analysis-timeout 14400 --tag $TAG \
    --results-dir $W/eval/results/$RES --confirm-dir $RT/eval/baselines/confirm_$RES
echo "== done rc=$? $(date -Is)"

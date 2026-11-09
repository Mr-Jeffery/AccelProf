#!/bin/bash
# C2: collector-only detector runs of the given ids (T21b/T21c recall policy: --reps 1 --confirm, tool timeout = cap, analysis timeout),
# then a CPU-node attribution job (co_attr.sh).   SET=recall|cand IDS="..." [FLAVOR=main|c5400] sbatch ... co_job.sh
# FLAVOR main: 1,200 s, store $S0, results eval/results/$RESNAME.  FLAVOR c5400: 5,400 s, store $S0/c5400, results .../c5400.
# Exit 97 BeeGFS/home unreadable, 98 not exactly one sm_89 GPU, 99 runtime hashes differ from f551ca0, 96 CUDA missing.
# array mode: LIST=<file of "SET|id id"> picks line $SLURM_ARRAY_TASK_ID
if [ -n "${LIST:-}" ]; then L=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" $LIST); export SET=${L%%|*} IDS=${L#*|}; fi
source /home/fzheng4/wt-co-rw/eval/realworld/harness/co_header.sh || exit $?
FLAVOR=${FLAVOR:-main}
export ACCEL_PROF_HOME=$A
export CUDA_HOME=${RW_CUDA_HOME:-/usr/local/cuda-13.4}
[ -d "$CUDA_HOME/bin" ] || { echo "C2: host=$(hostname) $CUDA_HOME missing" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
h16() { sha256sum "$1" | cut -c1-16; }
LSA=$(ldd $A/lib/libcompute_sanitizer.so | awk '/libsanalyzer.so/{print $3; exit}')
HS=$(h16 $LSA); HC=$(h16 $A/lib/libcompute_sanitizer.so); HF=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)
HL=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)
GPU=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tr '\n' ';')
NP=$(nproc)
echo "C2 job: host=$(hostname) job=${SLURM_JOB_ID:-none} set=$SET flavor=$FLAVOR date=$(date -Is) nproc=$NP"
echo "C2 job: gpu=$GPU cuda_home=$CUDA_HOME HEAD=$(git -C $W rev-parse --short HEAD) runtime_checkout=$(git -C $A rev-parse --short HEAD)"
echo "C2 job: runtime libsanalyzer=$HS ($LSA) collector=$HC fatbin=$HF late=$HL"
if [ "${HS:0:16}" != 5a20fd14ab6c6806 ] || [ "${HC:0:8}" != b746b4dd ] || [ "${HF:0:8}" != a2d7368b ]; then
  echo "C2: RUNTIME HASH MISMATCH on $(hostname): want 5a20fd14ab6c6806/b746b4dd/a2d7368b" >&2; exit 99
fi
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}')
[ "$(echo "$IDX" | grep -c .)" = 1 ] || { echo "C2: not exactly one sm_89 GPU on $(hostname): $GPU" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
GPU="$GPU used_index=$IDX"
case "$FLAVOR" in
  main)  TO=1200; S=$S0;        RES=$W/eval/results/$RESNAME;        CONF=$W/eval/baselines/confirm_$RESNAME ;;
  c5400) TO=5400; S=$S0/c5400;  RES=$W/eval/results/$RESNAME/c5400;  CONF=$W/eval/baselines/confirm_$RESNAME/c5400 ;;
  *) echo "bad FLAVOR $FLAVOR" >&2; exit 2 ;;
esac
ATO=3600
export BASELINE_MODES=collector-only BASELINE_TRACE_DIR=$S
LOG=$W/eval/x_logs; mkdir -p $LOG $RES $CONF $S
for id in ${IDS:-}; do
  echo "=== $(date -Is) run $id flavor=$FLAVOR"
  $PY $W/eval/baselines/parallel.py run --manifest $MANIFEST --id $id --reps 1 --confirm \
      --timeout-floor $TO --timeout-cap $TO --analysis-timeout $ATO --tag "$id-" \
      --results-dir $RES --confirm-dir $CONF > $LOG/co-run-$FLAVOR-$id.out 2>&1
  echo "  parallel.py rc=$? ($(tail -1 $LOG/co-run-$FLAVOR-$id.out | cut -c1-120))"
  if [ ! -s "$S/$id/meta.json" ] || ! timeout 60 ls "$S/$id" >/dev/null 2>&1; then echo "C2: host=$(hostname) store unreadable after run of $id; result void" >&2; exit 97; fi
  $PY $W/eval/realworld/harness/rw_postmeta.py --meta $S/$id/meta.json --flavor co-$FLAVOR --shards 0 --nproc $NP \
      --libsanalyzer $HS --collector $HC --fatbin $HF --fatbin-late $HL --cuda-home $CUDA_HOME --gpu "$GPU" \
      --job "${SLURM_JOB_ID:-none}" --head "$(git -C $W rev-parse HEAD)" --timeout $TO 2>&1 | tail -2
done
if [ -n "${IDS:-}" ]; then
  ( cd $W && SET=$SET sbatch --parsable --job-name="co-attr-${IDS%% *}" --partition=normal --nodes=1 --ntasks=1 --cpus-per-task=8 --time=23:50:00 \
      --export=ALL,SET=$SET,FLAVOR=$FLAVOR,IDS="$IDS" --output=$W/eval/x_logs/co-attr-$FLAVOR-${IDS%% *}-%j.log eval/realworld/harness/co_attr.sh )
fi
echo "=== $(date -Is) done"

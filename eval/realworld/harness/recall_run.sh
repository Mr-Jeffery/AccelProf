#!/bin/bash
# T21b recall job: detector runs (both modes) of the given target-variant ids on the installed runtime,
# then kernel-aware attribution of every report. One id = one parallel.py run (both modes in it).
#   IDS="amrex-1-buggy amrex-1-fixed" [FLAVOR=main|certain|vc5400|proto] sbatch ... recall_job.sh
# FLAVOR main     both modes, store $S0, results eval/results/realworld, confirm eval/baselines/confirm_realworld
# FLAVOR certain  vector-clock only under YOSEMITE_HB_GATE_POLICY=certain ("Race (sound)"), store $S0/certain
# FLAVOR vc5400   vector-clock only, timeout 5,400 s (the second pass for the timeouts), store $S0/vc5400
# The whole job exits non-zero (97) when BeeGFS/home/the worktree is unreadable, 98 when the GPU is not a single
# sm_89 device, 99 when the installed runtime's hashes differ from 38af04e's (libsanalyzer a01c1666, collector
# 83af1437, fatbin a2d7368b).
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
FLAVOR=${FLAVOR:-main}
export ACCEL_PROF_HOME=$A
export CUDA_HOME=${RW_CUDA_HOME:-/usr/local/cuda-13.3}
[ -d "$CUDA_HOME/bin" ] || { echo "T21b: host=$(hostname) $CUDA_HOME missing" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh          # keeps ACCEL_PROF_HOME and CUDA_HOME; sets PATH, LD_LIBRARY_PATH, PY
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
h16() { sha256sum "$1" | cut -c1-16; }
LSA=$(ldd $A/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}')
HS=$(h16 $LSA); HC=$(h16 $A/lib/libcompute_sanitizer.so); HF=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)
HL=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)
GPU=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tr '\n' ';')
NP=$(nproc); if [ "$NP" -ge 64 ]; then N=32; else N=16; fi
echo "T21b job: host=$(hostname) job=${SLURM_JOB_ID:-none} flavor=$FLAVOR date=$(date -Is) nproc=$NP shards=$N"
echo "T21b job: gpu=$GPU cuda_home=$CUDA_HOME HEAD=$(git -C $W rev-parse --short HEAD) runtime_checkout=$(git -C $A rev-parse --short HEAD)"
echo "T21b job: runtime libsanalyzer=$HS ($LSA) collector=$HC fatbin=$HF late=$HL"
if [ "${HS:0:8}" != a01c1666 ] || [ "${HC:0:8}" != 83af1437 ] || [ "${HF:0:8}" != a2d7368b ]; then
  echo "T21b: RUNTIME HASH MISMATCH on $(hostname): want a01c1666/83af1437/a2d7368b" >&2; exit 99
fi
[ "$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)" = 1 ] || { echo "T21b: not exactly one GPU on $(hostname)" >&2; exit 98; }
nvidia-smi --query-gpu=compute_cap --format=csv,noheader | grep -qx '8\.9' || { echo "T21b: not an sm_89 GPU on $(hostname): $GPU" >&2; exit 98; }

TO=1200
case "$FLAVOR" in
  main)    S=$S0;          RES=$W/eval/results/realworld;          CONF=$W/eval/baselines/confirm_realworld ;;
  certain) S=$S0/certain;  RES=$W/eval/results/realworld/certain;  CONF=$W/eval/baselines/confirm_realworld/certain
           export BASELINE_MODES=vector-clock YOSEMITE_HB_GATE_POLICY=certain ;;
  vc5400)  S=$S0/vc5400;   RES=$W/eval/results/realworld/vc5400;   CONF=$W/eval/baselines/confirm_realworld/vc5400
           TO=5400; export BASELINE_MODES=vector-clock ;;
  proto)   S=${PROTO_STORE:-/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-proto}; RES=$S/results; CONF=$S/confirm ;;
  *) echo "bad FLAVOR $FLAVOR" >&2; exit 2 ;;
esac
export BASELINE_TRACE_DIR=$S BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 YOSEMITE_HB_SHARDS=$N
MANIFEST=${MANIFEST:-$W/eval/realworld/manifest_t21b.csv}
LOG=$W/eval/x_logs; mkdir -p $LOG $RES $CONF $S
for id in ${IDS:-}; do
  echo "=== $(date -Is) run $id flavor=$FLAVOR"
  $PY $W/eval/baselines/parallel.py run --manifest $MANIFEST --id $id --reps 1 --confirm \
      --timeout-floor $TO --timeout-cap $TO --analysis-timeout 3600 --tag "$id-" \
      --results-dir $RES --confirm-dir $CONF > $LOG/run-$FLAVOR-$id.out 2>&1
  echo "  parallel.py rc=$? ($(tail -1 $LOG/run-$FLAVOR-$id.out | cut -c1-120))"
  $PY $W/eval/realworld/harness/rw_postmeta.py --meta $S/$id/meta.json --flavor $FLAVOR --shards $N --nproc $NP \
      --libsanalyzer $HS --collector $HC --fatbin $HF --fatbin-late $HL --cuda-home $CUDA_HOME --gpu "$GPU" \
      --job "${SLURM_JOB_ID:-none}" --head "$(git -C $W rev-parse HEAD)" --policy "${YOSEMITE_HB_GATE_POLICY:-recorded}" \
      --timeout $TO 2>&1 | tail -2
  $PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S --manifest $MANIFEST \
      --out $RES/attrib/$id.json > $LOG/attrib-$FLAVOR-$id.out 2>&1
  echo "  attribute rc=$? ($(tail -1 $LOG/attrib-$FLAVOR-$id.out | cut -c1-200))"
  CP=$W/eval/x_logs/store_copy/$FLAVOR/$id; mkdir -p $CP; cp $S/$id/meta.json $CP/ 2>/dev/null; for f in $S/$id/logs/*.txt; do tail -c 30000 "$f" > $CP/$(basename $f); done 2>/dev/null
done
echo "=== $(date -Is) done"

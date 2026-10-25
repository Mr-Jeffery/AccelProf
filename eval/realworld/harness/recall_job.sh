#!/bin/bash
# T21c copy of T21b's script (study/realworld-recall): worktree wt-t21c, store realworld-2026-10-t21c, results eval/results/realworld_t21c, manifest_t21c.csv.
# T21b recall job: detector runs (both modes) of the given target-variant ids on the installed runtime,
# then kernel-aware attribution of every report. One id = one parallel.py run (both modes in it).
#   IDS="amrex-1-buggy amrex-1-fixed" [FLAVOR=main|certain|vc5400|proto] sbatch ... recall_job.sh
# FLAVOR main     both modes, store $S0, results eval/results/realworld_t21c, confirm eval/baselines/confirm_realworld_t21c
# FLAVOR certain  vector-clock only under YOSEMITE_HB_GATE_POLICY=certain ("Race (sound)"), store $S0/certain
# FLAVOR vc5400   vector-clock only, timeout 5,400 s (the second pass for the timeouts), store $S0/vc5400
# The whole job exits non-zero (97) when BeeGFS/home/the worktree is unreadable, 98 when the GPU is not a single
# sm_89 device, 99 when the installed runtime's hashes differ from f551ca0's (libsanalyzer 5a20fd14, collector
# b746b4dd, fatbin a2d7368b).
source /home/fzheng4/wt-t21c/eval/realworld/harness/recall_header.sh || exit $?
FLAVOR=${FLAVOR:-main}
export ACCEL_PROF_HOME=$A
export CUDA_HOME=${RW_CUDA_HOME:-/usr/local/cuda-13.3}
[ -d "$CUDA_HOME/bin" ] || { echo "T21b: host=$(hostname) $CUDA_HOME missing" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh          # keeps ACCEL_PROF_HOME and CUDA_HOME; sets PATH, LD_LIBRARY_PATH, PY
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
h16() { sha256sum "$1" | cut -c1-16; }
LSA=$(ldd $A/lib/libcompute_sanitizer.so | awk '/libsanalyzer.so/{print $3; exit}')
HS=$(h16 $LSA); HC=$(h16 $A/lib/libcompute_sanitizer.so); HF=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)
HL=$(h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)
GPU=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tr '\n' ';')
NP=$(nproc); if [ "$NP" -ge 64 ]; then N=32; else N=16; fi
echo "T21b job: host=$(hostname) job=${SLURM_JOB_ID:-none} flavor=$FLAVOR date=$(date -Is) nproc=$NP shards=$N"
echo "T21b job: gpu=$GPU cuda_home=$CUDA_HOME HEAD=$(git -C $W rev-parse --short HEAD) runtime_checkout=$(git -C $A rev-parse --short HEAD)"
echo "T21b job: runtime libsanalyzer=$HS ($LSA) collector=$HC fatbin=$HF late=$HL"
if [ "${HS:0:8}" != 5a20fd14 ] || [ "${HC:0:8}" != b746b4dd ] || [ "${HF:0:8}" != a2d7368b ]; then
  echo "T21b: RUNTIME HASH MISMATCH on $(hostname): want 5a20fd14/b746b4dd/a2d7368b" >&2; exit 99
fi
# exactly one sm_89 device; other devices (c26 also carries an RTX 2060, sm_75) are hidden with CUDA_VISIBLE_DEVICES
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}')
[ "$(echo "$IDX" | grep -c .)" = 1 ] || { echo "T21b: not exactly one sm_89 GPU on $(hostname): $GPU" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
GPU="$GPU used_index=$IDX"
echo "T21b job: CUDA_VISIBLE_DEVICES=$IDX"

TO=1200; ATO=3600; CMD=run
case "$FLAVOR" in
  main)    S=$S0;          RES=$W/eval/results/realworld_t21c;          CONF=$W/eval/baselines/confirm_realworld_t21c ;;
  main-sc) S=$S0;          RES=$W/eval/results/realworld_t21c;     CONF=$W/eval/baselines/confirm_realworld_t21c   # T21c (Jeffery 2026-10-25): scalar-clock only for now
           export BASELINE_MODES=scalar-clock ;;
  certain) S=$S0/certain;  RES=$W/eval/results/realworld_t21c/certain;  CONF=$W/eval/baselines/confirm_realworld_t21c/certain
           export BASELINE_MODES=vector-clock YOSEMITE_HB_GATE_POLICY=certain ;;
  vc5400)  S=$S0/vc5400;   RES=$W/eval/results/realworld_t21c/vc5400;   CONF=$W/eval/baselines/confirm_realworld_t21c/vc5400
           TO=5400; export BASELINE_MODES=vector-clock ;;
  longcap-vc) S=$S0/longcap-vc; RES=$W/eval/results/realworld_t21c/longcap-vc; CONF=$W/eval/baselines/confirm_realworld_t21c/longcap-vc
           TO=${LONG_TO:-84600}; ATO=${LONG_ATO:-84600}; CMD=collect; ATTR=run; export BASELINE_MODES=vector-clock ;;
  longcap-sc) S=$S0/longcap-sc; RES=$W/eval/results/realworld_t21c/longcap-sc; CONF=$W/eval/baselines/confirm_realworld_t21c/longcap-sc
           TO=${LONG_TO:-84600}; ATO=${LONG_ATO:-84600}; CMD=collect; ATTR=run; export BASELINE_MODES=scalar-clock ;;
  proto)   S=${PROTO_STORE:-/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-proto}; RES=$S/results; CONF=$S/confirm ;;
  *) echo "bad FLAVOR $FLAVOR" >&2; exit 2 ;;
esac
export BASELINE_TRACE_DIR=$S BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 YOSEMITE_HB_SHARDS=$N
MANIFEST=${MANIFEST:-$W/eval/realworld/manifest_t21c.csv}
LOG=$W/eval/x_logs; mkdir -p $LOG $RES $CONF $S
for id in ${IDS:-}; do
  echo "=== $(date -Is) run $id flavor=$FLAVOR"
  $PY $W/eval/baselines/parallel.py ${CMD:-run} --manifest $MANIFEST --id $id --reps 1 --confirm \
      --timeout-floor $TO --timeout-cap $TO --analysis-timeout $ATO --tag "$id-" \
      --results-dir $RES --confirm-dir $CONF > $LOG/run-$FLAVOR-$id.out 2>&1
  echo "  parallel.py rc=$? ($(tail -1 $LOG/run-$FLAVOR-$id.out | cut -c1-120))"
  if [ ! -s "$S/$id/meta.json" ] || ! timeout 60 ls "$S/$id" >/dev/null 2>&1; then echo "T21b: host=$(hostname) store unreadable after run of $id (BeeGFS lost during the run); result void" >&2; exit 97; fi
  $PY $W/eval/realworld/harness/rw_postmeta.py --meta $S/$id/meta.json --flavor $FLAVOR --shards $N --nproc $NP \
      --libsanalyzer $HS --collector $HC --fatbin $HF --fatbin-late $HL --cuda-home $CUDA_HOME --gpu "$GPU" \
      --job "${SLURM_JOB_ID:-none}" --head "$(git -C $W rev-parse HEAD)" --policy "${YOSEMITE_HB_GATE_POLICY:-recorded}" \
      --timeout $TO 2>&1 | tail -2
  [ "${ATTR:-both}" = run ] && continue   # attribution runs separately on a CPU node (recall_attr.sh)
  if ! $PY -c "import csv,sys; sys.exit(0 if any(r['verdict'] in ('RACE','CLEAN') for r in csv.DictReader(open('$RES/baselines-cuvein-shard$id-all.csv'))) else 1)" 2>/dev/null; then echo "  no mode of $id ended RACE or CLEAN: attribution skipped (not scoreable)"; continue; fi
  $PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S --manifest $MANIFEST \
      --out $RES/attrib/$id.json > $LOG/attrib-$FLAVOR-$id.out 2>&1
  echo "  attribute rc=$? ($(tail -1 $LOG/attrib-$FLAVOR-$id.out | cut -c1-200))"
  CP=$W/eval/x_logs/store_copy/$FLAVOR/$id; mkdir -p $CP; cp $S/$id/meta.json $CP/ 2>/dev/null; for f in $S/$id/logs/*.txt; do tail -c 30000 "$f" > $CP/$(basename $f); done 2>/dev/null
done
if [ "${ATTR:-both}" = run ] && [ -n "${IDS:-}" ]; then
  if [ "${CMD:-run}" = collect ]; then SC=recall_analyze.sh; TL=24:00:00; else SC=recall_attr.sh; TL=23:50:00; fi
  ( cd $W && sbatch --parsable --job-name="t21b-attr-${IDS%% *}" --partition=normal --nodes=1 --ntasks=1 --cpus-per-task=8 --time=$TL       --export=ALL,FLAVOR=$FLAVOR,IDS="$IDS",LONG_ATO=${LONG_ATO:-84600} --output=$W/eval/x_logs/t21b-attr-$FLAVOR-${IDS%% *}-%j.log eval/realworld/harness/$SC )
fi
echo "=== $(date -Is) done"

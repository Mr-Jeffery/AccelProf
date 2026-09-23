#!/usr/bin/env bash
#SBATCH --job-name=t1a-eval
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t1a-eval-%j.log
# T1a step 6 (eval/CP_ASYNC_REPORT.md): the P5 ScoR litmus + canary and the P6 cuHadron
# programs (minus asyncmemcpy / interkernel -- host/inter-kernel, T2 -- and the sm_90-only
# bulkcpy / dsmem) through parallel.py in both modes with the T1a runtime; every verdict
# that differs from the merged baseline rows is listed. Then the green set + test_cp_async.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_eval.sh
set -u
W=/home/fzheng4/wt-T1a
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16)"
TAG=t1a-p56
rm -rf /mnt/beegfs/$USER/cuvein_traces/$TAG $W/eval/results/$TAG $W/eval/baselines/confirm_$TAG
BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG $PY eval/baselines/parallel.py run \
    --manifest eval/baselines/manifest.csv --id-file eval/baselines/setup/t1a_eval_ids.txt \
    --reps 1 --confirm --tag $TAG --results-dir $W/eval/results/$TAG \
    --confirm-dir $W/eval/baselines/confirm_$TAG 2>&1 | tail -3
# load_runs skips *-shard* files (the merged per-shard CSVs): compare through a plain copy
mkdir -p $W/eval/results/$TAG/cmp
cp $W/eval/results/$TAG/baselines-cuvein-shard$TAG*.csv $W/eval/results/$TAG/cmp/baselines-cuvein.csv
$PY - <<'PY'
import csv, glob, sys
sys.path.insert(0, "eval/baselines")
import make_tables as mt
base, _ = mt.load_runs()
new, _ = mt.load_runs(["eval/results/t1a-p56/cmp/baselines-cuvein.csv"])
chg = 0
for (i, t, m), r in sorted(new.items()):
    b = base.get((i, t, m))
    bv = b["verdict"] if b else "-"
    if bv != r["verdict"] or (b and b["report_ids"] != r["report_ids"]):
        chg += 1
        print(f"CHANGED {i} {m}: {bv} ({b['reports'] if b else '-'}) -> {r['verdict']} ({r['reports']}) {r['report_ids'][:120]}"
              f"  [baseline: {b['report_ids'][:120] if b else '-'}]")
print(f"{len(new)} (id, mode) rows; {chg} differ from the merged baseline (verdict or report ids)")
PY
echo "== green set (T1a runtime) + test_cp_async.py"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py python/test_cp_async.py -rxXs -W ignore 2>&1 | tail -3
echo "== done $(date -Is)"

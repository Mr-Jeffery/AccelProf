#!/usr/bin/env bash
#SBATCH --job-name=t8-fresh
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-T8/eval/baselines/setup/t8_check/fresh-%j.log
# T8 acceptance: a fresh five-program run (T8 harness + T8 library through the worktree's
# private collector) must write only the new names -- CSV mode column, store dirs, logs,
# partial dumps, meta.json, STORE_INFO.json, confirm files.
cd /home/fzheng4/wt-T8 || exit 1
export ACCEL_PROF_HOME=/home/fzheng4/wt-T8
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
TAG=t8-fresh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
rm -rf "$BASELINE_TRACE_DIR" eval/results/$TAG eval/baselines/confirm_$TAG
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) APH=$ACCEL_PROF_HOME"
$PY eval/baselines/parallel.py run --manifest eval/baselines/setup/manifest.evcand.csv \
    --id P5-race_interblock_none-lock_rtraw,P5-norace_interblock_atom,P5-canary,P4-1dconv-norace-small,P4-graph-coloring-norace-large \
    --confirm --tag $TAG --reps 1 --results-dir eval/results/$TAG --confirm-dir eval/baselines/confirm_$TAG 2>&1 | tail -8
echo "== rows (id, mode, verdict, notes)"; cut -d, -f1,7,9,17 eval/results/$TAG/*.csv | cut -c1-150
echo "== store layout"; (cd $BASELINE_TRACE_DIR && find . -maxdepth 3 -not -name "kernel_*.json" -not -name "*.dot" | sort)
echo "== STORE_INFO modes"; $PY -c "import json; print(json.load(open('$BASELINE_TRACE_DIR/STORE_INFO.json'))['modes'])"
echo "== meta modes keys / partial_dump"; for m in $BASELINE_TRACE_DIR/*/meta.json; do $PY -c "import json,sys; m=json.load(open(sys.argv[1])); print(m['id'], list(m['modes']), [v.get('partial_dump') for v in m['modes'].values()])" $m; done
echo "== confirm files"; ls eval/baselines/confirm_$TAG
echo "== old names anywhere in the outputs (expect none):"
grep -rlE '"(engine|trace-only)"|/engine/|/trace-only/|engine_rep|trace-only_rep|__cuvein__(engine|trace-only)|,engine,|,trace-only,' eval/results/$TAG eval/baselines/confirm_$TAG $BASELINE_TRACE_DIR --include=*.csv --include=*.json --include=PARTIAL 2>/dev/null | head
find $BASELINE_TRACE_DIR eval/baselines/confirm_$TAG -name "*engine*" -o -name "*trace-only*" | head
echo "== done"

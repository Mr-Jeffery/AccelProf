#!/usr/bin/env bash
#SBATCH --job-name=t0-smoke
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/wt-T0/eval/baselines/setup/build_logs/t0-smoke-%j.log
# T0 smoke test of the storage changes in parallel.py on one GPU node: four small
# programs (P4-uts-norace-small times out in vector-clock mode -> exercises the
# <mode>-partial-rep<k>/ path; two reps -> the "largest partial wins" rule), into a
# throw-away BeeGFS store, then the meta/layout is printed.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t0_smoke.sh
#   second smoke (timed-out reps WITH a partial dump -> <mode>-partial-rep<k>/):
#   PIN8G=1 TAG=t0-smoke2 NOGREEN=1 IDS=P4-graph-coloring-norace-large,P4-uts-norace-large \
#       sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t0_smoke.sh
CV=${CV:-/home/fzheng4/wt-T0}
cd "$CV" || exit 1
source eval/baselines/gpu_env.sh
# dual-GPU rtx4060ti8g nodes: pin the sm_89 device (no-op elsewhere)
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
TAG=${TAG:-t0-smoke}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
rm -rf "$BASELINE_TRACE_DIR"
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) cv=$CV store=$BASELINE_TRACE_DIR"
$PY eval/baselines/parallel.py run --manifest eval/baselines/setup/manifest.evcand.csv \
    --id "${IDS:-P5-norace_interblock_atom,P5-race_interblock_none-lock_rtraw,P4-1dconv-norace-small,P4-uts-norace-small}" \
    --confirm --tag "$TAG" --reps "${REPS:-2}" \
    --results-dir "$CV/eval/results/$TAG" --confirm-dir "$CV/eval/baselines/confirm_$TAG"
echo "== layout"; find "$BASELINE_TRACE_DIR" -maxdepth 2 | sort
echo "== sizes"; du -sh "$BASELINE_TRACE_DIR"/*/ 2>/dev/null
echo "== rows"; cat "$CV/eval/results/$TAG"/*.csv
for m in "$BASELINE_TRACE_DIR"/*/meta.json; do
  echo "== $m"
  $PY -c '
import json, sys
m = json.load(open(sys.argv[1]))
print({k: m.get(k) for k in ("status", "started", "finished", "slurm_job", "store")})
for mode, v in m["modes"].items():
    print(" ", mode, {k: vv for k, vv in v.items() if k != "reps"}, [(r["rc"], r["timed_out"], r["nkernels"], r["dump_mb"]) for r in v["reps"]])
' "$m"
done
for p in "$BASELINE_TRACE_DIR"/*/*-partial-rep*/PARTIAL; do echo "== $p"; cat "$p"; echo; done
[ -n "${NOGREEN:-}" ] && { echo "== done (green set skipped)"; exit 0; }
echo "== green set (A4): the detector is untouched by T0, so before == after; run once on this node"
cd /home/fzheng4/AccelProf || exit 1
rm -rf ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py 2>&1 | tail -15
echo "== done"

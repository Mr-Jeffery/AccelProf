#!/usr/bin/env bash
#SBATCH --job-name=t3-crs
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=08:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t3-crs-%j.log
# T3 (eval/CRS_CUDA_TRIAGE.md): CPU re-score of the kept P9-crs-cuda trace (T0 store
# full-2026-09-22, both modes) with the checkout's detector, the per-kernel triage
# table, and the pc -> source-line map of the binary (nvdisasm --print-line-info).
W=${W:-/home/fzheng4/wt-T3}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
STORE=/mnt/beegfs/$USER/cuvein_traces/full-2026-09-22
ID=P9-crs-cuda
EV=$W/eval/baselines/setup/t3_crs
S=/mnt/beegfs/$USER/t3_crs            # scratch: extracted cubin
mkdir -p "$EV" "$S"
echo "host=$(hostname) cpus=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G date=$(date -Is)"
echo "HEAD $(git rev-parse --short HEAD) dirty-detector-files: $(git status --porcelain -- python sanalyzer | wc -l)"
nvdisasm --version | tail -1
echo "== store"
du -sh $STORE/$ID/*/ 2>/dev/null
ls -la $STORE/$ID/vector-clock | head -60
echo "== cubin + line info"
(cd "$S" && rm -f *.cubin && cuobjdump -xelf all "$W/eval/baselines/bin/P9/crs-cuda" && ls -la)
CUBIN=$(grep -l "gcrs_m_1_w_4_coding_dotprod" "$S"/*.cubin | head -1)
echo "cubin: $CUBIN"
nvdisasm --print-line-info --print-code "$CUBIN" > "$S/lineinfo.txt"
wc -l "$S/lineinfo.txt"; gzip -c "$S/lineinfo.txt" > "$EV/lineinfo.txt.gz"
T=$(date +%s); echo "== parallel.py analyze (current detector) -> eval/results/t3-crs/"
export BASELINE_TRACE_DIR=$STORE
$PY eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv \
    --id $ID --confirm --tag t3-crs \
    --results-dir "$W/eval/results/t3-crs" --confirm-dir "$W/eval/baselines/confirm_t3-crs" \
    2>&1
echo "analyze: $(( $(date +%s) - T )) s"; T=$(date +%s); echo "== triage"
$PY eval/baselines/setup/t3_crs_triage.py --store $STORE --id $ID \
    --lineinfo "$S/lineinfo.txt" --out "$EV" 2>&1
echo "triage: $(( $(date +%s) - T )) s"; echo "== eval/triage.py on the two detail JSONs"
$PY eval/triage.py "$EV/detail_vector-clock.json" "$EV/detail_scalar-clock.json" > "$EV/triage_py.txt" 2>&1
tail -8 "$EV/triage_py.txt"
echo "== done $(date -Is)"

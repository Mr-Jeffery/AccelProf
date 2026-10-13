#!/usr/bin/env bash
#SBATCH --job-name=t3b-crs
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --output=/home/fzheng4/wt-T3b/eval/baselines/setup/build_logs/t3b-crs-%j.log
# T3b step 4 (eval/CRS_CUDA_TRIAGE.md §"Fix"): record P9-crs-cuda afresh, both modes, with the
# T3b runtime (a kept dump has no exit records, so no re-score can reach CLEAN), into a new
# BeeGFS store; analyze with the worktree's detector; summarise per kernel.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t3b_crs.sh
set -u
W=/home/fzheng4/wt-T3b
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
TAG=t3b-crs
STORE=/mnt/beegfs/$USER/cuvein_traces/$TAG-2026-09-28
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -- python sanalyzer | wc -l) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) date=$(date -Is)"
rm -rf $STORE $W/eval/results/$TAG $W/eval/baselines/confirm_$TAG
T=$(date +%s)
BASELINE_TRACE_DIR=$STORE $PY eval/baselines/parallel.py run \
    --manifest eval/baselines/manifest.csv --id P9-crs-cuda --reps 1 --confirm \
    --timeout-floor 1200 --tag $TAG --results-dir $W/eval/results/$TAG \
    --confirm-dir $W/eval/baselines/confirm_$TAG 2>&1 | tail -5
echo "run+analyze: $(( $(date +%s) - T )) s"
cat $W/eval/results/$TAG/*.csv | cut -c1-400
du -sh $STORE/P9-crs-cuda/*/ 2>/dev/null
echo "== per kernel"
$PY eval/baselines/setup/t3b_crs_summary.py $STORE/P9-crs-cuda > $W/eval/baselines/setup/t3b_crs/summary.tsv 2>&1
grep "^#" $W/eval/baselines/setup/t3b_crs/summary.tsv
echo "== done $(date -Is)"

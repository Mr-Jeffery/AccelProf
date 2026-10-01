#!/usr/bin/env bash
#SBATCH --job-name=merge-crs
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/merge-crs-%j.log
# T3b+T9 merge check: record P9-crs-cuda afresh, both modes, with the runtime installed from
# the merged tree (live collector + build/sanalyzer/lib/libsanalyzer.so), into a new BeeGFS
# store; analyze with this checkout's detector; summarise per kernel (setup/t3b_crs.sh's recipe).
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/merge_crs.sh
set -u
A=/home/fzheng4/AccelProf
cd $A || exit 1
export ACCEL_PROF_HOME=$A
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
TAG=merge-crs
STORE=/mnt/beegfs/$USER/cuvein_traces/$TAG-2026-09-28
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -uno -- python sanalyzer | wc -l) collector $(sha256sum $A/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $A/build/sanalyzer/lib/libsanalyzer.so | cut -c1-16) date=$(date -Is)"
rm -rf $STORE $A/eval/results/$TAG $A/eval/baselines/confirm_$TAG
T=$(date +%s)
BASELINE_TRACE_DIR=$STORE $PY eval/baselines/parallel.py run \
    --manifest eval/baselines/manifest.csv --id P9-crs-cuda --reps 1 --confirm \
    --timeout-floor 1200 --tag $TAG --results-dir $A/eval/results/$TAG \
    --confirm-dir $A/eval/baselines/confirm_$TAG 2>&1 | tail -5
echo "run+analyze: $(( $(date +%s) - T )) s"
cat $A/eval/results/$TAG/*.csv | cut -c1-400
du -sh $STORE/P9-crs-cuda/*/ 2>/dev/null
echo "== per kernel"
mkdir -p $A/eval/baselines/setup/merge_crs
$PY eval/baselines/setup/t3b_crs_summary.py $STORE/P9-crs-cuda > $A/eval/baselines/setup/merge_crs/summary.tsv 2>&1
grep "^#" $A/eval/baselines/setup/merge_crs/summary.tsv
echo "== done $(date -Is)"

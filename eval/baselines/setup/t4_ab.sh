#!/usr/bin/env bash
#SBATCH --job-name=t4-ab
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/wt-T4/build_logs/t4-ab-%j.log
# T4: the cost of no-dump mode on ONE node, back to back -- the same programs recorded with the
# dump (BASELINE_HB_DUMP=1) and without (=0), both modes, one rep each, HB_STATS on; the kept
# dumps go to cuvein_traces/t4-ab-{dump,nodump}. Wall and peak RSS from the CSV rows.
#   W=/home/fzheng4/wt-T4 IDS=<id file> sbatch eval/baselines/setup/t4_ab.sh
set -u
W=${W:-/home/fzheng4/wt-T4}
IDS=${IDS:-eval/baselines/setup/t4_ab_ids.txt}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
export YOSEMITE_HB_STATS=1
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
TAGP=${TAGP:-t4-ab}     # result/store tag prefix (a second run on another build: TAGP=t4-ab2)
for dump in 1 0; do
  TAG=$TAGP-$([ $dump = 1 ] && echo dump || echo nodump)
  mkdir -p eval/results/$TAG eval/baselines/confirm_$TAG /mnt/beegfs/$USER/cuvein_traces/$TAG
  export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
  echo "== BASELINE_HB_DUMP=$dump -> $TAG $(date -Is)"
  BASELINE_HB_DUMP=$dump $PY eval/baselines/parallel.py run --id-file $IDS --reps 1 --confirm --keep-all \
      --timeout-floor 1200 --analysis-timeout 3600 --tag $TAG \
      --results-dir $W/eval/results/$TAG --confirm-dir $W/eval/baselines/confirm_$TAG 2>&1 | tail -8
done
for TAG in $TAGP-dump $TAGP-nodump; do
  echo "== $TAG"; cut -d, -f1,7,9,13,15 eval/results/$TAG/*.csv | /usr/bin/grep -v '^id,'
done
echo "== done $(date -Is)"

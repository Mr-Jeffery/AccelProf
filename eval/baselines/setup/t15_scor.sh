#!/usr/bin/env bash
#SBATCH --job-name=t15-scor
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# T15 (eval/LATE_SEQ.md) step 3: the three ScoR programs whose Race-alone verdict rests on
# a2_uncertain reports only (eval/A2_WINDOWS.md: P4-matrix-multiplication-norace-small,
# P4-rule-110-norace-{small,large}), re-recorded once in vector-clock mode with the worktree
# runtime under YOSEMITE_HB_LATE_SEQ = 0, atomic, timer. Stores
# /mnt/beegfs/$USER/cuvein_traces/t15-<variant>, rows eval/results/t15-late-seq/<variant>/.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t15-scor-%j.log \
#       eval/baselines/setup/t15_scor.sh
set -u
W=${W:?set W=<task worktree>}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l)"
echo "collector $(sha256sum lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
IDS=$W/eval/baselines/setup/t15_scor_ids.txt
export BASELINE_MODES=vector-clock
for v in ${VARIANTS:-off atomic timer}; do
  lv=$v; [ $v = off ] && lv=0
  echo "== YOSEMITE_HB_LATE_SEQ=$lv"
  R=$W/eval/results/t15-late-seq/$v; mkdir -p $R/confirm
  S=/mnt/beegfs/$USER/cuvein_traces/t15-$v; rm -rf $S
  YOSEMITE_HB_LATE_SEQ=$lv BASELINE_TRACE_DIR=$S \
    .env/bin/python eval/baselines/parallel.py run --id-file $IDS --reps 1 --tag t15-$v \
      --results-dir $R --confirm-dir $R/confirm --analysis-timeout 7200 2>&1 | tail -8
  for f in $S/*/vector-clock/kernel_*.json; do
    .env/bin/python -c "import json,sys; t=json.load(open(sys.argv[1])); print(sys.argv[1].split('/')[-3], sys.argv[1].split('/')[-1], 'late', t.get('hb_late_seq_key'), 'events', len(t['hb_events']), 'tv', t.get('tv_violation'))" $f
  done
done
echo "== done $(date -Is)"

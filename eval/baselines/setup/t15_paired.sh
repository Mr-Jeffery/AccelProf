#!/usr/bin/env bash
# T15: per-run (paired) hand-off inversions of t15_handoffs.sh's late-keyed runs, late order
# vs buffer order of the same trace. CPU only (BeeGFS: a compute node).
#   W=<worktree> srun -p normal -n 1 -c 2 --time=30 bash eval/baselines/setup/t15_paired.sh
set -u
W=${W:?set W=<task worktree>}; cd "$W" || exit 1
T=${OUT:-/mnt/beegfs/$USER/t15-late-seq/handoffs}
for cfg in 1x2 1x4 4x4; do
  DOTS=("$T/$cfg/build"/lock_contention_a2_extracted_cubins/*.dot)
  for v in atomic timer; do
    for r in 1 2 3 4 5; do
      L=$(ls "$T/$cfg/$v/rep$r"/kernel_*.json); B=$(ls "$T/$cfg/$v-buffer/rep$r"/kernel_*.json)
      l=$(.env/bin/python eval/baselines/a2_window_count.py handoffs --dots "${DOTS[@]}" -- $L | tail -1 | sed -E "s/.*'cross_thread': ([0-9]+), 'inverted': ([0-9]+).*/\2\/\1/")
      b=$(.env/bin/python eval/baselines/a2_window_count.py handoffs --dots "${DOTS[@]}" -- $B | tail -1 | sed -E "s/.*'cross_thread': ([0-9]+), 'inverted': ([0-9]+).*/\2\/\1/")
      echo -e "$cfg\t$v\trep$r\tlate $l\tbuffer $b"
    done
  done
done

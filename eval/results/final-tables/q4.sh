#!/bin/bash
B=/mnt/beegfs/fzheng4/cuvein_traces
python3 -I ~/wt-x3/eval/results/final-tables/hwm_changes.py \
  $B/final-2026-10-long/P9-atomicCAS-cuda/vector-clock-partial-rep2 \
  $B/final-2026-11-24h-vc/P9-atomicCAS-cuda/vector-clock

#!/bin/bash
B=/mnt/beegfs/fzheng4/cuvein_traces
D=~/wt-x3/eval/results/final-tables/hb_stats_dump.py
echo "=== X1 5,400 s store (final-2026-10-long) atomicCAS vector-clock-partial-rep2"
python3 -I $D $B/final-2026-10-long/P9-atomicCAS-cuda/vector-clock-partial-rep2 last 0 1000
echo "=== X1b 84,600 s vc store (final-2026-11-24h-vc) atomicCAS"
python3 -I $D $B/final-2026-11-24h-vc/P9-atomicCAS-cuda/vector-clock last 0 1000
echo "=== particlefilter X1 5,400 vc"
python3 -I $D $B/final-2026-10-long/P7-particlefilter-cuda/vector-clock 0 1 2
echo "=== particlefilter X1b 5,400 vc partial"
python3 -I $D $B/final-2026-11-long/P7-particlefilter-cuda/vector-clock-partial-rep1 0 1 2
ls $B/final-2026-11/P7-particlefilter-cuda $B/final-2026-11-24h-sc/P7-stencil1d-cuda $B/final-2026-11-24h-vc/P7-stencil1d-cuda 2>&1

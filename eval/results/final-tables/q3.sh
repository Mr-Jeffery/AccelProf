#!/bin/bash
B=/mnt/beegfs/fzheng4/cuvein_traces
D=~/wt-x3/eval/results/final-tables/hb_stats_dump.py
echo "=== stencil1d X1b 84,600 s scalar-clock partial kernel 0 and last readable"
python3 -I $D $B/final-2026-11-24h-sc/P7-stencil1d-cuda/scalar-clock-partial-rep1 0 433
echo "=== particlefilter X1b first pass scalar-clock kernel 0"
python3 -I $D $B/final-2026-11/P7-particlefilter-cuda/scalar-clock 0

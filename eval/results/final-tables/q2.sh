#!/bin/bash
B=/mnt/beegfs/fzheng4/cuvein_traces
S=~/wt-x3/eval/results/final-tables/hb_series.py
echo "=== atomicCAS X1 5,400 s store, vector-clock-partial-rep2"
python3 -I $S $B/final-2026-10-long/P9-atomicCAS-cuda/vector-clock-partial-rep2 1000
echo "=== atomicCAS X1b 84,600 s store, vector-clock"
python3 -I $S $B/final-2026-11-24h-vc/P9-atomicCAS-cuda/vector-clock 2000
echo "=== particlefilter X1b first pass scalar-clock (N=16)"
python3 -I $S $B/final-2026-11/P7-particlefilter-cuda/scalar-clock 1
echo "=== stencil1d X1b 84,600 s scalar-clock partial"
python3 -I $S $B/final-2026-11-24h-sc/P7-stencil1d-cuda/scalar-clock-partial-rep1 20
echo "=== stencil1d X1b 84,600 s vector-clock partial"
python3 -I $S $B/final-2026-11-24h-vc/P7-stencil1d-cuda/vector-clock-partial-rep1 5
echo "=== expdist X1b 84,600 s vc entry"
ls -la $B/final-2026-11-24h-vc/P9-expdist-cuda $B/final-2026-11-24h-vc/P9-expdist-cuda/logs
for f in $B/final-2026-11-24h-vc/P9-expdist-cuda/logs/vector-clock_rep1.txt; do echo "-- tail $f"; tail -c 1500 $f; done
echo "=== expdist X1 24 h vc entry (final-2026-10-24h-vc)"
ls $B/final-2026-10-24h-vc/P9-expdist-cuda
tail -c 1200 $B/final-2026-10-24h-vc/P9-expdist-cuda/logs/vector-clock_rep1.txt
echo "=== stencil1d X1b 1,200 s first-pass dirs"
ls $B/final-2026-11/P7-stencil1d-cuda

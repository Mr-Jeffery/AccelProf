#!/usr/bin/env bash
# X13 phase 2 (after x13_sweep_all.sh), run as one srun step of the GPU job; each line is one x13_sweep2.sh call.
W=${W:-/home/fzheng4/wt-shard-balance}; L=$W/eval/x_logs; J=${SLURM_JOB_ID:-340799}
MALLOC=1 MODE=collector-only bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-malloc-co-$J.log 2>&1
MALLOC=1 MODE=scalar-clock   bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-malloc-sc-$J.log 2>&1
EXTRA=1 MODE=collector-only  bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-extra-co-$J.log 2>&1
TIMING=1 WORKERS=16 MODE=collector-only bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-timing16-co-$J.log 2>&1
TIMING=1 WORKERS=1  MODE=collector-only bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-timing1-co-$J.log 2>&1
TIMING=1 WORKERS=16 MODE=scalar-clock ONLY="bfs__500K bfs__1M stencil1d__L10" bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-timing16-sc-$J.log 2>&1
TIMING=1 WORKERS=1  MODE=scalar-clock ONLY="bfs__500K bfs__1M" bash $W/eval/x13/x13_sweep2.sh > $L/x13-p2-timing1-sc-$J.log 2>&1
echo "== phase 2 done $(date -Is)" > $L/x13-p2-done-$J.log

W=/home/fzheng4/wt-shard-balance
MODE=collector-only bash $W/eval/x13/x13_sweep.sh > $W/eval/x_logs/x13-sweep-collector-only-340799.log 2>&1
MODE=scalar-clock ONLY="bfs__500K bfs__1M stencil1d__L10 stencil1d__L20" bash $W/eval/x13/x13_sweep.sh > $W/eval/x_logs/x13-sweep-scalar-clock-340799.log 2>&1

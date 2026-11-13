W=/home/fzheng4/wt-shard-balance
export IDS="P4-reduction-norace-large P4-matrix-multiplication-norace-small P5-canary P7-backprop-cuda P7-bfs-cuda"
for m in collector-only scalar-clock; do MODE=$m bash $W/eval/x13/x13_parity.sh > $W/eval/x_logs/x13-parity-$m-340799.log 2>&1; done

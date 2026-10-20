#!/bin/bash
# LOGIN node: run one phase of one target as a job step inside the held work allocation (never on the login node itself).
#   hrun.sh <jobid> <id> <phase> [variant]      -> eval/x_logs/<id>-<phase>.log   (foreground: waits)
#   HRUN_BG=1 hrun.sh ...                       -> in the background (nohup), prints the log path
J=$1; id=$2; phase=$3; v=${4:-}
WT=/home/fzheng4/wt-t21a; log=$WT/eval/x_logs/$id-$phase${v:+-$v}.log; mkdir -p "$WT/eval/x_logs"
cmd="srun --jobid=$J --overlap -N1 -n1 --cpus-per-task=${HRUN_CPUS:-16} bash $WT/eval/realworld/harness/rw.sh $id $phase $v"
if [ -n "${HRUN_BG:-}" ]; then nohup $cmd > "$log" 2>&1 & echo "bg -> $log"; else $cmd > "$log" 2>&1; echo "rc=$? -> $log"; tail -${HRUN_TAIL:-5} "$log"; fi

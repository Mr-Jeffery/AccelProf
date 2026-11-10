#!/bin/bash
# usage: ck11t_node.sh HOSTPID P id...   Runs ids P at a time; if HOSTPID (the Slurm task holding this node) exits, kill the rest.
HOSTPID=$1; P=$2; shift 2
D=/home/fzheng4/wt-x13/eval/baselines/per_kernel
S=/home/fzheng4/wt-x13/eval/results/per-kernel/ck11t_ssh
LOG=/home/fzheng4/wt-x13/eval/x_logs/x13
mkdir -p $S
echo "$(hostname) host_pid=$HOSTPID ids=$*" > $S/node-$(hostname).txt
printf "%s\n" "$@" | xargs -P $P -I{} bash -c "$D/ck11t_one.sh {} > $LOG/ck11t-ssh-{}.log 2>&1" &
XP=$!
while kill -0 $XP 2>/dev/null; do
  if ! kill -0 $HOSTPID 2>/dev/null; then
    echo "$(date -Is) host task gone; killing extras" >> $S/node-$(hostname).txt
    for id in "$@"; do [ -f $S/t$id.rc ] || echo $id >> $S/killed.txt; done
    pkill -TERM -P $XP; pkill -TERM -u fzheng4 -f "ck11t_one.sh"; sleep 5
    for id in "$@"; do pkill -TERM -u fzheng4 -f "ck11t/t$id.csv"; done
    kill $XP 2>/dev/null; exit 1
  fi
  sleep 30
done
echo "$(date -Is) all done" >> $S/node-$(hostname).txt

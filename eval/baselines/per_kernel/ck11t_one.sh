#!/bin/bash
# Run one ck11t shard outside sbatch (started over ssh on a node allocated to 332672).
ID=$1
W=/home/fzheng4/wt-x13
PY=/home/fzheng4/AccelProf/.env/bin/python
O=$W/eval/results/per-kernel/ck11t
S=$W/eval/results/per-kernel/ck11t_ssh
mkdir -p $O $S
for v in $(env | grep -E "^(CUVEIN|YOSEMITE)_" | cut -d= -f1); do unset $v; done
L=$(sed -n "$((ID+1))p" $W/eval/baselines/per_kernel/x11_tasks2.txt)
IFS="|" read MODE STORE PROG KJ <<< "$L"
echo "$L"; echo "host=$(hostname) start=$(date -Is)"
echo "X11-$PROG" > /tmp/x13_id_$ID.txt
export X13_ALL=1 X13_KJ=$KJ
if [ "$MODE" = collector-only ]; then
  export X13_CO_C6=1 ACCEL_PROF_HOME=/home/fzheng4/wt-x11-cochain CUVEIN_HOME=/home/fzheng4/wt-x11-cochain; CODE=/home/fzheng4/wt-x11-cochain
else
  export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W; CODE=$W
fi
$PY $W/eval/baselines/per_kernel/curace_kernels.py $CODE $MODE $O/t$ID.csv 0/1 /tmp/x13_id_$ID.txt $STORE
rc=$?; echo "end=$(date -Is) rc=$rc"; echo $rc > $S/t$ID.rc

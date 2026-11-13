#!/usr/bin/env bash
# X13 live check (informational; the gate is x13_parity.sh's same-stream replay): P7 bfs recorded live through the harness at N=16
# three times -- counter off twice, counter on once -- and compared with co_json_diff.py. The record order is the GPU's schedule,
# so two live runs of bfs may differ by themselves; the off-vs-off row is the control for the off-vs-on rows.
#   MODE=collector-only|scalar-clock srun --input=none --jobid=<job> --overlap -n1 -c16 bash eval/x13/x13_live_bfs.sh
set -u
export W=${W:-/home/fzheng4/wt-shard-balance} S=${S:-/home/fzheng4/stage-x13}
source $W/eval/x13/x13_env.sh
DIFF=$W/eval/baselines/setup/co_json_diff.py
MODE=${MODE:-collector-only}; id=P7-bfs-cuda
OUT=/mnt/beegfs/fzheng4/x13/live-bfs-$MODE; rm -rf $OUT; mkdir -p $OUT
[ "$MODE" = scalar-clock ] && export BASELINE_HB_DUMP=0 YOSEMITE_HB_SHARDS=16
echo "host=$(hostname) mode=$MODE $(date -Is)"
for cfg in off1 off2 on1; do
  extra=""; [ $cfg = on1 ] && extra="YOSEMITE_SHARD_STATS=1"
  env BASELINE_MODES=$MODE BASELINE_WORKERS=16 BASELINE_TRACE_DIR=$OUT/$cfg $extra \
     $PY $W/eval/baselines/parallel.py collect --id $id --reps 1 --timeout-floor 1200 --timeout-cap 1200 > $OUT/$cfg.log 2>&1
  echo "$cfg: $(ls $OUT/$cfg/$id/$MODE/kernel_*.json 2>/dev/null | wc -l) kernel files"
done
for pair in "off1 off2" "off1 on1" "off2 on1"; do set -- $pair
  $PY $DIFF $OUT/$1/$id/$MODE $OUT/$2/$id/$MODE --label "$id live $MODE: $1 vs $2" --quiet 2>&1 | cut -c1-260
done
echo "== done $(date -Is)"

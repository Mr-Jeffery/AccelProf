#!/bin/bash
# P6 cp.async pair: X1 dump, confirm file, meta, source location (read only)
ID=P6-memcpy-shared_writewrite_race-racy
V=/mnt/beegfs/fzheng4/cuvein_traces/final-2026-10-view/$ID
ls -la $V/ $V/vector-clock/ $V/dots/
PY=/home/fzheng4/AccelProf/.env/bin/python
for m in vector-clock scalar-clock; do
  for f in $V/$m/kernel_*.json; do
    echo "== $m $f"
    $PY -I -c "
import json,sys
t=json.load(open(sys.argv[1]))
print(t['kernel']['kernel_name'], t['kernel']['grid_dim'], t['kernel']['block_dim'])
print('races', t.get('hb_races'))
print('sync_only', t.get('hb_races_sync_only'))
print('sync_pass', t.get('hb_sync_pass'))
print('async', t.get('hb_async'), 'events', 'hb_events' in t, t.get('hb_events_count'))
for e in t['edges']:
    if not e.get('cold_miss'): print('edge', hex(e['ancient_pc']), '->', hex(e['current_pc']), e['dist'])
" $f
  done
done
for c in confirm_final confirm_final-long confirm_final-long-sc confirm_final-24h-vc confirm_final-24h-sc; do
  ls /home/fzheng4/AccelProf/eval/baselines/$c/ 2>/dev/null | grep -i "$ID" | while read x; do echo "-- $c/$x"; head -c 3000 /home/fzheng4/AccelProf/eval/baselines/$c/$x; echo; done
done
for s in final-certain final-certain-recorded t16-certain t16-certain-exits t1a-p56 t12-after evcand; do
  d=/mnt/beegfs/fzheng4/cuvein_traces/$s/$ID
  [ -d $d ] && echo "store $s dot=$(md5sum $d/dots/*.dot | cut -c1-12) events=$(grep -c '"hb_events": \[' $d/vector-clock/kernel_0.json 2>/dev/null)"
done
echo "X1 dot=$(md5sum $V/dots/*.dot | cut -c1-12)"
find -L /mnt/beegfs/fzheng4/home_archive/eval_baselines/corpora /home/fzheng4/AccelProf/cuHadron -maxdepth 6 -name "*shared_writewrite_race*" 2>/dev/null | head

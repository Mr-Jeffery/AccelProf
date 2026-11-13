#!/usr/bin/env bash
# X13 parity gate: the counter must change no output. For each id and mode, one stream is captured live at N=16 through the
# capture shim (new runtime, counter off), then replayed through the new library at N=16 with the counter off and on, once with
# the default inline thresholds and once with every drain threaded (YOSEMITE_PCDEP_INLINE_MAX=0, YOSEMITE_HB_SHARD_INLINE_MAX=0);
# setup/co_json_diff.py compares the kernel JSONs (0 differences required) and the shards files are summarised.
#   MODE=collector-only|scalar-clock IDS="P4-... P7-bfs-cuda" srun --jobid=<job> --overlap -n1 -c16 bash eval/x13/x13_parity.sh
set -u
export W=${W:-/home/fzheng4/wt-shard-balance} S=${S:-/home/fzheng4/stage-x13}
source $W/eval/baselines/setup/t26_parity/common.sh
MODE=${MODE:-collector-only}; CAP=${CAP:-1200}
IDS=${IDS:-"P4-reduction-norace-large P7-bfs-cuda"}
echo "host=$(hostname) job=${SLURM_JOB_ID:-} mode=$MODE ids=[$IDS] $(date -Is)"
mkcaph; runtime_line
OUT=/mnt/beegfs/$USER/x13/parity-$MODE; ROOT=/tmp/$USER-x13-parity-$MODE; rm -rf $OUT $ROOT; mkdir -p $OUT $ROOT
[ "$MODE" = scalar-clock ] && export BASELINE_HB_DUMP=0
hbenv() { [ "$MODE" = collector-only ] && return; echo "YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$MODE YOSEMITE_HB_DUMP=0 YOSEMITE_HB_SHARDS=16"; }
for id in $IDS; do
  echo "== $id $(date -Is)"
  capd=$ROOT/cap/$id; mkdir -p $capd
  extra=""; [ "$MODE" = scalar-clock ] && extra="YOSEMITE_HB_SHARDS=16"
  t0=$(date +%s)
  env ACCEL_PROF_HOME=$CAPH CUVEIN_HOME=$CAPH BASELINE_MODES=$MODE BASELINE_WORKERS=16 BASELINE_TRACE_DIR=$OUT/Bc \
      CAP_REAL_LIB=$LIB_NEW CAP_DIR=$capd $extra \
      $PY $W/eval/baselines/parallel.py collect --id $id --reps 1 --timeout-floor $CAP --timeout-cap $CAP > $ROOT/live-$id.log 2>&1
  $PY -c "import json,sys; m=json.load(open(sys.argv[1])); r=(m.get('modes',{}).get(sys.argv[2],{}).get('reps') or [{}])[0]; print('  live Bc (%d s): rc=%s timed_out=%s wall=%s kernels=%s workers=%s' % (int(sys.argv[3]), r.get('rc'), r.get('timed_out'), r.get('wall'), r.get('nkernels'), m.get('analyzer_workers')))" $OUT/Bc/$id/meta.json $MODE $(( $(date +%s) - t0 )) 2>&1 | tail -1
  sc=""
  if [ "$MODE" != collector-only ]; then
    sc=$ROOT/scope-$id.txt
    $PY $W/python/atomic_scope_sidecar.py $OUT/Bc/$id/dots/*.dot -o $sc > /dev/null 2>&1 || sc=""
  fi
  cap=$(ls -S $capd/cap.*.bin 2>/dev/null | head -1)
  [ -n "$cap" ] || { echo "  no capture"; continue; }
  echo "  capture $(stat -c %s $cap) bytes ($(ls $capd/cap.*.bin | wc -l) files)"
  base="$(hbenv) ${sc:+YOSEMITE_ATOMIC_SCOPE_FILE=$sc}"
  export REPLAY_ENV="$base";                                   replay $cap $ROOT/r/$id/off new 16
  export REPLAY_ENV="$base YOSEMITE_SHARD_STATS=1";            replay $cap $ROOT/r/$id/on new 16
  export REPLAY_ENV="$base YOSEMITE_HB_SHARD_INLINE_MAX=0";    replay $cap $ROOT/r/$id/off0 new 16 0
  export REPLAY_ENV="$base YOSEMITE_HB_SHARD_INLINE_MAX=0 YOSEMITE_SHARD_STATS=1"; replay $cap $ROOT/r/$id/on0 new 16 0
  for r in off on off0 on0; do echo "  replay $r: $(grep -h 'rc=' $ROOT/r/$id/$r/replay.err | tr '\n' ' ')"; done
  rd() { depdir $ROOT/r/$id/$1; }
  cmpk() { rm -f $ROOT/diff.json
           $PY $DIFF "$1" "$2" --label "$id $3" --quiet --json $ROOT/diff.json > $ROOT/diff.txt 2>&1; local rc=$?; cat $ROOT/diff.txt; echo "  rc=$rc"
           [ $rc -ne 0 ] && [ -f $ROOT/diff.json ] && { mkdir -p $OUT/diffs; cp $ROOT/diff.json "$OUT/diffs/$id.$(echo $3 | tr -c 'A-Za-z0-9' _).json"; }; }
  cmpk "$(rd off)" "$(rd on)" "counter off vs on, default inline"
  cmpk "$(rd off0)" "$(rd on0)" "counter off vs on, every drain threaded"
  # byte identity as such, file by file (kernel_N.json only)
  nd=0; nf=0
  for pair in "off on" "off0 on0"; do set -- $pair
    for f in $(rd $1)/kernel_*.json; do b=$(basename $f); nf=$((nf+1)); cmp -s $f $(rd $2)/$b || { nd=$((nd+1)); echo "  DIFFERS $1 vs $2: $b"; }; done; done
  echo "  byte comparison: $nf kernel files, $nd differ"
  for r in off on off0 on0; do echo "  $r: kernel files $(ls $(rd $r)/kernel_*.json | wc -l) shards_N.json $(ls $(rd $r)/shards_[0-9]*.json 2>/dev/null | wc -l) shards_sync_N.json $(ls $(rd $r)/shards_sync_*.json 2>/dev/null | wc -l)"; done
  $PY - $(rd on) $(rd on0) <<'EOP'
import glob, json, sys
for d in sys.argv[1:]:
    for pat, name in (("shards_[0-9]*.json", "pcdep"), ("shards_sync_*.json", "sync")):
        L = W = S = R = 0
        for f in glob.glob(f"{d}/{pat}"):
            j = json.load(open(f)); L += sum(j["lane_records"]); W += sum(j["warp_records"]); S += j["split_warp_records"]; R += j["warp_records_distinct"]
        print(f"  {d.split('/')[-2]} {name}: lane_records {L} warp_records {W} distinct {R} split {S}")
EOP
  mkdir -p $OUT/replay/$id; for r in off on off0 on0; do mkdir -p $OUT/replay/$id/$r; cp $(rd $r)/shards*.json $OUT/replay/$id/$r/ 2>/dev/null; done
  rm -rf $ROOT/r/$id $capd
done
echo "== done $(date -Is)"

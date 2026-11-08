#!/usr/bin/env bash
#SBATCH --job-name=t26-t20
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
# T26 step 4, the T20 parity ids (setup/t5b_parity_ids.txt) on one node, through the harness
# (parallel.py collect, --reps 1, cap = floor = $CAP s), mode $MODE:
#   collector-only (CFGS "I0 Ic A B Bc"): I0 installed -n 1; Ic installed -n 1 through the capture shim;
#     A new -n 1; B new -n 16; Bc new -n 16 through the shim.
#   scalar-clock / vector-clock (CFGS "Ic Bc"): X1b's settings (BASELINE_HB_DUMP=0, YOSEMITE_HB_SHARDS=16
#     in scalar-clock mode) for both; Ic installed -n 1, Bc new -n 16, both through the shim.
# Each captured stream is replayed (t26_replay) through the installed library at -n 1 and the new one at
# N = 16 (collector-only also N = 1 and N = 16 with every drain threaded) with the run's env (HB knobs,
# the program's atomic-scope sidecar rebuilt from its dots). co_json_diff.py then compares: replay
# fidelity (installed replay of Ic == Ic live), same-stream parity (new replays == installed replay;
# Bc live == installed replay of Bc's records), and live recordings against I0 (collector-only) or Ic.
# Note: `parallel.py collect` does not pass --timeout-floor on (its tool timeout is min(max(10 x native,
# 120), cap)); LIVE=direct records through live_one.py with the tool timeout = $CAP instead.
#   MODE=collector-only [IDS_FILE=.. | IDS="id ..."] [LIVE=direct] [SKIP="P7-particlefilter-cuda"] sbatch -o <W>/eval/x_logs/t26-t20-co-%j.log t20.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
source $W/eval/baselines/setup/t26_parity/common.sh
for d in $INST /mnt/beegfs/$USER; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
MODE=${MODE:-collector-only}; CAP=${CAP:-1200}
IDS_FILE=${IDS_FILE:-$W/eval/baselines/setup/t5b_parity_ids.txt}
SKIP=${SKIP:-P7-particlefilter-cuda}
if [ "$MODE" = collector-only ]; then CFGS=${CFGS:-I0 Ic A B Bc}; RLIBS=${RLIBS:-inst n1 n16 n16t}
else CFGS=${CFGS:-Ic Bc}; RLIBS=${RLIBS:-inst n16}; export BASELINE_HB_DUMP=0; fi
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G job=${SLURM_JOB_ID:-} mode=$MODE cfgs=[$CFGS] replays=[$RLIBS] cap=${CAP}s skip=[$SKIP] $(date -Is)"
mkcaph; runtime_line
TAG=t20-$MODE-${SLURM_JOB_ID:-x}
OUT=/mnt/beegfs/$USER/t26/$TAG; mkdir -p $OUT
ROOT=/tmp/$USER-t26-$TAG; mkdir -p $ROOT
echo "store=$OUT work=$ROOT ($(df -h /tmp | tail -1 | awk '{print $4}') free)"
hbenv() {   # the HB knobs of a run of this mode (empty in collector-only mode)
  [ "$MODE" = collector-only ] && return
  echo "YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$MODE YOSEMITE_HB_DUMP=0"
  [ "$MODE" = scalar-clock ] && echo "YOSEMITE_HB_SHARDS=16"
}
live() {    # live <id> <cfg>
  local id=$1 cfg=$2 home n real=""
  case $cfg in
    I0) home=$INST; n=1;; Ic) home=$CAPH; n=1; real=$LIB_INST;; A) home=$NEWH; n=1;;
    B) home=$NEWH; n=16;; Bc) home=$CAPH; n=16; real=$LIB_NEW;;
  esac
  local capd=$ROOT/cap/$cfg/$id; rm -rf $capd; mkdir -p $capd
  local extra=""; [ "$MODE" = scalar-clock ] && extra="YOSEMITE_HB_SHARDS=16"
  local t0=$(date +%s)
  env ACCEL_PROF_HOME=$home CUVEIN_HOME=$home BASELINE_MODES=$MODE BASELINE_WORKERS=$n \
      BASELINE_TRACE_DIR=$OUT/$cfg ${real:+CAP_REAL_LIB=$real CAP_DIR=$capd} $extra \
      $( [ "${LIVE:-}" = direct ] \
         && echo $PY $W/eval/baselines/setup/t26_parity/live_one.py --id $id --mode $MODE --workers $n --out $OUT/$cfg/$id --cap $CAP \
         || echo $PY $W/eval/baselines/parallel.py collect --id $id --reps 1 --timeout-floor $CAP --timeout-cap $CAP ) \
      > $ROOT/live-$cfg-$id.log 2>&1
  local st=$($PY -c "import json,sys; m=json.load(open(sys.argv[1])); r=(m.get('modes',{}).get(sys.argv[2],{}).get('reps') or [{}])[0]; print('rc=%s timed_out=%s wall=%s kernels=%s records=%s workers=%s' % (r.get('rc'), r.get('timed_out'), r.get('wall'), r.get('nkernels'), r.get('drained_records'), m.get('analyzer_workers')))" $OUT/$cfg/$id/meta.json $MODE 2>&1 | tail -1)
  echo "  live $cfg ($(( $(date +%s) - t0 )) s): $st"
}
nid=0
for id in ${IDS:-$(cat $IDS_FILE)}; do
  case " $SKIP " in *" $id "*) echo "== $id: skipped (SKIP)"; continue;; esac
  nid=$((nid + 1))
  echo "== $id $(date -Is)"
  for cfg in $CFGS; do live $id $cfg; done
  sc=""
  if [ "$MODE" != collector-only ]; then
    sc=$ROOT/scope-$id.txt
    $PY $W/python/atomic_scope_sidecar.py $OUT/Ic/$id/dots/*.dot -o $sc > /dev/null 2>&1 || sc=""
  fi
  for s in Ic Bc; do
    case " $CFGS " in *" $s "*) ;; *) continue;; esac
    cap=$(ls $ROOT/cap/$s/$id/cap.*.bin 2>/dev/null | head -1)
    ncap=$(ls $ROOT/cap/$s/$id/cap.*.bin 2>/dev/null | wc -l)
    [ -n "$cap" ] || { echo "  $s: no capture"; continue; }
    [ $ncap -gt 1 ] && echo "  $s: $ncap capture files (one process per file); replaying the largest"
    [ $ncap -gt 1 ] && cap=$(ls -S $ROOT/cap/$s/$id/cap.*.bin | head -1)
    echo "  $s capture $(stat -c %s $cap) bytes"
    export REPLAY_ENV="$(hbenv) ${sc:+YOSEMITE_ATOMIC_SCOPE_FILE=$sc}"
    for r in $RLIBS; do
      case $r in inst) replay $cap $ROOT/r/$id/$s-inst inst 1;; n1) replay $cap $ROOT/r/$id/$s-n1 new 1;;
                 n16) replay $cap $ROOT/r/$id/$s-n16 new 16;; n16t) replay $cap $ROOT/r/$id/$s-n16t new 16 0;; esac
      grep -h "t26_replay\]\|rc=" $ROOT/r/$id/$s-$r/replay.err | sed "s|$ROOT/cap/||" | tr '\n' ' ' | sed "s|^|  replay $s $r: |"; echo
    done
    rm -f $ROOT/cap/$s/$id/cap.*.bin
  done
  live_dir() { echo $OUT/$1/$id/$MODE; }
  cmpk() { rm -f $ROOT/diff.json
           $PY $DIFF "$1" "$2" --label "$id $3" --quiet --json $ROOT/diff.json > $ROOT/diff.txt 2>&1; local rc=$?; cat $ROOT/diff.txt
           [ $rc -ne 0 ] && [ -f $ROOT/diff.json ] && { mkdir -p $OUT/diffs; cp $ROOT/diff.json "$OUT/diffs/$id.$(echo $3 | tr -c 'A-Za-z0-9' _).json"; }; }
  rd() { depdir $ROOT/r/$id/$1; }
  if [ -n "$(rd Ic-inst)" ]; then
    cmpk "$(rd Ic-inst)" "$(live_dir Ic)" "fidelity: replay(Ic, installed -n1) vs Ic live"
  fi
  for s in Ic Bc; do
    [ -n "$(rd $s-inst)" ] || continue
    for r in $RLIBS; do [ $r = inst ] && continue
      cmpk "$(rd $s-inst)" "$(rd $s-$r)" "same-stream: $s installed -n1 vs new $r"; done
  done
  [ -n "$(rd Bc-inst)" ] && cmpk "$(rd Bc-inst)" "$(live_dir Bc)" "same-stream: Bc live (new N=16) vs installed -n1 on its records"
  if [ "$MODE" = collector-only ]; then
    cmpk "$(live_dir I0)" "$(live_dir A)" "live: I0 installed -n1 vs A new N=1"
    cmpk "$(live_dir I0)" "$(live_dir B)" "live: I0 installed -n1 vs B new N=16"
    cmpk "$(live_dir I0)" "$(live_dir Ic)" "live control: I0 installed -n1 vs Ic installed -n1"
  else
    cmpk "$(live_dir Ic)" "$(live_dir Bc)" "live: Ic installed -n1 vs Bc new N=16"
  fi
  # keep the replays' kernel JSONs next to the live ones
  for d in $ROOT/r/$id/*; do dp=$(depdir $d); [ -n "$dp" ] && { mkdir -p $OUT/replay/$id/$(basename $d); cp $dp/kernel_*.json $OUT/replay/$id/$(basename $d)/ 2>/dev/null; }; done
  rm -rf $ROOT/r/$id
done
echo "== $nid ids $(date -Is)"
rm -rf $ROOT
echo "== done $(date -Is)"

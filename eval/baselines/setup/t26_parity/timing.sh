#!/usr/bin/env bash
#SBATCH --job-name=t26-time
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
# REPLAY_BIN: the replay driver (default stage-t26/bin/t26_replay2, the unlocked-read build).
# T26, timing on identical streams (not an X12 measurement): the largest T20 parity ids recorded once in
# collector-only mode through the capture shim (installed library, -n 1), then each stream replayed
# REPS times through the installed library at -n 1 and -n 16 (ctaId % N partition, atomic shadow) and the
# new one at N = 1 and 16, same node, one replay at a time; wall seconds of the replay process (the
# PCDepGraph pass is the whole of it in this mode) and the new library's [PCDEP_STATS] lines.
#   [IDS="..."] [REPS=3] sbatch -o <W>/eval/x_logs/t26-time-%j.log timing.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
source $W/eval/baselines/setup/t26_parity/common.sh
export REPLAY_BIN=${REPLAY_BIN:-$S/bin/t26_replay2}
IDS=${IDS:-P6-interkernel-global_writewrite_race-racy P9-overlap-cuda P9-crs-cuda P7-bfs-cuda P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n P7-backprop-cuda}
REPS=${REPS:-3}
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} reps=$REPS $(date -Is)"
mkcaph; runtime_line
OUT=/mnt/beegfs/$USER/t26/time-${SLURM_JOB_ID:-x}; ROOT=/tmp/$USER-t26-time-${SLURM_JOB_ID:-x}; mkdir -p $OUT $ROOT
for id in $IDS; do
  echo "== $id"
  capd=$ROOT/cap/$id; mkdir -p $capd
  env ACCEL_PROF_HOME=$CAPH CUVEIN_HOME=$CAPH BASELINE_MODES=collector-only BASELINE_WORKERS=1 BASELINE_TRACE_DIR=$OUT \
      CAP_REAL_LIB=$LIB_INST CAP_DIR=$capd $PY $W/eval/baselines/parallel.py collect --id $id --reps 1 \
      --timeout-floor 1200 --timeout-cap 1200 > $ROOT/live-$id.log 2>&1
  cap=$(ls -S $capd/cap.*.bin 2>/dev/null | head -1)
  [ -n "$cap" ] || { echo "  no capture"; continue; }
  echo "  capture $(stat -c %s $cap) bytes"
  for cfg in inst1 inst16 new1 new16; do
    which=${cfg%%[0-9]*}; n=${cfg#$which}
    for rep in $(seq 1 $REPS); do
      d=$ROOT/r/$id/$cfg-$rep; rm -rf $d
      REPLAY_ENV="YOSEMITE_PCDEP_STATS=1" replay $cap $d $which $n
      s=$(sed -n 's/.*records, \([0-9.]*\) s.*/\1/p' $d/replay.err)
      lib=$(sed -n 's/.*\] library \(.*\)/\1/p' $d/replay.err)
      tot=$(grep -h 'PCDEP_STATS' $d/replay.err | sed 's/^[^{]*//' | $PY -c "import sys,json; r=[json.loads(l) for l in sys.stdin]; print('pass: drain_s %.3f route_s %.3f wait_s %.3f busy_max_sum %.3f kernels %d' % (sum(x['drain_s'] for x in r), sum(x['route_s'] for x in r), sum(x['wait_s'] for x in r), sum(max(x['busy_s']) for x in r), len(r)) if r else '')")
      echo "  $cfg rep $rep: replay ${s} s; library ${lib}; $tot"
    done
    $PY $DIFF "$(depdir $ROOT/r/$id/inst1-1)" "$(depdir $ROOT/r/$id/$cfg-1)" --label "  $id inst1 vs $cfg" --quiet
  done
  grep -h 'PCDEP_STATS' $ROOT/r/$id/new16-1/replay.err | awk '{print "  new16 " $0}' | cut -c1-400 | head -5
  rm -rf $ROOT/r/$id $capd
done
rm -rf $ROOT
echo "== done $(date -Is)"

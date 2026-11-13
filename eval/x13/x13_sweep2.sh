#!/usr/bin/env bash
# X13 follow-up runs (same driver as x13_sweep.sh), inside the GPU job:
#   EXTRA=1  more pathfinder sizes (R100, R200, and R1000 = the paper's input), counter on, N=16
#   TIMING=1 WORKERS=16|1  every size of the sweep with the counter OFF (YOSEMITE_SHARD_STATS unset) at N=WORKERS: wall and native
#            for the N=1 vs N=16 speed-up of the reduced inputs (the counter's own cost is in the counter-on walls)
#   MALLOC=1 bfs 1M with the cudaMalloc logging shim preloaded (names the allocation of the top segment)
#   MODE=collector-only|scalar-clock [ONLY="name ..."] srun --jobid=<job> --overlap -n1 -c16 bash eval/x13/x13_sweep2.sh
set -u
W=${W:-/home/fzheng4/wt-shard-balance}
source $W/eval/x13/x13_env.sh
MODE=${MODE:-collector-only}; CAPS=${CAPS:-7200}; WORKERS=${WORKERS:-16}
G=$HEC/data/bfs
declare -a RUNS=()
if [ -n "${EXTRA:-}" ]; then RUNS+=(
  "pathfinder__R100|$BIN/P7/pathfinder-cuda|100000 100 5"
  "pathfinder__R200|$BIN/P7/pathfinder-cuda|100000 200 5"
  "pathfinder__R1000|$BIN/P7/pathfinder-cuda|100000 1000 5"
); fi
if [ -n "${TIMING:-}" ]; then RUNS+=(
  "stencil1d__L10|$BIN/P7/stencil1d-cuda|134217728 10"
  "stencil1d__L20|$BIN/P7/stencil1d-cuda|134217728 20"
  "pathfinder__R10|$BIN/P7/pathfinder-cuda|100000 10 5"
  "pathfinder__R20|$BIN/P7/pathfinder-cuda|100000 20 5"
  "bfs__500K|$BIN/P7/bfs-cuda|$D/data/graph500KW_6.txt"
  "bfs__1M|$BIN/P7/bfs-cuda|$G/graph1MW_6.txt"
  "atomicCAS__r100|$BIN/P9/atomicCAS-cuda|100"
  "atomicCAS__r200|$BIN/P9/atomicCAS-cuda|200"
); fi
OPT=""; ROOT=$D/runs
[ -n "${TIMING:-}" ] && { OPT="--no-stats"; ROOT=$D/timing_n$WORKERS; }
if [ -n "${MALLOC:-}" ]; then RUNS=("bfs__1M|$BIN/P7/bfs-cuda|$G/graph1MW_6.txt"); OPT="--preload /home/fzheng4/stage-x13/bin/libx13malloc.so --no-native"; ROOT=$D/malloclog; fi
echo "host=$(hostname) job=${SLURM_JOB_ID:-} mode=$MODE workers=$WORKERS opt=[$OPT] root=$ROOT $(date -Is)"
echo "runtime HEAD=$(git -C $W rev-parse --short=12 HEAD) libsanalyzer=$(sha256sum $S/san-install/lib/libsanalyzer.so | cut -c1-16)"
mkdir -p $ROOT
for r in "${RUNS[@]}"; do
  IFS='|' read -r name exe args <<< "$r"
  [ -n "${ONLY:-}" ] && case " $ONLY " in *" $name "*) ;; *) continue;; esac
  echo "== $name [$MODE N=$WORKERS] $(date -Is): $(basename $exe) $args"
  $PY $X/x13_run.py --id X13-$name --exe $exe --args "$args" --mode $MODE --workers $WORKERS --cap $CAPS $OPT --out $ROOT/${name}__$MODE
done
echo "== done $(date -Is)"

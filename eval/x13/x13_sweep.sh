#!/usr/bin/env bash
# X13 runs: N=16, one rep per size, counter on (YOSEMITE_SHARD_STATS=1), through x13_run.py. Inside the GPU job:
#   MODE=collector-only|scalar-clock [ONLY="stencil1d__L10 ..."] srun --jobid=<job> --overlap -n1 -c16 bash eval/x13/x13_sweep.sh
# Paper command lines (eval/baselines/manifest.csv): stencil1d-cuda 134217728 1000 | pathfinder-cuda 100000 1000 5 |
#   bfs-cuda ../data/bfs/graph1MW_6.txt | atomicCAS-cuda 10000
set -u
W=${W:-/home/fzheng4/wt-shard-balance}
source $W/eval/x13/x13_env.sh
MODE=${MODE:-collector-only}; CAPS=${CAPS:-7200}
G=$HEC/data/bfs
declare -a RUNS=(
  "stencil1d__L10|$BIN/P7/stencil1d-cuda|134217728 10"
  "stencil1d__L20|$BIN/P7/stencil1d-cuda|134217728 20"
  "pathfinder__R10|$BIN/P7/pathfinder-cuda|100000 10 5"
  "pathfinder__R20|$BIN/P7/pathfinder-cuda|100000 20 5"
  "bfs__500K|$BIN/P7/bfs-cuda|$D/data/graph500KW_6.txt"
  "bfs__1M|$BIN/P7/bfs-cuda|$G/graph1MW_6.txt"
  "atomicCAS__r100|$BIN/P9/atomicCAS-cuda|100"
  "atomicCAS__r200|$BIN/P9/atomicCAS-cuda|200"
)
echo "host=$(hostname) job=${SLURM_JOB_ID:-} mode=$MODE $(date -Is)"
echo "runtime HEAD=$(git -C $W rev-parse --short=12 HEAD) libsanalyzer=$(sha256sum $S/san-install/lib/libsanalyzer.so | cut -c1-16)"
mkdir -p $D/runs
for r in "${RUNS[@]}"; do
  IFS='|' read -r name exe args <<< "$r"
  [ -n "${ONLY:-}" ] && case " $ONLY " in *" $name "*) ;; *) continue;; esac
  echo "== $name [$MODE] $(date -Is): $(basename $exe) $args"
  $PY $X/x13_run.py --id X13-$name --exe $exe --args "$args" --mode $MODE --workers 16 --cap $CAPS --out $D/runs/${name}__$MODE
done
echo "== done $(date -Is)"

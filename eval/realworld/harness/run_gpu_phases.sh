#!/bin/bash
# On the sm_89 node, inside the held GPU allocation:  run_gpu_phases.sh <id>...
# native (3 runs), reach (nsys kernel list), racecheck for each target, one log per target phase in eval/x_logs/.
#   srun --jobid=<gpu hold> --overlap -N1 -n1 bash eval/realworld/harness/run_gpu_phases.sh cccl-1 cccl-2 ... > eval/x_logs/gpu-batch.log 2>&1
HERE=$(cd "$(dirname "$0")" && pwd)
WT=$(dirname "$(dirname "$(dirname "$HERE")")")
for id in "$@"; do
  for ph in native reach racecheck; do
    echo "### $id $ph $(date +%T) host=$(hostname)"
    timeout "${PHASE_TIMEOUT:-3600}" "$HERE/rw.sh" "$id" "$ph" > "$WT/eval/x_logs/$id-$ph.log" 2>&1
    rc=$?
    echo "rc=$rc: $(grep -v '^T21 job' "$WT/eval/x_logs/$id-$ph.log" | tail -2 | cut -c1-200 | tr '\n' '|')"
  done
done

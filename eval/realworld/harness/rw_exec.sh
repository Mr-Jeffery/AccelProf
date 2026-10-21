#!/bin/bash
# T21b: run one ad-hoc command file (RWX=<path under the worktree>) on a GPU-partition node, with the BeeGFS checks.
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
echo "rw_exec: host=$(hostname) job=${SLURM_JOB_ID:-none} $(date -Is) running $RWX"
bash "$RWX"
echo "rw_exec: rc=$? $(date -Is)"

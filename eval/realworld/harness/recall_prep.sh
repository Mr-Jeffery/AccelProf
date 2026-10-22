#!/bin/bash
# T21b prep job: move the pre-T24 outputs aside (never scored), then verify the installed runtime's hashes.
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
D=/mnt/beegfs/fzheng4/realworld/pre-t24-discarded
mkdir -p $D || exit 1
echo "prep host=$(hostname) $(date -Is) HEAD=$(git -C $W rev-parse --short HEAD)"
mvx() { if [ -e "$1" ]; then echo "move $1 -> $D/$2"; mv "$1" "$D/$2" && echo "  ok" || echo "  FAILED"; else echo "absent $1"; fi; }
mvx $W/eval/results/realworld results_realworld
mvx $W/eval/baselines/confirm_realworld confirm_realworld
mvx $W/eval/x_logs/store_copy store_copy
mkdir -p $D/x_logs
for f in $W/eval/x_logs/attrib-main-* $W/eval/x_logs/attrib-certain-* $W/eval/x_logs/attrib-proto-* $W/eval/x_logs/run-main-* $W/eval/x_logs/run-certain-* $W/eval/x_logs/run-proto-* $W/eval/x_logs/t21b-main-* $W/eval/x_logs/t21b-certain-* $W/eval/x_logs/t21b-proto-*; do
  [ -e "$f" ] && mv "$f" $D/x_logs/
done
mvx /mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10 traces_realworld-2026-10
mvx /mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-proto traces_proto
echo "left in worktree:"; ls $W/eval/results/realworld 2>&1 | head -3; ls $W/eval/x_logs | grep -E '^(attrib|run)-|^t21b-(main|certain|proto)' | head
ls $D | head -20
echo "=== hash check"
IDS="" FLAVOR=main bash $W/eval/realworld/harness/recall_job.sh
echo "hashcheck rc=$?"

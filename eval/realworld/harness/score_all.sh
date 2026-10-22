#!/bin/bash
# T21b: tv scan (BeeGFS), score, queue, report on a CPU node
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
cd /home/fzheng4/wt-t21b || exit 1
python3 eval/realworld/harness/scan_tv.py eval/results/realworld/tv_violation.json || exit 2
python3 eval/realworld/harness/rw_score.py --write || exit 3
python3 eval/realworld/harness/rw_queue.py || exit 4
python3 eval/realworld/harness/rw_report.py || exit 5

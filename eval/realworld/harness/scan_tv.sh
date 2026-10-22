#!/bin/bash
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
python3 /home/fzheng4/wt-t21b/eval/realworld/harness/scan_tv.py /home/fzheng4/wt-t21b/eval/results/realworld/tv_violation.json

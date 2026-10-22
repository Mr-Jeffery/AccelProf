#!/bin/bash
L=/home/fzheng4/wt-t21b/eval/realworld/harness/recall_reattr.list
line=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" $L)
export FLAVOR=${line%% *}; export IDS=${line#* }
echo "reattr task $SLURM_ARRAY_TASK_ID: $line"
exec bash /home/fzheng4/wt-t21b/eval/realworld/harness/recall_attr.sh

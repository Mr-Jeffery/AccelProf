#!/bin/bash
# T21b: one array task = one line of recall_array.list: "FLAVOR target"; runs <target>-buggy and <target>-fixed.
L=/home/fzheng4/wt-t21b/eval/realworld/harness/recall_array.list
line=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" $L)
export FLAVOR=${line%% *}; t=${line#* }
export IDS="$t-buggy $t-fixed"
echo "array task $SLURM_ARRAY_TASK_ID: $line"
exec bash /home/fzheng4/wt-t21b/eval/realworld/harness/recall_job.sh

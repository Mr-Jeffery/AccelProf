#!/bin/bash
# T21b: run recall_job.sh; when the node cannot read BeeGFS/home (rc 97) or has no usable GPU (98), record the node in
# eval/x_logs/bad_nodes.txt and resubmit this job excluding every recorded node (at most 8 times). Env: FLAVOR, IDS, TRY.
TRY=${TRY:-0}
W=/home/fzheng4/wt-t21b
bash $W/eval/realworld/harness/recall_job.sh; rc=$?
if { [ $rc = 97 ] || [ $rc = 98 ]; } && [ "$TRY" -lt 8 ]; then
  echo "$(hostname)" >> $W/eval/x_logs/bad_nodes.txt
  EX=c2,c21,c22,c23,c34,c37,c46,c54,$(sort -u $W/eval/x_logs/bad_nodes.txt | tr '\n' ',' | sed 's/,$//')
  echo "T21b retry: rc=$rc on $(hostname); resubmitting excluding $EX (try $((TRY+1)))"
  cd $W
  sbatch --parsable --job-name="${SLURM_JOB_NAME}" --partition=rtx4060ti8g,rtx4060ti16g --exclude="$EX" --nodes=1 --ntasks=1 --cpus-per-task=16 --time=05:00:00 \
    --export=ALL,FLAVOR="$FLAVOR",IDS="$IDS",TRY=$((TRY+1)) --output=$W/eval/x_logs/t21b-retry-$FLAVOR-${IDS%% *}-%j.log eval/realworld/harness/recall_retry.sh
  exit 0
fi
exit $rc

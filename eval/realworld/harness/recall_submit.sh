#!/bin/bash
# T21c copy of T21b's script (study/realworld-recall): worktree wt-t21c, store realworld-2026-10-t21c, results eval/results/realworld_t21c, manifest_t21c.csv.
# T21b: submit one recall job per target (buggy and fixed, both modes) on the final runtime (f551ca0).
#   FLAVOR=main|certain|vc5400 [IDS_PER_JOB=...] recall_submit.sh <target> [<target> ...]
# Partitions: rtx4060ti8g first, then rtx4060ti16g; whole node; excluded nodes per CLAUDE.md T21.
W=/home/fzheng4/wt-t21c
FLAVOR=${FLAVOR:-main}
TL=${TL:-16:00:00}
for t in "$@"; do
  case "$t" in *-buggy|*-fixed) ids="$t" ;; *) ids="$t-buggy $t-fixed" ;; esac
  IDS="$ids" FLAVOR=$FLAVOR sbatch --parsable -p rtx4060ti8g,rtx4060ti16g -N 1 --exclusive -t $TL \
    --exclude=c23,c46,c2,c21,c37,c54 -J t21b-$FLAVOR-$t \
    -o $W/eval/x_logs/t21b-$FLAVOR-$t-%j.log --export=ALL,IDS="$ids",FLAVOR=$FLAVOR \
    $W/eval/realworld/harness/recall_job.sh | sed "s/^/$t $FLAVOR job /"
done

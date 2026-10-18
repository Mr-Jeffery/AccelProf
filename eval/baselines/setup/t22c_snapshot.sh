#!/usr/bin/env bash
# T22 cont.: before the 2026-10-18 18:00 cluster shutdown, record what a still-running step C/D run has
# written: its store's kernel JSONs' write times and aggregates (t22c_kstats.py) into
# eval/results/<tag>-<id>-n<N>/kstats-cut.txt, the snapshot time and the run's elapsed time, and (COPY=1)
# the kernel JSONs themselves (no dump: aggregates and hb_stats only) into .../cut-kernels/.
# Run on a node that mounts BeeGFS (inside the run's own allocation: srun --jobid=<id> --overlap).
#   t22c_snapshot.sh <tag>-<id>-n<N> <job start, epoch s> [COPY]
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
T=$1; START=$2; COPY=${3:-0}
S=/mnt/beegfs/$USER/cuvein_traces/$T
R=$W/eval/results/$T
mkdir -p $R
now=$(date +%s)
{
  echo "# snapshot $(date -Is) on $(hostname); job start $(date -d @$START -Is); elapsed $((now - START)) s"
  echo "# store $S: $(find $S -name 'kernel_*.json' | wc -l) kernel JSONs"
  $W/.env/bin/python $W/eval/baselines/setup/t22c_kstats.py $S
} > $R/kstats-cut.txt 2>&1
if [ "$COPY" = 1 ]; then
  mkdir -p $R/cut-kernels
  find $S -name 'kernel_*.json' -exec cp -p {} $R/cut-kernels/ \;
fi
head -2 $R/kstats-cut.txt; tail -2 $R/kstats-cut.txt

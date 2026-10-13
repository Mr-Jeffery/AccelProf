#!/usr/bin/env bash
#SBATCH --job-name=t17-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-T17/build_logs/t17-rescore-%j.log
# T17 acceptance: re-score one kept program per suite with the code before the rename (the
# main checkout, whose python/ and eval/baselines/*.py equal 7849a70's) and after it (this
# worktree), same store, same manifest; then compare the result CSVs and confirm JSONs.
# Pick per pset: the largest program under 20 MB whose store holds both modes' dumps.
# P1-P6 from the evcand store. P7/P9 (full-2026-09-22) have nothing under 20 MB with both modes:
# IDS="full-2026-09-22:P7:P7-particlefilter-cuda full-2026-09-22:P9:P9-crs-cuda" names them.
#   sbatch eval/baselines/setup/t17_rescore.sh
set -u
A=/home/fzheng4/AccelProf; W=/home/fzheng4/wt-T17
OUT=$W/build_logs/t17-rescore; [ -z "${IDS:-}" ] && rm -rf $OUT; mkdir -p $OUT
PY=$A/.env/bin/python
pick() {   # store pset -> id
  local d=/mnt/beegfs/fzheng4/cuvein_traces/$1
  for i in $(ls $d | grep "^$2-"); do
    ls $d/$i/vector-clock/kernel_*.json >/dev/null 2>&1 || continue
    ls $d/$i/scalar-clock/kernel_*.json >/dev/null 2>&1 || continue
    s=$(du -sb $d/$i/vector-clock $d/$i/scalar-clock | awk '{t+=$1} END {print t}')
    [ "$s" -lt 20000000 ] && echo "$s $i"
  done | sort -n | tail -1 | awk '{print $2}'
}
for spec in ${IDS:-evcand:P1 evcand:P2 evcand:P3 evcand:P4 evcand:P5 evcand:P6 full-2026-09-22:P7 full-2026-09-22:P9}; do
  IFS=: read -r tag ps id <<< "$spec"
  [ -z "$id" ] && id=$(pick $tag $ps); echo "$ps $tag $id"
  [ -z "$id" ] && continue
  for side in before:$A after:$W; do
    s=${side%%:*}; cv=${side#*:}
    ( cd $cv && BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$tag \
        BASELINE_MODES=vector-clock,scalar-clock \
        $PY eval/baselines/parallel.py analyze --manifest eval/baselines/setup/manifest.evcand.csv \
        --id $id --confirm --analysis-timeout 20000 \
        --results-dir $OUT/$s/$ps --confirm-dir $OUT/$s/$ps/confirm > $OUT/$s-$ps.log 2>&1 )
    echo "  $s rc=$?"
  done
done
echo "== compare"
for ps in P1 P2 P3 P4 P5 P6 P7 P9; do
  [ -d $OUT/before/$ps ] || continue
  if diff -r $OUT/before/$ps $OUT/after/$ps > $OUT/diff-$ps.txt; then echo "$ps identical: $(cd $OUT/before/$ps && find . -type f | sort | tr '\n' ' ')"
  else echo "$ps DIFFERS ($(wc -l < $OUT/diff-$ps.txt) diff lines)"; fi
done

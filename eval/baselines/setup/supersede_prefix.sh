#!/usr/bin/env bash
# Move (never delete) every cuVein-derived result of the pre-fix revision (fe694b5 +
# lib of 2026-09-10) out of the paths the merge/table scripts glob, so a re-run on a
# new detector revision cannot mix revisions: parallel.py merge concatenates every
# baselines-cuvein-shard*.csv and make_tables.load_runs collapses reps per
# (id, tool, mode) with RACE-wins. Other tools' CSVs stay (their tools did not change).
# Idempotent: re-running with nothing to move is a no-op.
set -u
cd /home/fzheng4/AccelProf || exit 1
DST=eval/results/prefix_fe694b5
B=eval/baselines
mkdir -p "$DST"
n=0
for f in eval/results/baselines-cuvein.csv eval/results/baselines-cuvein-shard*.csv \
         eval/results/baselines-diagnose.csv eval/results/baselines-disagreements.csv \
         eval/results/baselines-fp-causes.csv; do
  [ -e "$f" ] || continue
  mv -n "$f" "$DST/" && n=$((n+1))
done
for d in confirm traces_keep; do
  [ -d "$B/$d" ] && [ ! -e "$B/$d.prefix_fe694b5" ] && mv "$B/$d" "$B/$d.prefix_fe694b5" && n=$((n+1))
done
for l in keep_ids.txt keep_all_ids.txt residual_ids.txt engine_timeout_ids.txt; do
  [ -e "$B/setup/$l" ] && mv -n "$B/setup/$l" "$DST/$l" && n=$((n+1))
done
# diag/p7fix logs feed classify_residuals' "Killed" scan -> keep the old ones apart
mkdir -p "$B/setup/build_logs/prefix_fe694b5"
for lg in "$B"/setup/build_logs/diag-*.log "$B"/setup/build_logs/p7fix*.log; do
  [ -e "$lg" ] && mv -n "$lg" "$B/setup/build_logs/prefix_fe694b5/" && n=$((n+1))
done
echo "superseded: $n items -> $DST (shards: $(ls $DST/baselines-cuvein-shard*.csv 2>/dev/null | wc -l))"

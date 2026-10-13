#!/usr/bin/env bash
# Move (never delete) the cuVein rows of the 2026-09-18 revision (fe694b5 + working-tree
# diff sha 36a93d0849043935) out of the globbed paths before the re-run on the
# 2026-09-20 revision (python/sync_dominance.py edited 2026-09-20 21:25: event-stream
# candidates + past-release gate). The PI rows (baselines-cuvein-shardpi*.csv, their
# confirm files and kept traces) STAY: every PI shard started after 2026-09-20 22:19,
# i.e. already on the new revision. Idempotent.
set -u
cd /home/fzheng4/AccelProf || exit 1
TAG=prefix_36a93d08
DST=eval/results/$TAG
B=eval/baselines
mkdir -p "$DST" "$B/confirm.$TAG" "$B/traces_keep.$TAG" "$B/setup/build_logs/$TAG"
n=0
for f in eval/results/baselines-cuvein.csv eval/results/baselines-cuvein-shard*.csv \
         eval/results/baselines-diagnose.csv eval/results/baselines-disagreements.csv \
         eval/results/baselines-fp-causes.csv; do
  [ -e "$f" ] || continue
  case "$f" in *shardpi[0-9]*) continue;; esac
  mv -n "$f" "$DST/" && n=$((n+1))
done
for d in confirm traces_keep; do
  for e in "$B/$d"/*; do
    [ -e "$e" ] || continue
    case "$(basename "$e")" in PI-*) continue;; esac
    mv -n "$e" "$B/$d.$TAG/" && n=$((n+1))
  done
done
for l in keep_ids.txt keep_all_ids.txt residual_ids.txt engine_timeout_ids.txt; do
  [ -e "$B/setup/$l" ] && mv -n "$B/setup/$l" "$DST/$l" && n=$((n+1))
done
for lg in "$B"/setup/build_logs/diag-*.log; do
  [ -e "$lg" ] && mv -n "$lg" "$B/setup/build_logs/$TAG/" && n=$((n+1))
done
echo "superseded: $n items -> $DST (shards: $(ls $DST/baselines-cuvein-shard*.csv 2>/dev/null | wc -l); PI shards kept: $(ls eval/results/baselines-cuvein-shardpi*.csv | wc -l))"

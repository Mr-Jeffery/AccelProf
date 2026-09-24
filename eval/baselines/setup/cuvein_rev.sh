#!/usr/bin/env bash
# Pin the cuVein revision a re-run is about to use. Records (never modifies) the
# detector state: HEAD, modified detector files + mtimes, sha256 of the working-tree
# diff (saved in full under setup/cuvein_rev/), sha256 + mtime of the engine libs, and
# the knob defaults in effect. Exits 3 if the engine library is older than any
# sanalyzer/ source (the harness never rebuilds the detector; the blocker names the
# command). Usage: bash cuvein_rev.sh [label]   -> setup/cuvein_rev.status
cd /home/fzheng4/AccelProf || exit 1
HERE=eval/baselines/setup
LABEL="${1:-working-tree-$(date +%F)}"
OUT="$HERE/cuvein_rev.status"
mkdir -p "$HERE/cuvein_rev"
DIFF="$HERE/cuvein_rev/$LABEL.diff"
git diff HEAD -- python sanalyzer bin > "$DIFF"
DSHA=$(sha256sum "$DIFF" | cut -c1-16)
{
  echo "label: $LABEL"
  echo "recorded: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD) ($(git rev-parse --abbrev-ref HEAD))"
  echo "working-tree diff (python/ sanalyzer/ bin/): $(wc -l < "$DIFF") lines, sha256[:16]=$DSHA -> $DIFF"
  echo "modified detector files:"
  git diff --name-only HEAD -- python sanalyzer bin | while read -r f; do
    printf "  %s  %s\n" "$(stat -c %y "$f" | cut -c1-19)" "$f"
  done
  echo "engine libs:"
  for so in build/sanalyzer/lib/libsanalyzer.so lib/libcompute_sanitizer.so; do
    printf "  %s  sha256[:16]=%s  %s\n" "$(stat -c %y "$so" | cut -c1-19)" "$(sha256sum "$so" | cut -c1-16)" "$so"
  done
  echo "knobs: CUVEIN_STRONG_LDST=${CUVEIN_STRONG_LDST:-<unset: generic>} CUVEIN_BARRIER_PASS=${CUVEIN_BARRIER_PASS:-<unset: on>} BASELINE_MODES=${BASELINE_MODES:-<unset: vector-clock,scalar-clock>}"
} > "$OUT"
# freshness: libsanalyzer.so must postdate every sanalyzer source
SO=build/sanalyzer/lib/libsanalyzer.so
STALE=$(find sanalyzer -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.cu' \) -newer "$SO" | head -5)
if [ -n "$STALE" ]; then
  {
    echo "BLOCKED: engine sources newer than $SO:"; echo "$STALE"
    echo "next: cmake --build build/sanalyzer -j8   (detector rebuild is outside this harness)"
  } >> "$OUT"
  cat "$OUT"; exit 3
fi
echo "OK: engine lib newer than every sanalyzer/ source" >> "$OUT"
cat "$OUT"

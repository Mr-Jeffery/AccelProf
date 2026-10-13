#!/bin/bash
# Steps 3-4: value test and A2 in vivo. Every run in a clean environment.
# usage: run_values.sh [REPS]   (REPS runs of each lock configuration)
source "$(dirname "$0")/env.sh"
REPS=${1:-5}
APP=$WORK/atom_values
SO=$SPIKE/atom_after/atom_after.so
OUT=$WORK/values; mkdir -p "$OUT"
PY=/home/fzheng4/AccelProf/.env/bin/python
for at in after next; do
  for part in 1 2 4; do
    f=$OUT/p${part}_$at
    ATOM_VALUE_AT=$at ATOM_AFTER_OUT=$f.rec LD_PRELOAD=$SO "$APP" $part > $f.out 2>&1
    echo "part$part value_at=$at rc=$? app: $(grep '^part' $f.out)"
    $PY "$SPIKE/analyze_atom.py" $part $f.rec | tee $f.json
  done
  # lock idiom: 2, 4, 16 contending warps
  for cfg in "1 2" "1 4" "4 4"; do
    set -- $cfg
    for r in $(seq 1 $REPS); do
      f=$OUT/p3_${1}x${2}_${at}_r$r
      ATOM_VALUE_AT=$at ATOM_AFTER_OUT=$f.rec LD_PRELOAD=$SO "$APP" 3 $1 $2 16 > $f.out 2>&1
      echo "part3 B=$1 W=$2 rep=$r value_at=$at rc=$? app: $(grep '^part' $f.out)"
      $PY "$SPIKE/analyze_atom.py" 3 $f.rec $f.out > $f.json; cat $f.json
    done
  done
done

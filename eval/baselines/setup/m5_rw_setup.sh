#!/usr/bin/env bash
# M5: the real-world attribution harness of C6 (copy of /home/fzheng4/c6rw = C6's c6_rw_setup.sh output: study/realworld-recall and
# study/realworld-candidates harnesses with RW_MODES from C4 and the chain_closure=True / chain_src edits), with ONE more edit:
#   sd.analyze(dot, kj, chain_closure=True) -> sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3="off")   (S2)
# The chain-atomic-hop switch is read from $CUVEIN_CHAIN_ATOMIC_HOP by sync_dominance (python/ of $ACCEL_PROF_HOME).
set -eu
SRC=/home/fzheng4/c6rw; DST=/home/fzheng4/m5rw
[ -d $DST ] || cp -a $SRC $DST
for s in t21b t21c; do
  f=$DST/$s/eval/realworld/harness/rw_attribute.py
  sed -i 's/rep = sd.analyze(dot, kj, chain_closure=True)$/rep = sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3="off")/' $f
  grep -c "co_async=True" $f
done

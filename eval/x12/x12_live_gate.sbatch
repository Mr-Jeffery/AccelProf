#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# X12 G2 (T26's live_gate.py): every kept rep of the sharded recording against X11's three -n 1 recordings, per gated program;
# and the Indigo3 ids C1 recorded at least twice (main, parity-a, parity-b) against the N=16 reps. W=<harness worktree>
W=${W:?}; G=$W/eval/baselines/setup/t26_parity/live_gate.py; PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces; S=$B/final-2026-11-co-sh; OUT=$W/eval/results/co-sharded/parity; mkdir -p $OUT
echo "host=$(hostname) $(date -Is)"
for a in crs dxtc2 fpc gpp knn mr overlap tridiagonal; do
  $PY -I $G --label $a --base $B/x11-co-r1-$a/X11-$a/collector-only $B/x11-co-r2-$a/X11-$a/collector-only $B/x11-co-r3-$a/X11-$a/collector-only \
      --new $S/X11-$a/collector-only-rep1 $S/X11-$a/collector-only-rep2 $S/X11-$a/collector-only-rep3 --json $OUT/live_gate-$a.json
  echo "LIVE-GATE $a rc=$?"
done
echo "=== Indigo3 (P1) ids with 3 C1 -n 1 recordings"
P=$B/final-2026-11-co-sh-p1
for i in $(ls $B/final-2026-11-co-parity-a | grep '^P1-'); do
  [ -d $B/final-2026-11-co-parity-b/$i ] || continue
  $PY -I $G --label $i --base $B/final-2026-11-co/$i/collector-only $B/final-2026-11-co-parity-a/$i/collector-only $B/final-2026-11-co-parity-b/$i/collector-only \
      --new $P/$i/collector-only-rep1 $P/$i/collector-only-rep2 $P/$i/collector-only-rep3 --json $OUT/live_gate-p1-$(echo $i | md5sum | cut -c1-8).json
  echo "LIVE-GATE-P1 $i rc=$?"
done
echo "== done $(date -Is)"

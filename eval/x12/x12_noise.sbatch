#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# noise floor vs sharded: X12 Indigo3 ids that C1 recorded twice (parity-a/-b) + the HeCBench programs against X11. W=<harness>
B=/mnt/beegfs/fzheng4/cuvein_traces; W=${W:?}; PY="/home/fzheng4/AccelProf/.env/bin/python -I $W/eval/x12/x12_noise.py"
N=$B/final-2026-11-co-sh-p1
for i in $(ls $B/final-2026-11-co-parity-a | grep '^P1-' | head -20); do
  [ -d $B/final-2026-11-co-parity-b/$i ] || continue
  echo "== $i"
  $PY "C1 parity-a vs parity-b (-n 1 vs -n 1)" $B/final-2026-11-co-parity-a/$i/collector-only $B/final-2026-11-co-parity-b/$i/collector-only
  $PY "N16 rep1 vs C1 main (-n 1)" $N/$i/collector-only-rep1 $B/final-2026-11-co/$i/collector-only
  $PY "N16 rep1 vs N16 rep2" $N/$i/collector-only-rep1 $N/$i/collector-only-rep2
  $PY "C1 main vs C1 parity-a (-n 1 vs -n 1)" $B/final-2026-11-co/$i/collector-only $B/final-2026-11-co-parity-a/$i/collector-only
done
echo "=== HeCBench, X11 vs sharded"
for a in crs dxtc2 fpc gpp mr overlap; do
  b() { echo $B/x11-co-r$1-$a/X11-$a/collector-only; }
  echo "== $a"
  $PY "X11 r1 vs r2 (-n 1 vs -n 1)" $(b 1) $(b 2)
  $PY "N16 rep1 vs X11 r1" $B/final-2026-11-co-sh/X11-$a/collector-only-rep1 $(b 1)
  $PY "N16 rep1 vs N16 rep2" $B/final-2026-11-co-sh/X11-$a/collector-only-rep1 $B/final-2026-11-co-sh/X11-$a/collector-only-rep2
done

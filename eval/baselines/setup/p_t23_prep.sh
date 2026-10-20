#!/usr/bin/env bash
#SBATCH --job-name=t23-prep
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-prep-%j.log
# T23 step 1 prep (BeeGFS is mounted on compute nodes only): fetch the CFG dot + atomic-scope
# sidecar of X4's c58 scalar-clock/recorded cfg dirs into python/testdata/r3_closure, list the
# BeeGFS layout of the stores the re-score will read, and copy ScoR (5.7 MB) into the worktree so
# the green set reads a private copy of the artifacts.
set -u
W=/home/fzheng4/wt-t23
B=/mnt/beegfs/fzheng4/cuvein_traces
echo "host=$(hostname) date=$(date -Is)"
for lab in scor-scalar-clock scor-recorded; do
  echo "== $B/final-rtraw/$lab/c58/cfg"
  ls -la $B/final-rtraw/$lab/c58/cfg
done
echo "== dots under scor-scalar-clock/c58/cfg"
find $B/final-rtraw/scor-scalar-clock/c58/cfg -name '*.dot' | head
echo "== sha256 of the dot(s) of both labels"
find $B/final-rtraw/scor-scalar-clock/c58/cfg $B/final-rtraw/scor-recorded/c58/cfg -name '*.dot' -exec sha256sum {} +
echo "== stores"
for t in t20-parity2 final-certain final-certain-recorded final-rtraw final-2026-10 final-2026-10-long final-2026-10-long-sc final-2026-10-24h-vc final-2026-10-24h-sc; do
  if [ -d $B/$t ]; then echo "$t: $(ls $B/$t | wc -l) entries; first: $(ls $B/$t | head -3 | tr '\n' ' ')"; else echo "$t: MISSING"; fi
done
echo "== one program of final-2026-10"
P=$(ls $B/final-2026-10 | head -1); ls -la $B/final-2026-10/$P; ls $B/final-2026-10/$P/* | head -20
cp -r /home/fzheng4/AccelProf/ScoR $W/ScoR && echo "ScoR copied: $(du -sh $W/ScoR | cut -f1)"

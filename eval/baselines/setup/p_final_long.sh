#!/usr/bin/env bash
#SBATCH --job-name=x1-final-long
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c[0-3],c[23-24],c37,c[50-58],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/final-long-%A_%a.log
# X1 second pass (eval/FINAL_SWEEP.md): vector-clock mode only, the cap 5,400 s (--timeout-floor =
# --timeout-cap = 5400, as p_final.sh does at 1,200 s), over the ids whose vector-clock rows of the
# first pass are TIMEOUT in P1, P3, P4, P6, P7, P9 (never PI) -- setup/final_long_ids.txt, written
# by setup/final_long_ids.py from eval/results/final/. Everything else is p_final.sh's
# configuration (BASELINE_HB_DUMP=0, YOSEMITE_HB_STATS=1, --reps 3, --confirm, --keep-all).
# Its own store /mnt/beegfs/$USER/cuvein_traces/final-2026-10-long: collect_one wipes <store>/<id>,
# so recording into final-2026-10 would delete the first pass's scalar-clock dumps of these ids.
# Shard CSVs -> eval/results/final-long/; `parallel.py merge --override eval/results/final-long`
# replaces every vector-clock row of these ids in the merged CSV.
# Nodes: the 188 GB hosts of the partition only (c60-c72; the exclude list above also drops the
# 128 GB hosts and the known-bad c54/c2/c37): a 5,400 s vector-clock run of the barrier-heavy
# programs passes 128 GB (stencil1d 130 GiB under T19), which on a 128 GB host is an OOM kill,
# not a measurement.
#   NSHARDS=<n> sbatch --array=0-<n-1> eval/baselines/setup/p_final_long.sh    (one id per shard)
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
export W MODES=vector-clock CAP=5400 TAG=final-long RES=final-long STORE_TAG=final-2026-10-long
export ID_FILE=${ID_FILE:-$W/eval/baselines/setup/final_long_ids.txt}
export NSHARDS=${NSHARDS:?set NSHARDS = the number of lines of the id file}
bash $W/eval/baselines/setup/p_final.sh

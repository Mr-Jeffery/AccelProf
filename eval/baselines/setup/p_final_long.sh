#!/usr/bin/env bash
#SBATCH --job-name=x1-final-long
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c[0-3],c[23-24],c37,c[50-58],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/final-long-%A_%a.log
# X1 second pass (eval/FINAL_SWEEP.md): the cap 5,400 s (--timeout-floor = --timeout-cap = 5400, as
# p_final.sh does at 1,200 s) over the first pass's TIMEOUT ids of P1, P3, P4, P6, P7, P9 (never PI),
# one mode per pass. Everything else is p_final.sh's configuration (BASELINE_HB_DUMP=0,
# YOSEMITE_HB_STATS=1, --reps 3, --confirm, --keep-all).
#   vector-clock (the brief's long pass): ids = setup/final_long_ids.py eval/results/final
#     (>= 1 vector-clock TIMEOUT rep), store final-2026-10-long, results eval/results/final-long/
#   scalar-clock (added 2026-10-14 at Jeffery's request): MODE=scalar-clock, ids =
#     setup/final_long_ids.py --mode scalar-clock eval/results/final, store final-2026-10-long-sc,
#     results eval/results/final-long-sc/
# Each pass has its own store: collect_one wipes <store>/<id>, so recording into final-2026-10 would
# delete the first pass's other-mode dumps of these ids, and the two long passes would delete each
# other's. `parallel.py merge --override eval/results/final-long,eval/results/final-long-sc` replaces
# every row of the (id, mode) keys they hold.
# Nodes: the 188 GB hosts of the partition (c60-c72; the exclude list above drops the 128 GB hosts and
# the known-bad c54/c2/c37): a 5,400 s run of the memory-heavy programs passes 128 GB (stencil1d
# 130 GiB under T19), which on a 128 GB host is an OOM kill, not a measurement. An id whose
# first-pass peak in that mode was <= 10 GB may run on any good node (pass -x c2,c21,c37,c54 on the
# command line, or scontrol update ExcNodeList for a pending task): 4.5x its 1,200 s footprint stays
# far below 128 GB.
# The ids were submitted in batches as the first pass produced them, each batch with its own TAG
# (shard CSV names baselines-cuvein-shard<TAG><k>_<N>.csv must not collide):
#   ID_FILE=<ids> NSHARDS=<lines> TAG=final-long-b<k> sbatch --array=0-<n-1> eval/baselines/setup/p_final_long.sh
#   MODE=scalar-clock ID_FILE=<ids> NSHARDS=<n> TAG=final-long-sc-<x> sbatch --array=0-<n-1> eval/baselines/setup/p_final_long.sh
# Shard k of NSHARDS = the k-th id of the file in MANIFEST order (one id per shard).
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
MODE=${MODE:-vector-clock}
if [ "$MODE" = scalar-clock ]; then SFX=-sc; else SFX=; fi
export W MODES=$MODE CAP=5400 TAG=${TAG:-final-long$SFX} RES=final-long$SFX STORE_TAG=final-2026-10-long$SFX
export ID_FILE=${ID_FILE:-$W/eval/baselines/setup/final_long${SFX/-/_}_ids.txt}
export NSHARDS=${NSHARDS:?set NSHARDS = the number of lines of the id file}
bash $W/eval/baselines/setup/p_final.sh

#!/usr/bin/env bash
#SBATCH --job-name=x1b-final-24h
#SBATCH --partition=max
#SBATCH --exclude=c[0-26],c29,c[33-37],c[39-48],c[50-59],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=2-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/finalb-24h-%A_%a.log
# X1 third pass (eval/FINAL_SWEEP.md section 4b), added 2026-10-14 at Jeffery's request: the (id, mode)
# keys still TIMEOUT at 5,400 s re-run with a 24 h cap, ONE rep (Jeffery's choice; native timing one
# rep as well), one mode per array. Everything else is p_final.sh's configuration (BASELINE_HB_DUMP=0,
# YOSEMITE_HB_STATS=1, --confirm, --keep-all, --timeout-floor = --timeout-cap, --analysis-timeout
# 14400).
# Partition: `max` (8-day limit) because 24 h + native + extraction + analysis does not fit the
# rtx4060ti16g partition's 1-day limit; `max` contains the same hosts, and the exclude lists keep the
# job on rtx4060ti16g hosts only: the default above = the 188 GB hosts c60-c72; for an id whose
# 5,400 s peak was <= 6 GB (16 x its 1.5 h footprint stays below 125 GB) pass
#   -x c2,c[4-22],c[25-26],c29,c[33-37],c[39-48],c54,c57,c59
# (= every rtx4060ti16g host except c2, c37, c54; c21 is not one). The GPU check in p_final.sh refuses
# any host that is not an RTX 4060 Ti / sm_89.
# Own stores (collect_one wipes <store>/<id>): final-2026-10-24h-vc / -sc; results
# eval/results/final-24h-vc/ / -sc/. Merge (p_final_post.sh): a 24 h row replaces the 5,400 s rows of
# its (id, mode) only when the 24 h run reached RACE, CLEAN or a 24 h TIMEOUT; an OOM kill or any other
# ERROR leaves the 5,400 s TIMEOUT standing (Jeffery's choice) and is listed in the report.
#   MODE=vector-clock|scalar-clock ID_FILE=<ids> NSHARDS=<n> TAG=<tag> sbatch --array=0-<n-1> [-x ...] \
#     eval/baselines/setup/p_final_24h.sh        (shard k = the k-th id of the file in manifest order)
set -u
W=${W:-/home/fzheng4/wt-x1b}
MODE=${MODE:?set MODE=vector-clock or scalar-clock}
if [ "$MODE" = scalar-clock ]; then SFX=sc; else SFX=vc; fi
export W MODES=$MODE CAP=86400 REPS=1 TAG=${TAG:-final-b-24h-$SFX} RES=final-b-24h-$SFX STORE_TAG=final-2026-11-24h-$SFX
export ID_FILE=${ID_FILE:?} NSHARDS=${NSHARDS:?set NSHARDS = the number of lines of the id file}
bash $W/eval/baselines/setup/p_final.sh

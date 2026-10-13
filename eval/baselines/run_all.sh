#!/usr/bin/env bash
# THE single command that regenerates every baseline table. Idempotent. Meant to
# run on a GPU node (srun/sbatch); the manifest + classify + tables stages also run
# on the login node. Tolerant of tools that did not build (records a blocker, keeps
# going). Stages can be limited with STAGES="manifest build cuvein ...".
#
#   srun -p rtx3060ti -N1 -n1 -t 06:00:00 bash eval/baselines/run_all.sh
#   # or a subset:
#   STAGES="cuvein racecheck classify tables" srun ... bash eval/baselines/run_all.sh
set -u
cd "$(dirname "$0")/../.." || exit 1          # repo root
source eval/baselines/gpu_env.sh
PY="${PY:-$ACCEL_PROF_HOME/.env/bin/python}"
B=eval/baselines
STAGES="${STAGES:-manifest build cuvein racecheck hirace iguard classify tables}"
PSETS="${PSETS:-}"                            # e.g. PSETS="P4,P5,P6"; empty = all
psarg=""; [ -n "$PSETS" ] && psarg="--pset $PSETS"

has() { echo " $STAGES " | grep -q " $1 "; }

has manifest  && { echo "== manifest =="; $PY $B/mk_manifest.py; }
has build     && { echo "== build =="; $PY $B/build_corpora.py ${PSETS:+--pset $PSETS} || true; }
has cuvein    && { echo "== cuvein =="; $PY $B/run_cuvein.py $psarg --confirm || true; }
has racecheck && { echo "== racecheck =="; $PY $B/run_racecheck.py $psarg || true; }
has hirace    && { echo "== hirace =="; $PY $B/run_hirace.py $psarg 2>/dev/null || echo "  (hirace not available — blocker)"; }
has iguard    && { echo "== iguard =="; $PY $B/run_iguard.py $psarg 2>/dev/null || echo "  (iguard not available — blocker)"; }
has classify  && { echo "== classify =="; $PY $B/classify_endpoints.py || true; }
has tables    && { echo "== tables =="; $PY $B/make_tables.py; }
echo "run_all: done ($STAGES)"

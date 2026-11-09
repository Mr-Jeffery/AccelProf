#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# X12: the C6 analysis (VERDICT_PARALLEL section 7 command + --chain-closure) of a whole suite's recording, sharded.
# Code = the read-only co-chain worktree ~/wt-x11-cochain (be325e03), same as X11 / C6. No GPU.
#   PSET=P1 STORE=final-2026-11-co-sh-p1 RES=co-sharded-p1 NSHARDS=8 W=<harness> sbatch --array=0-7 -J x12-chain-p1 -o ... x12_analyze_suite.sbatch
set -u
PSET=${PSET:-}; IDFILE=${IDFILE:-}; STORE=${STORE:?}; RES=${RES:?}; W=${W:?}; NS=${NSHARDS:-1}; K=${SLURM_ARRAY_TASK_ID:-0}; ATO=${ATO:-14400}
C=/home/fzheng4/wt-x11-cochain; PY=/home/fzheng4/AccelProf/.env/bin/python; B=/mnt/beegfs/fzheng4/cuvein_traces
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$C CUVEIN_HOME=$C; [ -n "${GRAPHCACHE:-}" ] && export CUVEIN_GRAPH_CACHE=$GRAPHCACHE; [ -n "${PREFILTER:-}" ] && export CUVEIN_DOT_PREFILTER=$PREFILTER
SEL=(--pset $PSET --shard $K/$NS); [ -n "$IDFILE" ] && SEL=(--id-file $IDFILE)
d=$W/eval/results/$RES/chain; mkdir -p $d/confirm
echo "host=$(hostname) nproc=$(nproc) co-chain=$(git -C $C rev-parse HEAD) shard=$K/$NS $(date -Is)"
BASELINE_TRACE_DIR=$B/$STORE BASELINE_MODES=collector-only $PY $C/eval/baselines/parallel.py analyze --manifest ${MANIFEST:-$C/eval/baselines/manifest.csv} ${SEL[@]} \
    --tag ${TAG:-chain}-${PSET:-ids} --results-dir $d --confirm --confirm-dir $d/confirm ${CHAINFLAG---chain-closure} --analysis-timeout $ATO --analysis-workers 16
echo "== done rc=$? $(date -Is)"

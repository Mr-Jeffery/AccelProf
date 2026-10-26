#!/usr/bin/env bash
#SBATCH --job-name=t23-diff
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-diff-%x-%A_%a.log
# T23 step 3, phase 2a (eval/R3_CLOSURE.md): analyze the kernels phase 1 flagged twice -- with
# $CUVEIN_R3_LOC_CLOSURE=0 (the pre-T23 rule) and with the closure -- and list every verdict that
# moves. The scan files are eval/results/t23/scan/<SCAN>/shard*.jsonl; one shard per array task
# (over the flagged kernels).
#   SCAN=<name>         (required)
#   OUT=<name>          eval/results/t23/diff/<name>/shard<K>.jsonl   (default: SCAN)
#   ALL=1 [MAXMB=n]     every scanned kernel, not only the flagged ones (the check of the scan's
#                       necessary condition), skipping kernel JSONs over n MB
#   W=<checkout>        whose t23_closure.py and python/ run (default: the task worktree)
W=${W:-/home/fzheng4/wt-t23}
for need in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do [ -d "$need" ] || { echo "MISSING $need on $(hostname)"; exit 75; }; done
cd "$W" || exit 1
source eval/baselines/setup/home_quota_guard.sh
: "${SCAN:?set SCAN=<scan name>}"
N=${NSHARDS:-${SLURM_ARRAY_TASK_COUNT:-1}}; K=${SLURM_ARRAY_TASK_ID:-0}
OUTD=$W/eval/results/t23/diff/${OUT:-$SCAN}
mkdir -p "$OUTD"
echo "host=$(hostname) date=$(date -Is) scan=$SCAN shard=$K/$N head=$(git rev-parse HEAD)"
env | grep -E '^(CUVEIN_|YOSEMITE_)' | sort
.env/bin/python eval/baselines/setup/t23_closure.py diff "$W"/eval/results/t23/scan/$SCAN/shard*.jsonl \
    --shard "$K/$N" ${ALL:+--all} ${MAXMB:+--max-mb $MAXMB} --out "$OUTD/shard$K.jsonl"
rc=$?
echo "done rc=$rc date=$(date -Is)"
exit $rc

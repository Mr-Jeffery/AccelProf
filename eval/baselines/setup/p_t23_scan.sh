#!/usr/bin/env bash
#SBATCH --job-name=t23-scan
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=12:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-scan-%x-%A_%a.log
# T23 step 3, phase 1 (eval/R3_CLOSURE.md): which kernels of a kept BeeGFS trace store can R3's
# location closure change? One shard per array task; reads the kernel JSONs' edges and the dots,
# analyzes nothing. CPU only, BeeGFS (compute nodes).
#   STORE=<tag under /mnt/beegfs/fzheng4/cuvein_traces/>   (required)
#   RTRAW=1             STORE is X4's <label>/<node>/{cfg,runK} layout, not a harness store
#   IDFILE=<path>       only these program ids (default: every program in the store)
#   OUT=<name>          eval/results/t23/scan/<name>/shard<K>.jsonl   (default: STORE)
#   W=<checkout>        whose t23_closure.py and python/ run (default: the task worktree)
W=${W:-/home/fzheng4/wt-t23}
cd "$W" || exit 1
source eval/baselines/setup/home_quota_guard.sh
: "${STORE:?set STORE=<store tag>}"
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUTD=$W/eval/results/t23/scan/${OUT:-$STORE}
mkdir -p "$OUTD"
SRC=(--store "/mnt/beegfs/fzheng4/cuvein_traces/$STORE")
[ -n "${RTRAW:-}" ] && SRC=(--rtraw-root "/mnt/beegfs/fzheng4/cuvein_traces/$STORE")
[ -n "${IDFILE:-}" ] && SRC+=(--ids "$IDFILE")
echo "host=$(hostname) date=$(date -Is) store=$STORE shard=$K/$N head=$(git rev-parse HEAD)"
.env/bin/python eval/baselines/setup/t23_closure.py scan "${SRC[@]}" --shard "$K/$N" \
    --out "$OUTD/shard$K.jsonl"
rc=$?
echo "done rc=$rc date=$(date -Is)"
exit $rc

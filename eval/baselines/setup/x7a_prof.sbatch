#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -t 05:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-prof
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-prof-%j.log
# X7 A2: cProfile of the verdict step, pre-X7 code (f551ca0), one worker per program.
set -u
W=/home/fzheng4/wt-x7a
CODE=${X7_CODE:-/home/fzheng4/AccelProf}     # the f551ca0 checkout whose code is profiled
PY=/home/fzheng4/AccelProf/.env/bin/python
T=/mnt/beegfs/fzheng4/cuvein_traces
OUT=/mnt/beegfs/fzheng4/x7a/prof-$SLURM_JOB_ID
LOG=$W/eval/x_logs
mkdir -p $OUT
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export CUVEIN_HOME=$CODE ACCEL_PROF_HOME=$CODE
echo "host=$(hostname) nproc=$(nproc) mem=$(free -g | awk '/Mem/{print $2}')G start=$(date '+%F %T')"
echo "code=$CODE head=$(git -C $CODE rev-parse --short=12 HEAD) dirty=$(git -C $CODE status --porcelain -uno | wc -l)"
$PY -c "import networkx, pydot; print('networkx', networkx.__version__, 'pydot', pydot.__version__)"

# the Indigo 1.3 program: the PI program with the most vector-clock kernel JSONs below 1000
# among those whose vector-clock dump was saved complete (read from meta.json)
PI=$($PY - <<'PYEOF'
import json, glob, os
best = None
for d in sorted(glob.glob("/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11/PI-*")):
    try:
        m = json.load(open(f"{d}/meta.json"))
    except Exception:
        continue
    vc = m.get("modes", {}).get("vector-clock", {})
    if not vc.get("saved") or vc.get("partial"):
        continue
    n = len(glob.glob(f"{d}/vector-clock/kernel_*.json"))
    if n < 1000 and (best is None or n > best[0]):
        best = (n, os.path.basename(d))
print(best[1] if best else "")
PYEOF
)
echo "indigo program: $PI"

run() {   # label mode_dir dots_dir limit
    $PY $W/eval/baselines/setup/x7_profile.py --label "$1" --mode-dir "$2" --dots-dir "$3" \
        --limit-s "$4" --out "$OUT/$1.prof" > "$LOG/x7a-prof-$1-$SLURM_JOB_ID.log" 2>&1
    echo "done $1 rc=$? $(date '+%T')"
}
run atomicCAS-co   $T/final-2026-11-co/P9-atomicCAS-cuda/collector-only     $T/final-2026-11-co/P9-atomicCAS-cuda/dots 3600 &
run heartwall-sc   $T/final-2026-11-24h-sc/P7-heartwall-cuda/scalar-clock   $T/final-2026-11-24h-sc/P7-heartwall-cuda/dots 14400 &
run knn-sc         $T/final-2026-11-24h-sc/P9-knn-cuda/scalar-clock         $T/final-2026-11-24h-sc/P9-knn-cuda/dots 14400 &
run stencil1d-co   $T/final-2026-11-co-24h/P7-stencil1d-cuda/collector-only $T/final-2026-11-co-24h/P7-stencil1d-cuda/dots 14400 &
[ -n "$PI" ] && run indigo-vc $T/final-2026-11/$PI/vector-clock $T/final-2026-11/$PI/dots 14400 &
wait
echo "end $(date '+%F %T')"

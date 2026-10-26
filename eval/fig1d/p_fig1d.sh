#!/usr/bin/env bash
#SBATCH --job-name=fig1d
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclusive --nodes=1 --ntasks=1
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-fig1d/eval/x_logs/fig1d-%j.log
# M2 / figure 1d: build the two variants of PI conditional_edge_neighbors_block (the reduction loop's
# trailing __syncthreads present = A, removed = B; eval/fig1d/src), record each in both modes x 3 reps
# with X1b's harness flags (parallel.py run), then dump every pair verdict (fig1d_pairs.py).
#   sbatch eval/fig1d/p_fig1d.sh
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d not readable"; exit 2; }; done
W=/home/fzheng4/wt-fig1d; RT=/home/fzheng4/AccelProf; H=$(hostname)
F=$W/eval/fig1d; O=$W/eval/results/fig1d
SRC=$RT/eval/baselines/setup/tools/HiRace/indigo
BIN=/mnt/beegfs/fzheng4/fig1d/bin
cd $RT || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.4 CUDA_PATH=/usr/local/cuda-13.4
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.4/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
h() { sha256sum "$1" | cut -c1-16; }
SAN=$(ldd $RT/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
[ "$(h $SAN)" = 5a20fd14ab6c6806 ] && [ "$(h $RT/lib/libcompute_sanitizer.so)" = b746b4dd23e90f46 ] \
    && [ "$(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)" = a2d7368bc1c61986 ] \
    || { echo "RUNTIME MISMATCH"; exit 99; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $H: GPU [$gpu]"; exit 2;; esac
[ -x $CUDA_HOME/bin/nvcc ] || { echo "NODE-PROBLEM $H: no $CUDA_HOME"; exit 2; }
echo "host=$H gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] runtime=$(git -C $RT rev-parse --short=12 HEAD) harness=$(git -C $W rev-parse --short=12 HEAD) job=${SLURM_JOB_ID:-} $($CUDA_HOME/bin/nvcc --version | tail -1) $(date -Is)"
mkdir -p $BIN $O
# 1. build, the PI recipe (build_indigo_full.py _nvcc)
for V in A B; do
  nvcc -O3 -arch=sm_89 -lineinfo --cudart shared -ccbin /usr/bin/g++ -I $SRC/indigo_include \
      -o $BIN/fig1d_$V $F/src/edge_block_$V.cu || { echo "BUILD FAILED $V"; exit 3; }
done
# the corpus binary of the hand-checked program, built Sep 20, kept for the SASS comparison
for x in fig1d_A fig1d_B; do cuobjdump -sass $BIN/$x > $O/$x.sass.txt; done
cuobjdump -sass $RT/eval/baselines/bin/PI/conditional_edge_neighbors_block > $O/corpus_bin.sass.txt
sha256sum $BIN/fig1d_A $BIN/fig1d_B $RT/eval/baselines/bin/PI/conditional_edge_neighbors_block > $O/binaries.sha256
# 2. manifest: the corpus row of the hand-checked id with the exe swapped
M=$O/manifest_fig1d.csv
$PY - <<'PYEOF'
import csv, os
O = "/home/fzheng4/wt-fig1d/eval/results/fig1d"
rows = [r for r in csv.DictReader(open("/home/fzheng4/wt-fig1d/eval/baselines/manifest.csv"))
        if r["id"] == "PI-conditional_edge_neighbors_block-DAG_100n_100e"]
assert len(rows) == 1
r = rows[0]
print("corpus row args:", r["args"], "exists:", os.path.exists(r["args"].split()[0]))
w = csv.DictWriter(open(f"{O}/manifest_fig1d.csv", "w", newline=""), fieldnames=list(r))
w.writeheader()
for v in "AB":
    x = dict(r, id=f"fig1d-{v}", exe=f"/mnt/beegfs/fzheng4/fig1d/bin/fig1d_{v}", timeout="1200", reps="3")
    w.writerow(x)
PYEOF
# 3. record, X1b's knobs (p_final.sh): no dump, hb_stats on, scalar-clock at 16 shards, cap 1200 s, 3 reps
export BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/fig1d
mkdir -p $O/confirm
$PY $W/eval/baselines/parallel.py run --manifest $M --shard 0/1 --reps 3 --confirm --keep-all \
    --timeout-floor 1200 --timeout-cap 1200 --analysis-timeout 14400 --tag fig1d \
    --results-dir $O --confirm-dir $O/confirm
echo "parallel rc=$? $(date -Is)"
unset BASELINE_HB_DUMP YOSEMITE_HB_STATS BASELINE_HB_SHARDS
# 4. every pair verdict of the kept recordings
$PY $F/fig1d_pairs.py --store $BASELINE_TRACE_DIR --bin $BIN --out $O/pairs.json fig1d-A:fig1d_A fig1d-B:fig1d_B
echo "pairs rc=$? == done $(date -Is)"

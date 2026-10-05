#!/usr/bin/env bash
#SBATCH --job-name=t18-green
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t18-green-%j.log
# T18: the green set (CLAUDE.md A4 + test_instance_gate.py) from worktree W against the INSTALLED
# runtime (W has lib/build/.env/ScoR/cuHadron/nv-compute/lib symlinked to the main checkout).
# LATE=0: default fatbin; LATE=atomic: YOSEMITE_HB_LATE_SEQ=atomic (the _late fatbin, the other
# collector schedule). Every trace is re-recorded.
#   W=/home/fzheng4/wt-t18 LATE=0 sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t18_green.sh
set -u
W=${W:?}; LATE=${LATE:-0}; A=/home/fzheng4/AccelProf
cd $W || exit 1
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export ACCEL_PROF_HOME=$W
[ "$LATE" != 0 ] && export YOSEMITE_HB_LATE_SEQ=$LATE
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) LATE=$LATE $(date -Is)"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    -rfExXs --tb=short -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -60
# keep the lock litmus traces + CFGs of this run (the next run wipes artifacts/) for the A2 write-up
K=/mnt/beegfs/$USER/t18-green/LATE=$LATE; rm -rf $K; mkdir -p $K
for n in race_interblock_none-lock_rtraw norace_interblock_lock_waw race_interblock_none-lock_waw; do
  [ -d ScoR/microbenchmarks/artifacts/$n ] && cp -r ScoR/microbenchmarks/artifacts/$n $K/
done
echo "kept lock litmus traces under $K"

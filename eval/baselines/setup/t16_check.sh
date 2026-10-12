#!/usr/bin/env bash
#SBATCH --job-name=t16-check
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c37
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-t16/build_logs/t16-check-%j.log
# T16 (certain clock) on the worktree's private runtime (t16_build.sh): (1) the green set
# (CLAUDE.md A4 + test_instance_gate.py) plus test_no_dump.py under the default policy, every
# trace re-recorded (getall.sh sets ACCEL_PROF_HOME to the worktree: private lib/, ScoR/,
# cuHadron/) -- expected unchanged, 332 passed, 2 skipped; (2) t16_parity.py: HbClock ==
# specification under both policies on the ScoR litmus, the project's litmus kernels and the
# 16-warp lock, and the invariant Rep_certain >= Rep_recorded on their recorded dumps.
#   W=/home/fzheng4/wt-t16 sbatch eval/baselines/setup/t16_check.sh
set -u
W=${W:-/home/fzheng4/wt-t16}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
unset YOSEMITE_HB_GATE_POLICY CUVEIN_GATE_POLICY CUVEIN_GATE CUVEIN_STRONG_LDST YOSEMITE_HB_LATE_SEQ
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l) $(date -Is)"
echo "runtime $W collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) -> libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
if [ -z "${SKIP_GREEN:-}" ]; then
echo "== (1) green set + gate + no-dump, default policy (worktree runtime)"
find ScoR/microbenchmarks/artifacts -mindepth 1 -maxdepth 1 -exec rm -rf {} +
rm -rf cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    python/test_instance_gate.py python/test_no_dump.py \
    -rfExXs --tb=short -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -60
fi
echo "== (2) parity under both policies + the superset invariant (t16_parity.py)"
OUT=/mnt/beegfs/$USER/t16-check; rm -rf $OUT; mkdir -p $OUT/bin
for k in lock_contention_a2 write_after_unlock_other_schedule atomic_mm_handoff gate_held strong_store_strong_load write_before_lock; do
  nvcc -arch=native -lineinfo --cudart shared python/testdata/$k.cu -o $OUT/bin/$k 2>&1 | grep -v "^$" | head -3
done
nvcc -arch=native -lineinfo --cudart shared -DNB=1 -DNW=4 python/testdata/lock_contention_a2.cu -o $OUT/bin/lock_contention_a2_1x4 2>&1 | head -3
BINS=$(ls $OUT/bin/*; for f in ScoR/microbenchmarks/bin/race_* ScoR/microbenchmarks/bin/norace_*; do [ -f "$f" ] && [ -x "$f" ] && echo "$f"; done)
.env/bin/python eval/baselines/setup/t16_parity.py --out $OUT/runs $BINS 2>&1 | grep -v "Warning\|setParseAction"
echo "== done $(date -Is)"

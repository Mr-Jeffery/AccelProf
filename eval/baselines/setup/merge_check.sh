#!/usr/bin/env bash
#SBATCH --job-name=merge-check
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/merge-check-%j.log
# Checks on the INSTALLED runtime from checkout W (W's lib/build/.env/ScoR/cuHadron/nv-compute/lib
# symlinked to the main checkout): (1) the green set (CLAUDE.md A4 + test_instance_gate.py, then
# test_no_dump.py), every trace re-recorded; (2) the no-dump spot check: two programs recorded with
# YOSEMITE_HB_DUMP=1 twice and YOSEMITE_HB_DUMP=0 once in each mode, the kernel-end aggregates compared.
#   W=<checkout> sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/merge_check.sh
set -u
W=${W:?}; A=/home/fzheng4/AccelProf
cd $W || exit 1
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export ACCEL_PROF_HOME=$W
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_DUMP YOSEMITE_HB_NO_ENGINE
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) $(date -Is)"
echo "runtime: libsanalyzer $(h $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}')) collector $(h $W/lib/libcompute_sanitizer.so) fatbin $(h $W/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin) late $(h $W/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)"

if [ -z "${SKIP_GREEN:-}" ]; then
echo "== (1a) green set: A4 files + test_instance_gate.py"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    -rfExXs --tb=short -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -40
echo "== (1b) test_instance_gate.py alone on the fresh artifacts"
$PY -m pytest python/test_instance_gate.py -q -p no:cacheprovider 2>&1 | tail -3
echo "== (1c) test_no_dump.py"
$PY -m pytest python/test_no_dump.py -q -rfExXs -p no:cacheprovider 2>&1 | tail -8
fi

echo "== (2) no-dump spot check"
OUT=/mnt/beegfs/$USER/merge-check-nodump; rm -rf $OUT; mkdir -p $OUT
for prog in ${SPOT:-norace_interwarp_blkfence_raw race_interblock_blklock_waw}; do
  for mode in vector-clock scalar-clock; do
    for run in dump1a dump1b dump0; do
      D=$OUT/$prog/$mode/$run; mkdir -p $D; cp ScoR/microbenchmarks/bin/$prog $D/
      dump=1; [ $run = dump0 ] && dump=0
      YOSEMITE_HB_MODE=$mode YOSEMITE_HB_DUMP=$dump bash getall.sh $D/$prog > $D/getall.log 2>&1
      echo "$prog $mode $run rc=$? kernels=$(ls $D/dependency_${prog}*/kernel_*.json 2>/dev/null | wc -l)"
    done
  done
done
# at the parity key (a first inline comparison of whole records -- device addresses included --
# and of the no-dump-only hb_aggregates marker reported every pair as different; job 301354)
$PY eval/baselines/setup/nodump_spot_cmp.py $OUT
echo "== done $(date -Is)"

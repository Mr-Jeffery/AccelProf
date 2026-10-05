#!/usr/bin/env bash
#SBATCH --job-name=t1a-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t1a-check-%j.log
# T1a (eval/CP_ASYNC_REPORT.md): (1) the default tool path and the vector-clock dumps of two
# ScoR programs (no cp.async) are identical to the installed library's, up to device
# addresses (the vector-clock dump minus the one added key, hb_async); (2) python/test_cp_async.py -- the tripwire (commit/wait events fire), the
# engine's races, engine == oracle, offline pass == oracle, verdicts in both modes; (3) the
# green set with test_cp_async.py.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_check.sh
set -u
W=/home/fzheng4/wt-T1a; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16)"
OUT=/mnt/beegfs/$USER/t1a_check; rm -rf $OUT; mkdir -p $OUT
run() {
  local D=$1 R=$2 exe=$3; shift 3
  local base=$(basename $exe)
  mkdir -p $D; ln -sf $exe $D/$base
  ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE \
      ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH "$@" \
      accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
  local d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
}
C="$PY eval/baselines/setup/dump_compare.py"
echo "== (1) unchanged outside cp.async"
for exe in $A/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw $A/ScoR/microbenchmarks/bin/norace_interblock_atom; do
  b=$(basename $exe)
  run $OUT/$b/default-main $A $exe; run $OUT/$b/default-t1a $W $exe
  run $OUT/$b/vc-main $A $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock
  run $OUT/$b/vc-t1a $W $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock
  echo "$b default: $($C $OUT/$b/default-main/dump $OUT/$b/default-t1a/dump)"
  echo "$b vector-clock: $($C $OUT/$b/vc-main/dump $OUT/$b/vc-t1a/dump --drop hb_async)"
  $PY -c "import json,glob,sys; d=[json.load(open(f)) for f in glob.glob(sys.argv[1]+'/kernel_*.json')]; e=[json.load(open(f)) for f in glob.glob(sys.argv[2]+'/kernel_*.json')]; print('$b hb_async marker: vector-clock', sorted({j.get('hb_async') for j in d}), 'default', sorted({str(j.get('hb_async')) for j in e}))" $OUT/$b/vc-t1a/dump $OUT/$b/default-t1a/dump
done
echo "== (2) test_cp_async.py"
$PY -m pytest python/test_cp_async.py -rxXs -p no:cacheprovider 2>&1 | grep -v Warning | tail -25
echo "== (3) green set (T1a runtime) + test_cp_async.py"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py python/test_cp_async.py -rxXs 2>&1 | tail -4
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=t3b-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:30:00
#SBATCH --output=/home/fzheng4/wt-T3b/eval/baselines/setup/build_logs/t3b-check-%j.log
# T3b (eval/CRS_CUDA_TRIAGE.md §"Fix"): the private runtime (setup/t3b_build.sh) against the
# installed one (cuVein 3331d35).
#  (1) default tool path identical; vector-clock and scalar-clock dumps identical once the
#      exit records and the hb_exits marker are removed (two ScoR programs);
#  (2) python/test_barrier_exit.py (synthetic + the crs-cuda reproducer + the positive control);
#  (3) the green set, plus test_hb_substitutions.py (T6's I1/I2/I5 xfails must stay xfails)
#      and test_cp_async.py.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t3b_check.sh
set -u
W=/home/fzheng4/wt-T3b; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -- python sanalyzer | wc -l)"
echo "private collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16); live collector $(sha256sum $A/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $A/build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"
OUT=/mnt/beegfs/$USER/t3b_check; rm -rf $OUT; mkdir -p $OUT
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
F="$PY eval/baselines/setup/t3b_filter_exits.py"
echo "== (1) unchanged outside the exit records"
for exe in $A/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw $A/ScoR/microbenchmarks/bin/norace_interblock_atom; do
  b=$(basename $exe)
  run $OUT/$b/default-main $A $exe; run $OUT/$b/default-t3b $W $exe
  echo "$b default: $($C $OUT/$b/default-main/dump $OUT/$b/default-t3b/dump)"
  for m in vector-clock scalar-clock; do
    run $OUT/$b/$m-main $A $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$m
    run $OUT/$b/$m-t3b $W $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$m
    echo "$b $m: $($F $OUT/$b/$m-t3b/dump $OUT/$b/$m-t3b/filtered); $($C $OUT/$b/$m-main/dump $OUT/$b/$m-t3b/filtered)"
  done
  $PY -c "import json,glob,sys; d=[json.load(open(f)) for f in glob.glob(sys.argv[1]+'/kernel_*.json')]; print('$b vector-clock t3b: hb_exits', sorted({j.get('hb_exits') for j in d}), 'tv_violation', [j.get('tv_violation') for j in d], 'exit records', sum(e['type']=='exit' for j in d for e in j['hb_events']))" $OUT/$b/vector-clock-t3b/dump
done
echo "== (2) test_barrier_exit.py"
$PY -m pytest python/test_barrier_exit.py -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -25
echo "== (3) green set (T3b runtime) + test_barrier_exit + test_hb_substitutions + test_cp_async"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -15
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=t2-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t2-check-%j.log
# T2 prototype check (eval/HOST_MEMCPY_STUDY.md §3). (1) Flag unset: the T2 runtime's dumps
# equal the installed library's (default tool path and a vector-clock dump; two ScoR
# programs; up to device addresses) and no host_ops.json is written. (2) Flag set on the
# same program: identical kernel dumps plus a host_ops.json. (3) The micro test, four
# variants x both modes, YOSEMITE_HB_TRACE=1 YOSEMITE_HB_HOST_MEMCPY=1: host_hb.py races.
# (2b) YOSEMITE_HB_STATS (T5a) adds only hb_stats. GREEN=1: the green set at the end.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t2_check.sh
set -u
W=/home/fzheng4/wt-T2; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader)"
echo "T2 collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) (main $(sha256sum $A/lib/libcompute_sanitizer.so | cut -c1-16))"
OUT=/mnt/beegfs/$USER/t2_check; rm -rf $OUT; mkdir -p $OUT
run() {   # run <dir> <runtime> <exe> [env...]: dump -> <dir>/dump, accelprof log kept
  local D=$1 R=$2 exe=$3; shift 3
  local base=$(basename $exe)
  mkdir -p $D; ln -sf $exe $D/$base
  ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE \
      -u YOSEMITE_HB_HOST_MEMCPY ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH "$@" \
      accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
  local d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
}
C="$PY eval/baselines/setup/dump_compare.py"
echo "== (1)/(2) gating"
for exe in $A/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw $A/ScoR/microbenchmarks/bin/norace_interblock_atom; do
  b=$(basename $exe)
  run $OUT/$b/default-main $A $exe
  run $OUT/$b/default-t2 $W $exe
  run $OUT/$b/vc-main $A $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock
  run $OUT/$b/vc-t2 $W $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock
  run $OUT/$b/vc-t2-flag $W $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock YOSEMITE_HB_HOST_MEMCPY=1
  echo "$b default main vs t2: $($C $OUT/$b/default-main/dump $OUT/$b/default-t2/dump)"
  echo "$b vector-clock main vs t2: $($C $OUT/$b/vc-main/dump $OUT/$b/vc-t2/dump)"
  echo "$b vector-clock t2 vs t2+flag: $($C $OUT/$b/vc-t2/dump $OUT/$b/vc-t2-flag/dump)"
  echo "$b host_ops.json: unset=$(ls $OUT/$b/vc-t2/dump/host_ops.json 2>/dev/null | wc -l) default=$(ls $OUT/$b/default-t2/dump/host_ops.json 2>/dev/null | wc -l) flag=$(ls $OUT/$b/vc-t2-flag/dump/host_ops.json 2>/dev/null | wc -l) ($(grep -c '"kind"' $OUT/$b/vc-t2-flag/dump/host_ops.json 2>/dev/null) ops)"
  # T5a's hook in the same build: YOSEMITE_HB_STATS adds only the hb_stats field
  run $OUT/$b/vc-t2-stats $W $exe YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock YOSEMITE_HB_STATS=1
  echo "$b vector-clock t2 vs t2+HB_STATS: $($C $OUT/$b/vc-t2/dump $OUT/$b/vc-t2-stats/dump --drop hb_stats)"
done
echo "== (3) micro test"
B=$OUT/bin; mkdir -p $B
for v in racy fixed kfirst-racy kfirst-fixed; do
  F=""; case $v in fixed) F="-DFIXED";; kfirst-racy) F="-DKERNEL_FIRST";; kfirst-fixed) F="-DKERNEL_FIRST -DFIXED";; esac
  nvcc -arch=sm_89 -lineinfo --cudart shared $F -o $B/host_memcpy_race_$v python/testdata/host_memcpy_race.cu
  for m in vector-clock scalar-clock; do
    D=$OUT/micro/$v/$m
    run $D $W $B/host_memcpy_race_$v YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$m YOSEMITE_HB_HOST_MEMCPY=1
    echo "-- $v $m: $(cat $D/rc.txt) kernels=$(ls $D/dump/kernel_*.json 2>/dev/null | wc -l)"
    $PY python/host_hb.py $D/dump | sed 's/^/     /'
  done
done
cp $OUT/micro/racy/vector-clock/dump/host_ops.json $W/eval/baselines/setup/t2_evidence/host_ops.micro_racy.json 2>/dev/null
cp $OUT/micro/kfirst-fixed/vector-clock/dump/host_ops.json $W/eval/baselines/setup/t2_evidence/host_ops.micro_kfirst-fixed.json 2>/dev/null
if [ -n "${GREEN:-}" ]; then
  echo "== green set (T2 runtime)"
  rm -rf ScoR/microbenchmarks/artifacts/*
  $PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
      python/test_coherent_ldst.py python/test_atomic_memory_model.py python/test_host_hb.py -rxXs 2>&1 | tail -4
fi
echo "== done $(date -Is)"

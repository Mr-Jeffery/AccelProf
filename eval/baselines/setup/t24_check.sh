#!/usr/bin/env bash
#SBATCH --job-name=t24-check
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=12:00:00
# T24 parity A, with the worktree's private runtime (t24_build.sh; W/lib -> stage-t24/rt-lib):
# (0) the default tool path (no YOSEMITE_HB_TRACE), the installed runtime vs the worktree's, on two
# ScoR programs, then two worktree runs byte for byte (t20_default_compare.py); then per
# configuration in CONFIGS the green set -- (1a) the CLAUDE.md A4 files + test_instance_gate.py +
# test_syncwarp.py, (1b) test_instance_gate.py alone on the fresh artifacts, (1c) test_no_dump.py,
# (1d) test_sync_shapes.py -- every trace re-recorded, the knob exported for the whole pytest run:
#   1    YOSEMITE_HB_SHARDS unset (the serial pass)
#   8    YOSEMITE_HB_SHARDS=8
#   16   YOSEMITE_HB_SHARDS=16
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-check-%j.log <W>/eval/baselines/setup/t24_check.sh
set -u
W=${W:-/home/fzheng4/wt-t24}; A=/home/fzheng4/AccelProf
for d in $A /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
unset YOSEMITE_HB_LATE_SEQ YOSEMITE_HB_DUMP YOSEMITE_HB_NO_ENGINE YOSEMITE_HB_SHARDS YOSEMITE_HB_SHARD_INLINE_MAX YOSEMITE_HB_MODE
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) nproc=$(nproc) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l) $(date -Is)"
for rt in $A $W; do
  echo "runtime $rt collector $(h $rt/lib/libcompute_sanitizer.so) -> libsanalyzer $(h $(ldd $rt/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}'))"
done

if [ -z "${SKIP_DEFAULT:-}" ]; then
echo "== (0) default path"
OUT=/mnt/beegfs/$USER/t24-check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  # directory names as t20_default_compare.py expects them: live = the installed runtime,
  # t20 / t20b = two runs of the worktree's (here T24's)
  for rt in live t20 t20b; do
    R=$A; [ $rt != live ] && R=$W
    D=$OUT/$base/default/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
    ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_HB_DUMP \
        -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
        accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
    d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
  done
done
$PY eval/baselines/setup/t20_default_compare.py $OUT
fi

for cfg in ${CONFIGS:-1 8 16}; do
  unset YOSEMITE_HB_SHARDS YOSEMITE_HB_SHARD_INLINE_MAX
  [ "$cfg" != 1 ] && export YOSEMITE_HB_SHARDS=$cfg
  echo "==== config $cfg: YOSEMITE_HB_SHARDS=${YOSEMITE_HB_SHARDS:-unset} $(date -Is)"
  echo "== (1a) green set: A4 files + test_instance_gate.py + test_syncwarp.py"
  rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
  $PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
      python/test_coherent_ldst.py python/test_atomic_memory_model.py \
      python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
      python/test_syncwarp.py \
      -rfExXs --tb=short -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -40
  echo "== (1b) test_instance_gate.py alone on the fresh artifacts"
  $PY -m pytest python/test_instance_gate.py -q -p no:cacheprovider 2>&1 | tail -3
  echo "== (1c) test_no_dump.py"
  $PY -m pytest python/test_no_dump.py -q -rfExXs -p no:cacheprovider 2>&1 | tail -8
  echo "== (1d) test_sync_shapes.py"
  $PY -m pytest python/test_sync_shapes.py -q -rfExXs -p no:cacheprovider 2>&1 | tail -8
done
echo "== done $(date -Is)"

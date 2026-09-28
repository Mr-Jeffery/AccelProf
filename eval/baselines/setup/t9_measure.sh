#!/usr/bin/env bash
#SBATCH --job-name=t9-measure
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-measure-%j.log
# T9 measurements with the T9 worktree runtime (the "before" is T5a's job 287964, same
# programs, same helper eval/baselines/setup/t5a_stats.py, pre-T9 engine layout):
#  (A) YOSEMITE_HB_STATS on T5a's three programs -- the bucket term (tiled_gemm N=256,
#      reduction large, Indigo3 CC push 1296n under a 300 s cap with snapshots). 188 GB node.
#  (B) hb_events before/after the local-memory exclusion (I5, D14): local_mem_blocks.cu in
#      vector-clock mode, and one P7 program with LDL/STL in its SASS in scalar-clock mode
#      (a dump that is not replayed, only counted), main runtime vs T9 runtime.
#   sbatch -p rtx4060ti16g -w c70 eval/baselines/setup/t9_measure.sh
set -u
W=/home/fzheng4/wt-T9; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
EV=$W/eval/baselines/setup/t9_stats; mkdir -p $EV
B=/mnt/beegfs/$USER/t9_bin; mkdir -p $B
if [ -z "${SKIP_A:-}" ]; then
echo "== (A) HB_STATS, T9 runtime"
nvcc -arch=sm_89 -lineinfo --cudart shared -o $B/tiled_gemm python/testdata/scale/tiled_gemm.cu
S="$PY eval/baselines/setup/t5a_stats.py --out $EV"
CC=CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug
$S --mode vector-clock --label t9-tiled_gemm-256 --exe $B/tiled_gemm --args 256 --cap 900
$S --mode vector-clock --label t9-reduction-norace-large --exe $A/eval/baselines/bin/P4/reduction_norace \
   --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
$S --mode vector-clock --label t9-cc-push-1296n --exe $A/eval/baselines/bin/P1/${CC}__slower_atomic \
   --args "$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect4dim_rand_torus_1296n_10368e.egr 1 0 1" \
   --cap 300 --every 1000
fi

echo "== (B) hb_events and local records, main vs T9 runtime"
count() {   # dump dir -> per kernel: bytes, events, local records (text counts, no json load)
  for f in $(ls $1/kernel_*.json 2>/dev/null | sort -V); do
    echo "  $(basename $f) bytes=$(stat -c %s $f) events=$(grep -o '"seq": ' $f | wc -l) local=$(grep -o '"space": "local"' $f | wc -l)"
  done
}
run() {   # runtime-root mode workdir exe args... -> dump under workdir/dump
  local R=$1 mode=$2 D=$3; shift 3
  mkdir -p $D; cd $D
  local scope; scope=$(ls $D/../cubins/atomic_scope.txt 2>/dev/null)
  timeout -s KILL ${CAP:-600} env ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$mode \
      ${scope:+YOSEMITE_ATOMIC_SCOPE_FILE=$scope} accelprof -t pc_dependency_analysis -n 1 "$@" < /dev/null > run.log 2>&1
  echo "  rc=$? $(du -sh $D 2>/dev/null | cut -f1)"
  d=$(ls -d $D/dependency_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
  cd $W
}
OUT=/mnt/beegfs/$USER/t9_local; rm -rf $OUT; mkdir -p $OUT/local_mem_blocks/cubins
nvcc -arch=sm_89 -lineinfo --cudart shared -o $OUT/local_mem_blocks/local_mem_blocks python/testdata/local_mem_blocks.cu
( cd $OUT/local_mem_blocks/cubins && cuobjdump -xelf all ../local_mem_blocks > /dev/null && for c in *.cubin; do nvdisasm -bbcfg -poff $c > ${c%.cubin}.dot; done \
  && $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt > /dev/null )
for which in main t9; do
  R=$A; [ $which = t9 ] && R=$W
  echo "local_mem_blocks vector-clock $which"
  run $R vector-clock $OUT/local_mem_blocks/$which $OUT/local_mem_blocks/local_mem_blocks
  count $OUT/local_mem_blocks/$which/dump
  grep -o '"space": "local"' $OUT/local_mem_blocks/$which/dump/kernel_0.json >/dev/null 2>&1
  $PY -c "import json,sys; t=json.load(open('$OUT/local_mem_blocks/$which/dump/kernel_0.json')); r=t.get('hb_races',[]); print('  hb_races', len(r), 'local', sum(x['space']=='local' for x in r))"
done
for p in hotspot pathfinder srad stencil1d heartwall lavaMD particlefilter; do
  exe=$A/eval/baselines/bin/P7/$p-cuda
  n=$(cuobjdump -sass $exe 2>/dev/null | grep -cE '\b(LDL|STL)\b')
  echo "P7 $p: LDL/STL instructions in SASS: $n"
  [ "$n" -gt 0 ] && { P7=$p; break; }
done
if [ -n "${P7:-}" ]; then
  args=$(.env/bin/python -c "
import csv
for r in csv.DictReader(open('eval/baselines/manifest.csv')):
    if r['id'] == 'P7-$P7-cuda': print(r['args'])")
  mkdir -p $OUT/$P7/cubins
  ( cd $OUT/$P7/cubins && cuobjdump -xelf all $A/eval/baselines/bin/P7/$P7-cuda > /dev/null && for c in *.cubin; do nvdisasm -bbcfg -poff $c > ${c%.cubin}.dot; done \
    && $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt > /dev/null )
  for which in main t9; do
    R=$A; [ $which = t9 ] && R=$W
    echo "P7 $P7 scalar-clock $which (cap ${CAP:-600}s; args: $args)"
    ln -sf $A/eval/baselines/bin/P7/$P7-cuda $OUT/$P7/$P7-cuda
    [ -d $A/eval/baselines/data ] && ln -sfn $A/eval/baselines/data $OUT/data
    CAP=${P7CAP:-600} run $R scalar-clock $OUT/$P7/$which $OUT/$P7/$P7-cuda $args
    count $OUT/$P7/$which/dump
  done
fi
echo "== done $(date -Is)"

#!/bin/bash
# Step 5: wall clock under native / Sanitizer HB path (scalar-clock, collector
# only, no offline analysis) / NVBit mem_trace / atom_after. REPS runs each,
# min and all values reported. Binaries are copied to node-local scratch so the
# collector's dependency_* dumps never land in the shared bin/ directories.
# NVBit tool output goes to /dev/null (formatting cost kept, disk excluded);
# the collector writes its kernel JSON to node-local /tmp.
source "$(dirname "$0")/env.sh"
REPS=${1:-3}   # usage: cost.sh [REPS] [large]
APH=/home/fzheng4/AccelProf
S=/tmp/fzheng4_t13_cost; rm -rf $S; mkdir -p $S
cp $APH/ScoR/microbenchmarks/bin/race_interblock_fence_rtraw $S/
cp $APH/eval/baselines/bin/P4/matrix-multiplication_norace $S/
MMIN=$APH/eval/baselines/inputs/matrix-multiplication.small.in
MT=$NVBIT_ROOT/1.8/nvbit_release_x86_64/tools/mem_trace/mem_trace.so
AA=$SPIKE/atom_after/atom_after.so
cd $S
# atomic-scope sidecar, as the harness builds it
for b in race_interblock_fence_rtraw matrix-multiplication_norace; do
  PATH=$CUDA_HOME/bin:$PATH $APH/.env/bin/python -c "
import sys; sys.path.insert(0, '$APH/eval/baselines'); import blib, os
env = blib.base_env('$CUDA_HOME')
scope, cubs = blib.extract(os.path.realpath('$b'), '$S/${b}_cubins', env)
open('$S/$b.scope_path', 'w').write(scope)"
done
t() { local s e; s=$(date +%s.%N); "$@"; local rc=$?; e=$(date +%s.%N); echo "$(echo "$e - $s" | bc) $rc"; }
run() { # name bin stdin
  local name=$1 b=$2 in=$3 cfg w rc
  for cfg in native sanitizer-hb mem_trace atom_after; do
    local ws=()
    for r in $(seq 1 $REPS); do
      rm -rf $S/dependency_${b}_*
      case $cfg in
        native)       read w rc < <(t bash -c "./$b < $in > /dev/null 2>&1") ;;
        sanitizer-hb) read w rc < <(t env ACCEL_PROF_HOME=$APH CUDA_HOME=$CUDA_HOME \
                          PATH=$APH/bin:$CUDA_HOME/bin:$PATH \
                          LD_LIBRARY_PATH=$CUDA_HOME/compute-sanitizer:$CUDA_HOME/lib64:/opt/ohpc/pub/compiler/gcc/12.4.0/lib64 \
                          YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock \
                          YOSEMITE_ATOMIC_SCOPE_FILE=$(cat $S/$b.scope_path) \
                          bash -c "accelprof -t pc_dependency_analysis -n 1 ./$b < $in > $S/$b.san.log 2>&1") ;;
        mem_trace)    read w rc < <(t bash -c "LD_PRELOAD=$MT ./$b < $in > /dev/null 2>&1") ;;
        atom_after)   read w rc < <(t bash -c "ATOM_AFTER_OUT=/dev/null LD_PRELOAD=$AA ./$b < $in > /dev/null 2>&1") ;;
      esac
      ws+=("$w/rc$rc")
    done
    local extra=""
    if [ $cfg = sanitizer-hb ]; then
      extra="dump: $(du -sh $S/dependency_${b}_* 2>/dev/null | cut -f1) events: $(grep -o '"type"' $S/dependency_${b}_*/kernel_*.json 2>/dev/null | wc -l)"
    fi
    echo "$name $cfg ${ws[*]} $extra"
  done
}
if [ "$2" = large ]; then   # one kernel-dominated data point
  run matmul-norace-large matrix-multiplication_norace $APH/eval/baselines/inputs/matrix-multiplication.large.in
  exit 0
fi
run rtraw race_interblock_fence_rtraw /dev/null
run matmul-norace-small matrix-multiplication_norace $MMIN
# record counts for the NVBit tools (one extra run each, output kept)
LD_PRELOAD=$MT ./matrix-multiplication_norace < $MMIN 2>&1 | grep -c '^MEMTRACE: CTX.*grid_launch_id' | sed 's/^/matmul mem_trace warp-records: /'
ATOM_AFTER_OUT=$S/mm.rec LD_PRELOAD=$AA ./matrix-multiplication_norace < $MMIN > /dev/null 2>&1
echo "matmul atom_after lane-records: $(wc -l < $S/mm.rec) (B/A: $(grep -c '^AA [BA] ' $S/mm.rec))"
cp $S/mm.rec $WORK/matmul_atom_after.rec

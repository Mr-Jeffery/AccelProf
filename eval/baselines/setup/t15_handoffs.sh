#!/usr/bin/env bash
#SBATCH --job-name=t15-handoffs
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
# T15 (eval/LATE_SEQ.md): the lock idiom of python/testdata/lock_contention_a2.cu (kernel
# kcontend) at T14's contention levels (1x2, 1x4, 4x4 warps; ITERS acquisitions per warp; RUNS
# runs each) under YOSEMITE_HB_LATE_SEQ = 0 (off), atomic, timer, with the worktree runtime.
# A late-keyed dump carries both keys, so each such run is scored twice by
# a2_window_count.py handoffs: in its own (late) order and, after late_seq.py prep, in buffer
# order. Wall-clock of each accelprof run and its record count go to times.tsv.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t15-handoffs-%j.log \
#       eval/baselines/setup/t15_handoffs.sh
set -u
W=${W:?set W=<task worktree>}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$CUDA_HOME/compute-sanitizer:$LD_LIBRARY_PATH
export PATH=$W/bin:$PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l)"
echo "collector $(sha256sum lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16) fatbin $(sha256sum nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin | cut -c1-16)"
T=${OUT:-/mnt/beegfs/$USER/t15-late-seq/handoffs}; rm -rf "$T"; mkdir -p "$T"
echo -e "cfg\tvariant\trun\twall_s\trc\tevents" > $T/times.tsv
for cfg in 1x2 1x4 4x4; do
  nb=${cfg%x*}; nw=${cfg#*x}
  B=$T/$cfg/build; mkdir -p "$B"
  nvcc -arch=native -lineinfo --cudart shared -DNB=$nb -DNW=$nw -DITERS=${ITERS:-16} \
      python/testdata/lock_contention_a2.cu -o "$B/lock_contention_a2"
  bash getall.sh "$B/lock_contention_a2" > "$B/getall.log" 2>&1     # CFG dots + sidecar
  export YOSEMITE_ATOMIC_SCOPE_FILE=$B/lock_contention_a2_extracted_cubins/atomic_scope.txt
  for v in off atomic timer; do
    D=$T/$cfg/$v; mkdir -p "$D"; ln -sf "$B/lock_contention_a2" "$D/lock_contention_a2"
    for r in $(seq 1 ${RUNS:-5}); do
      lv=$v; [ $v = off ] && lv=0
      t0=$(date +%s.%N)
      ( cd "$D" && YOSEMITE_HB_TRACE=1 YOSEMITE_HB_LATE_SEQ=$lv \
          accelprof -v -t pc_dependency_analysis -n 1 ./lock_contention_a2 > run_$r.log 2>&1 )
      rc=$?; t1=$(date +%s.%N)
      d=$(ls -td "$D"/dependency_lock_contention_a2_* 2>/dev/null | head -1)
      [ -n "$d" ] && mv "$d" "$D/rep$r"
      n=$(.env/bin/python -c "import json,glob,sys; print(sum(len(json.load(open(f))['hb_events']) for f in glob.glob(sys.argv[1]+'/kernel_*.json')))" "$D/rep$r" 2>/dev/null)
      echo -e "$cfg\t$v\t$r\t$(echo "$t1 - $t0" | bc)\t$rc\t${n:-NA}" >> $T/times.tsv
    done
  done
  DOTS=("$B"/lock_contention_a2_extracted_cubins/*.dot)
  echo "== $cfg off (buffer order, late key not drawn)"
  .env/bin/python eval/baselines/a2_window_count.py handoffs --dots "${DOTS[@]}" -- "$T/$cfg/off"/rep*/kernel_*.json | tail -1
  for v in atomic timer; do
    echo "== $cfg $v: W0 / seq order / ties"
    .env/bin/python eval/baselines/late_seq.py prep --out "$T/$cfg/$v-buffer" "$T/$cfg/$v"/rep*/kernel_*.json | tail -1
    echo "== $cfg $v late order"
    .env/bin/python eval/baselines/a2_window_count.py handoffs --dots "${DOTS[@]}" -- "$T/$cfg/$v"/rep*/kernel_*.json | tail -1
    echo "== $cfg $v buffer order (same runs)"
    .env/bin/python eval/baselines/a2_window_count.py handoffs --dots "${DOTS[@]}" -- "$T/$cfg/$v-buffer"/rep*/kernel_*.json | tail -1
  done
done
cat $T/times.tsv
echo "== done $(date -Is)"

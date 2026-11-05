#!/usr/bin/env bash
# X11 stage B, inside the ubuntu22.04 image (artifact binaries need GLIBC 2.34). One (app, tool, run) per job.
#   TOOL = racecheck | iguard | vector-clock | scalar-clock ; APP ; RUN ; TAG ; TREE ; LOGD
set -u
RT=/home/fzheng4/AccelProf; X=/home/fzheng4/wt-x11/eval/x11
case "$TOOL" in vector-clock|scalar-clock) W=/home/fzheng4/wt-x1b;; *) W=/home/fzheng4/wt-x7b;; esac
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source $RT/eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "in-container: $(. /etc/os-release; echo $PRETTY_NAME) glibc=$(ldd --version | head -1 | awk '{print $NF}') tool=$TOOL app=$APP run=$RUN"
echo "runtime $RT HEAD=${X11_RT_HEAD:0:12} harness $W HEAD=${X11_W_HEAD:0:12} nvcc=$($CUDA_HOME/bin/nvcc --version | tail -1) sanitizer=$($CUDA_HOME/compute-sanitizer/compute-sanitizer --version 2>&1 | tail -1)"
$PY $X/x11_mktree.py $TREE "$APP" || exit 3
M=$TREE/manifest.csv; ID=X11-$APP
mkdir -p $LOGD
case "$TOOL" in
racecheck)
  $PY $W/eval/baselines/run_sanitizer.py --manifest $M --tools racecheck --id $ID --reps 1 --timeout 84600 --out $LOGD/racecheck.csv ;;
iguard)
  export IGUARD_SO=$RT/eval/baselines/setup/iguard/iguard.so BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/x11_work/iguard_logs/$TAG
  echo "iguard.so sha=$(sha256sum $IGUARD_SO | cut -c1-16)"
  $PY $W/eval/baselines/run_iguard.py --manifest $M --id $ID --reps 1 --timeout 84600 --out $LOGD/iguard.csv ;;
vector-clock|scalar-clock)
  # accelprof needs git (absent in the image; metadata only) and the app's cudart symbols (artifact binaries link cudart statically):
  # shadow ACCEL_PROF_HOME with a copy of bin/accelprof that also preloads libcudart.so.13 (bin/ itself untouched)
  export X11_CUDART=/usr/local/cuda-13.3/lib64/libcudart.so.13
  mkdir -p $TREE/shim; cp $X/shim/git $TREE/shim/git
  APHD=$TREE/aph; rm -rf $APHD; mkdir -p $APHD/bin
  for e in $RT/* $RT/.env; do n=$(basename $e); [ $n = bin ] || ln -sfn $e $APHD/$n; done
  for e in $RT/bin/*; do ln -sfn $e $APHD/bin/$(basename $e); done
  rm $APHD/bin/accelprof
  sed 's#LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE}#LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE}#' $RT/bin/accelprof > $APHD/bin/accelprof; chmod +x $APHD/bin/accelprof
  diff $RT/bin/accelprof $APHD/bin/accelprof | grep -c '^>' | sed 's/^/accelprof lines changed: /'
  export ACCEL_PROF_HOME=$APHD CUVEIN_HOME=$APHD PATH=$TREE/shim:$APHD/bin:$PATH
  export BASELINE_MODES=$TOOL BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16
  export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$TAG
  echo "hb_shards(scalar-clock)=16 hb_dump=0 mode=$TOOL"
  # recording half only (the analysis half is a separate job, x11_b_analyze.sbatch, afterany this one)
  $PY $X/x11_b_collect.py $W $M $ID ${CAP:-84600};;
*) echo "bad TOOL $TOOL"; exit 4;;
esac
echo "== tool rc=$?"

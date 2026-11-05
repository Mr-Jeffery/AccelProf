#!/usr/bin/env bash
# runs inside the container. Harness = C1's (eval/collector-only 0c286343, ~/wt-co: has the -v drain counts), python/ = installed runtime = wt-co's (C1: identical). (see x11_a_collect.sbatch)
set -u
W=/home/fzheng4/wt-co; RT=/home/fzheng4/AccelProf; X=/home/fzheng4/wt-x11/eval/x11
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_TRACE_ALLOW_NONBEEGFS
export BASELINE_MODES=collector-only
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source $RT/eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
# The artifact binaries link cudart statically; libcompute_sanitizer.so needs cudart symbols (cudaDeviceGetStreamPriorityRange)
# that only a shared-cudart app exports. Workaround: a copy of bin/accelprof that also preloads libcudart.so.13
# (the only change; bin/ itself is untouched).
export X11_CUDART=/usr/local/cuda-13.3/lib64/libcudart.so.13
[ -e "$X11_CUDART" ] || { echo "no $X11_CUDART"; exit 4; }
mkdir -p $TREE/shim; cp $X/shim/git $TREE/shim/git
# shadow ACCEL_PROF_HOME: symlinks to the runtime, except bin/accelprof (patched copy). blib puts $ACCEL_PROF_HOME/bin first on PATH.
APHD=$TREE/aph; rm -rf $APHD; mkdir -p $APHD/bin
for e in $RT/* $RT/.env; do n=$(basename $e); [ $n = bin ] || ln -sfn $e $APHD/$n; done
for e in $RT/bin/*; do ln -sfn $e $APHD/bin/$(basename $e); done
rm $APHD/bin/accelprof
sed 's#LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE}#LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE}#' $RT/bin/accelprof > $APHD/bin/accelprof; chmod +x $APHD/bin/accelprof
diff $RT/bin/accelprof $APHD/bin/accelprof | grep -c '^>' | sed 's/^/accelprof lines changed: /'
export ACCEL_PROF_HOME=$APHD CUVEIN_HOME=$APHD
export PATH=$TREE/shim:$APHD/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$TAG
echo "in-container: $(. /etc/os-release; echo $PRETTY_NAME) glibc=$(ldd --version | head -1 | awk '{print $NF}')"
echo "runtime $RT HEAD=${X11_RT_HEAD:0:12} collector=$(sha256sum $RT/lib/libcompute_sanitizer.so | cut -c1-16) harness $W HEAD=${X11_W_HEAD:0:12} nvcc=$($CUDA_HOME/bin/nvcc --version | tail -1)"
$PY $X/x11_mktree.py $TREE "${IDS:-}" || exit 3
SEL=(--id-file /dev/stdin)
ids=$($PY -c "import csv;print(','.join(r['id'] for r in csv.DictReader(open('$TREE/manifest.csv'))))")
mkdir -p /home/fzheng4/wt-x11/eval/x_logs/x11/stageA-$TAG/confirm
echo "no HbClock (YOSEMITE_HB_TRACE unset), accelprof -n 1, cap=84600 s, reps=1, ids=$ids"
$PY $W/eval/baselines/parallel.py run --manifest $TREE/manifest.csv --id $ids --reps 1 --confirm --keep-all \
    --timeout-floor 84600 --timeout-cap 84600 --analysis-timeout 14400 --tag $TAG \
    --results-dir /home/fzheng4/wt-x11/eval/x_logs/x11/stageA-$TAG --confirm-dir /home/fzheng4/wt-x11/eval/x_logs/x11/stageA-$TAG/confirm
echo "== harness rc=$?"

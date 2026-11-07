#!/usr/bin/env bash
# inside the ubuntu22.04 container (artifact binaries need glibc 2.34). Adapted from X11's x11_a_inner.sh (eval/sc-native-hecbench).
set -u
X=$W/eval/x12
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_TRACE_ALLOW_NONBEEGFS
export BASELINE_MODES=collector-only BASELINE_WORKERS=$N BASELINE_KEEP_REPS=1
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source /home/fzheng4/AccelProf/eval/baselines/gpu_env.sh      # PY etc.
export PATH=/usr/local/cuda-13.3/bin:$PATH
export X11_CUDART=/usr/local/cuda-13.3/lib64/libcudart.so.13
[ -e "$X11_CUDART" ] || { echo "no $X11_CUDART"; exit 4; }
mkdir -p $TREE/shim; cp $X/shim/git $TREE/shim/git
# shadow ACCEL_PROF_HOME = symlinks to the runtime, except bin/accelprof (patched copy that also preloads the shared cudart)
APHD=$TREE/aph; rm -rf $APHD; mkdir -p $APHD/bin
for e in $RT/* $RT/.env; do n=$(basename $e); [ $n = bin ] || ln -sfn $e $APHD/$n; done
for e in $RT/bin/*; do ln -sfn $e $APHD/bin/$(basename $e); done
rm $APHD/bin/accelprof
sed 's#LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE}#LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE}#' $RT/bin/accelprof > $APHD/bin/accelprof; chmod +x $APHD/bin/accelprof
echo "accelprof lines changed: $(diff $RT/bin/accelprof $APHD/bin/accelprof | grep -c '^>')"
export ACCEL_PROF_HOME=$APHD CUVEIN_HOME=$APHD
export PATH=$TREE/shim:$APHD/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$STORE
h() { sha256sum "$1" | cut -c1-16; }
SAN=$(ldd $RT/lib/libcompute_sanitizer.so | awk '/libsanalyzer/{print $3}')
echo "runtime $RT HEAD=${X12_RT_HEAD:0:12} libsanalyzer=$(h $SAN) ($SAN) collector=$(h $RT/lib/libcompute_sanitizer.so) harness $W HEAD=${X12_W_HEAD:0:12} dirty=$X12_W_DIRTY nvcc=$($CUDA_HOME/bin/nvcc --version | tail -1)"
echo "binary: $(sha256sum /home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/supercollider-artifacts/bin/hecbench/native/$APP | cut -c1-16)"
# manifest of the artifact's native binary (X11's tool: id X11-<app>, build sc-native, args from artifact_subset.json)
$PY $W/eval/x12/x12_mktree.py $TREE $APP || exit 3
mkdir -p $W/eval/results/$RES/confirm
echo "no HbClock, accelprof -v -n $N, cap=84600 s, reps=$REPS, id=X11-$APP"
$PY $W/eval/baselines/parallel.py run --manifest $TREE/manifest.csv --id X11-$APP --reps $REPS --confirm --keep-all \
    --timeout-floor 84600 --timeout-cap 84600 --analysis-timeout 14400 --analysis-workers 16 --tag x12-$APP \
    --results-dir $W/eval/results/$RES --confirm-dir $W/eval/results/$RES/confirm
echo "== harness rc=$?"

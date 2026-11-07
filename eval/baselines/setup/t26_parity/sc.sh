#!/usr/bin/env bash
#SBATCH --job-name=t26-sc
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
# T26 x X12: same-stream parity on SuperCollider's native HeCBench binaries (X12's program set).
# Each app is recorded ONCE in collector-only mode (installed library, -n 1, accelprof -v) through the
# capture shim, inside X12's container with X12's shadow ACCEL_PROF_HOME (bin/accelprof also preloads
# libcudart.so.13) and X12's run tree (x12_mktree.py: cwd src/<app>-cuda, args from artifact_subset.json).
# The captured stream is replayed on the host through the installed library at -n 1 and the new one at
# N = 1, 16 and 16 with every drain threaded; co_json_diff.py compares (same-stream parity: must be 0),
# plus replay fidelity (installed replay vs the live run that produced the stream) and, for context
# only, the live run and X11's three -n 1 recordings against each other.
# KMAX_<app>=k: capture only the first k kernels (CAP_MAX_KERNELS; the run goes on) when the whole stream would not
# fit on the node's disk (~300 B per record: knn 11.8 G records, tridiagonal 5.6 G).
#   [APPS="mr crs fpc dxtc2"] [KMAX_knn=20] sbatch -o <W>/eval/x_logs/t26-sc-%j.log sc.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
SELF=$W/eval/baselines/setup/t26_parity/sc.sh
X12W=/home/fzheng4/wt/x12
SIF=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/ubuntu2204.sif
SING=/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity
SCBIN=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/supercollider-artifacts/bin/hecbench/native

if [ "${1:-}" = inner ]; then
  # ---- inside ubuntu2204.sif: record each app once through the capture shim -------------------------
  for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|CAP\)_[A-Z0-9_]*'); do unset $v; done
  export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
  export X11_CUDART=$CUDA_HOME/lib64/libcudart.so.13
  [ -e "$X11_CUDART" ] || { echo "no $X11_CUDART"; exit 4; }
  APHD=$ROOT/aph; rm -rf $APHD; mkdir -p $APHD/bin
  for e in $CAPH/* $CAPH/.env; do n=$(basename $e); [ $n = bin ] || ln -sfn $(readlink -f $e) $APHD/$n; done
  for e in $CAPH/bin/*; do ln -sfn $(readlink -f $e) $APHD/bin/$(basename $e); done
  rm $APHD/bin/accelprof
  sed 's#LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE}#LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE}#' $CAPH/bin/accelprof > $APHD/bin/accelprof
  chmod +x $APHD/bin/accelprof
  echo "accelprof lines changed: $(diff $CAPH/bin/accelprof $APHD/bin/accelprof | grep -c '^>') lib -> $(readlink $APHD/lib)"
  export ACCEL_PROF_HOME=$APHD CUVEIN_HOME=$APHD
  export PATH=$APHD/bin:$CUDA_HOME/bin:$PATH
  # append: singularity --nv puts the host driver (/.singularity.d/libs) on LD_LIBRARY_PATH
  export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$CUDA_HOME/compute-sanitizer:$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
  echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
  TREE=$ROOT/tree
  $PY $X12W/eval/x12/x12_mktree.py $TREE $(echo $APPS | tr ' ' ,) || exit 3
  # git for accelprof's VERSION line, as X11/X12 (their shim)
  mkdir -p $ROOT/shim; cp /home/fzheng4/wt/x12/eval/x12/shim/git $ROOT/shim/git; export PATH=$ROOT/shim:$PATH
  for app in $APPS; do
    args=$($PY -c "import csv,sys; print([r for r in csv.DictReader(open(sys.argv[1])) if r['id']=='X11-'+sys.argv[2]][0]['args'])" $TREE/manifest.csv $app)
    capd=$ROOT/cap/$app; rm -rf $capd; mkdir -p $capd
    cwd=$TREE/src/$app-cuda
    t0=$(date +%s%N)
    kv=KMAX_$app; km=${!kv:-}
    ( cd $cwd && env CAP_REAL_LIB=$LIB_INST CAP_DIR=$capd ${km:+CAP_MAX_KERNELS=$km} accelprof -v -t pc_dependency_analysis -n 1 ./$app $args \
        > $ROOT/live-$app.out 2> $ROOT/live-$app.err ); rc=$?
    t1=$(date +%s%N)
    mkdir -p $OUT/$app/live
    cp $ROOT/live-$app.out $ROOT/live-$app.err $OUT/$app/ 2>/dev/null; cp $cwd/*.accelprof.log $OUT/$app/ 2>/dev/null
    n=0; for kj in $cwd/dependency_${app}_*/kernel_*.json; do [ -f "$kj" ] && { mv $kj $OUT/$app/live/; n=$((n+1)); }; done
    rm -rf $cwd/dependency_${app}_*
    echo "== $app: args [$args] ${km:+CAP_MAX_KERNELS=$km }rc=$rc wall=$(( (t1 - t0) / 1000000 )) ms kernels=$n binary=$(sha256sum $cwd/$app | cut -c1-16) captures=$(ls $capd | wc -l) bytes=$(du -cb $capd/cap.*.bin 2>/dev/null | tail -1 | cut -f1)"
    grep -h "t26-capture" $ROOT/live-$app.err $cwd/*.accelprof.log 2>/dev/null | tail -2 | sed 's/^/   /'
  done
  exit 0
fi

# ---- host -------------------------------------------------------------------------------------------
source $W/eval/baselines/setup/t26_parity/common.sh
for d in $INST /mnt/beegfs/$USER; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
export REPLAY_BIN=${REPLAY_BIN:-$S/bin/t26_replay2}
APPS=${APPS:-mr crs fpc dxtc2}
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} apps=[$APPS] $(date -Is)"
mkcaph; runtime_line
LOC=/mnt/local/$USER; [ -d $LOC ] && [ -w $LOC ] || LOC=/tmp
ROOT=$LOC/t26-sc-${SLURM_JOB_ID:-x}; OUT=/mnt/beegfs/$USER/t26/sc-${SLURM_JOB_ID:-x}
mkdir -p $ROOT $OUT
echo "store=$OUT work=$ROOT ($(df -h $LOC | tail -1 | awk '{print $4}') free)"
env -u LD_LIBRARY_PATH -u LD_PRELOAD ROOT=$ROOT OUT=$OUT CAPH=$CAPH LIB_INST=$LIB_INST APPS="$APPS" PY=$INST/.env/bin/python \
    $SING exec --nv --bind /mnt/beegfs,/opt,/usr/local${LOC:+,$LOC} $SIF bash $SELF inner
echo "== capture done rc=$? $(date -Is)"
X11=/mnt/beegfs/$USER/cuvein_traces
cmp1() { $PY $DIFF "$1" "$2" --label "$3" --quiet --json $ROOT/diff.json; local rc=$?
         [ $rc -ne 0 ] && [ -f $ROOT/diff.json ] && { mkdir -p $OUT/diffs; cp $ROOT/diff.json "$OUT/diffs/$(echo $3 | tr -c 'A-Za-z0-9' _).json"; }; rm -f $ROOT/diff.json; }
for app in $APPS; do
  echo "== $app $(date -Is)"
  cap=$(ls -S $ROOT/cap/$app/cap.*.bin 2>/dev/null | head -1)
  [ -n "$cap" ] || { echo "  no capture"; continue; }
  echo "  capture $(stat -c %s $cap) bytes ($(ls $ROOT/cap/$app/cap.*.bin | wc -l) files, largest replayed)"
  for r in inst n1 n16 n16t; do
    case $r in inst) replay $cap $ROOT/r/$app/inst inst 1;; n1) replay $cap $ROOT/r/$app/n1 new 1;;
               n16) replay $cap $ROOT/r/$app/n16 new 16;; n16t) replay $cap $ROOT/r/$app/n16t new 16 0;; esac
    echo "  replay $r: $(grep -h 't26_replay\]\|rc=' $ROOT/r/$app/$r/replay.err | sed "s|$ROOT/cap/||" | tr '\n' ' ')"
    dp=$(depdir $ROOT/r/$app/$r); [ -n "$dp" ] && { mkdir -p $OUT/$app/$r; cp $dp/kernel_*.json $OUT/$app/$r/; }
  done
  for r in n1 n16 n16t; do cmp1 $OUT/$app/inst $OUT/$app/$r "$app same-stream: installed -n1 vs new $r"; done
  kv=KMAX_$app; km=${!kv:-}
  if [ -n "$km" ]; then   # prefix stream: compare the live run's first $km kernels only; no X11 context
    mkdir -p $OUT/$app/live-prefix
    for f in $OUT/$app/live/kernel_*.json; do i=$(basename $f .json); i=${i#kernel_}; [ $i -lt $km ] && ln -sfn $f $OUT/$app/live-prefix/; done
    cmp1 $OUT/$app/inst $OUT/$app/live-prefix "$app fidelity: installed replay vs live first $km kernels (installed -n1 via shim)"
    rm -rf $ROOT/r/$app $ROOT/cap/$app; continue
  fi
  cmp1 $OUT/$app/inst $OUT/$app/live "$app fidelity: installed replay vs live (installed -n1 via shim)"
  xd() { local d=$X11/x11-co-r$1-$app/X11-$app/collector-only; [ -d $d ] || d=$X11/x11-co-r$1/X11-$app/collector-only; echo $d; }
  for i in 1 2 3; do cmp1 $(xd $i) $OUT/$app/live "$app context: X11 r$i vs this live run"; done
  cmp1 $(xd 1) $(xd 2) "$app context: X11 r1 vs r2"; cmp1 $(xd 1) $(xd 3) "$app context: X11 r1 vs r3"
  rm -rf $ROOT/r/$app $ROOT/cap/$app
done
rm -rf $ROOT
echo "== done $(date -Is)"

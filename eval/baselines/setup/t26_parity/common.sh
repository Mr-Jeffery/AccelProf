# T26 parity: shared settings for the fixture and T20-id parity jobs (sourced).
#   INST  the installed runtime (read only)          NEWH  the worktree runtime (lib -> stage-t26/rt-lib)
#   CAPH  the capture home: a symlink farm whose lib/ holds the collector relinked against the capture
#         shim; CAP_REAL_LIB picks the analyzer it forwards to (installed or new), CAP_DIR the stream dir
W=${W:-/home/fzheng4/wt/sharded-pcdep}; INST=/home/fzheng4/AccelProf; S=${S:-/home/fzheng4/stage-t26}
NEWH=$W; CAPH=$S/caphome
LIB_INST=$INST/build/sanalyzer/lib/libsanalyzer.so
LIB_NEW=$S/san-install/lib/libsanalyzer.so
PY=$W/.env/bin/python
DIFF=$W/eval/baselines/setup/co_json_diff.py
export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$CUDA_HOME/compute-sanitizer:$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
# no detector knob from the submitting shell: collector-only mode is "no YOSEMITE_HB_* at all"
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\|CAP\)_[A-Z0-9_]*'); do unset $v; done
h() { sha256sum "$1" | cut -c1-16; }
mkcaph() {
  mkdir -p $CAPH
  ln -sfn $INST/bin $CAPH/bin; ln -sfn $INST/nv-compute $CAPH/nv-compute; ln -sfn $INST/build $CAPH/build
  ln -sfn $S/cap-rt-lib $CAPH/lib; ln -sfn $W/python $CAPH/python
  ln -sfn $W/eval $CAPH/eval; ln -sfn $INST/.env $CAPH/.env      # the harness's imports and sidecar python
}
runtime_line() {
  echo "installed: libsanalyzer $(h $LIB_INST) collector $(h $INST/lib/libcompute_sanitizer.so) HEAD $(git -C $INST rev-parse --short=12 HEAD)"
  echo "new: libsanalyzer $(h $LIB_NEW) collector $(h $NEWH/lib/libcompute_sanitizer.so) worktree HEAD $(git -C $W rev-parse --short=12 HEAD) dirty $(git -C $W status --porcelain -uno | wc -l)"
  echo "capture: shim $(h $S/cap-lib/libsanalyzer.so) collector $(h $CAPH/lib/libcompute_sanitizer.so) replay $(h $S/bin/t26_replay)"
  echo "fatbin $(h $INST/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"
}
# replay <cap.bin> <outdir> <lib: inst|new> <N> [inline_max]: the tool's kernel JSONs land in <outdir>/dependency_*
replay() {
  local cap=$1 out=$2 which=$3 n=$4 im=${5:-}
  local ld=$S/san-install/lib
  [ "$which" = inst ] && ld=$INST/build/sanalyzer/lib
  mkdir -p $out
  ( cd $out && env YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_APP_NAME=replay \
      YOSEMITE_WORKER_COUNT=$n ${im:+YOSEMITE_PCDEP_INLINE_MAX=$im} ${REPLAY_ENV:-} \
      LD_LIBRARY_PATH=$ld:$LD_LIBRARY_PATH ${REPLAY_BIN:-$S/bin/t26_replay} $cap > replay.out 2> replay.err; echo "rc=$?" >> replay.err )
}
depdir() { ls -d $1/dependency_* 2>/dev/null | head -1; }

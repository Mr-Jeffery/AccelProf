#!/usr/bin/env bash
# B3 iGUARD (SOSP'21) build -- hard 3-hour box. Run on a GPU node (nvcc + NVBit).
#   sbatch -p rtx4060ti16g -N1 -n1 -t 03:00:00 -o build_logs/iguard_setup-%j.log \
#       eval/baselines/setup/iguard_setup.sh
#
# Root cause of the previous BUILD-BLOCKED record: the box invoked
# `make ARCH=89`, but iGUARD's detector Makefile passes `-arch=$(ARCH)` straight to
# nvcc, which needs `sm_89` (error was literally "Unsupported gpu architecture
# '89'"). Second, real constraint: iGUARD pins NVBit 1.7.4 (driver <= 555.xx) while
# the nodes run driver 580.82.07 / CUDA 13.3, so the newest NVBit is used instead
# (1.8: CUDA 13.2 headers; fallbacks 1.7.7.3, 1.7.6). Any detector-source edit
# needed for the newer NVBit API is recorded as a diff in setup/iguard_diffs/.
# On failure the exact command + error is kept verbatim in setup/iguard.status.
set -u
REPO=/home/fzheng4/AccelProf
cd "$REPO/eval/baselines/setup" || exit 1
source "$REPO/eval/baselines/gpu_env.sh"
[ -f "$PWD/spack_env.sh" ] && . "$PWD/spack_env.sh" 2>/dev/null   # README deps if present
DEST="$PWD/iguard"; mkdir -p "$DEST"
STATUS="$PWD/iguard.status"; : > "$STATUS"
DIFFS="$PWD/iguard_diffs"; mkdir -p "$DIFFS"
log(){ echo "$@" | tee -a "$STATUS"; }
WORK="$PWD/tools"; mkdir -p "$WORK"
SRC="$WORK/iGUARD-SOSP21"
ARCH="${IGUARD_ARCH:-sm_89}"
log "iguard_setup $(date -Is) node=$(hostname) CUDA=$CUDA_HOME nvcc=$(nvcc --version | tail -1) driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1) arch=$ARCH"
if [ ! -d "$SRC/.git" ]; then
  log "\$ git clone --depth 1 https://github.com/csl-iisc/iGUARD-SOSP21 $SRC"
  git clone --depth 1 https://github.com/csl-iisc/iGUARD-SOSP21 "$SRC" 2>>"$STATUS" || { log "FAIL: clone"; exit 3; }
fi
cd "$SRC" || exit 3
log "iGUARD commit: $(git rev-parse --short HEAD)"
# keep the pristine detector for diffing
[ -d "$WORK/iguard_detector_orig" ] || cp -r detector "$WORK/iguard_detector_orig"

try_nvbit() {  # $1 = version tag (e.g. 1.8), $2 = optional CUDA_HOME override
  local ver="$1" cuda="${2:-}"
  local tb="nvbit-Linux-x86_64-${ver}.tar.bz2"
  local url="https://github.com/NVlabs/NVBit/releases/download/v${ver}/${tb}"
  log "=== attempt NVBit $ver ${cuda:+CUDA_HOME=$cuda}"
  if [ ! -f "$WORK/$tb" ]; then
    log "\$ wget -q $url"
    wget -q -O "$WORK/$tb" "$url" 2>>"$STATUS" || { log "FAIL: download $tb"; rm -f "$WORK/$tb"; return 1; }
  fi
  log "sha256 $(sha256sum "$WORK/$tb" | cut -c1-16)... $tb"
  rm -rf nvbit_release nvbit_release_x86_64
  tar -xf "$WORK/$tb" || { log "FAIL: untar $tb"; return 1; }
  # newer tarballs extract to nvbit_release_x86_64/, older to nvbit_release/
  [ -d nvbit_release ] || { d=$(ls -d nvbit_release* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" nvbit_release; }
  [ -d nvbit_release/core ] || { log "FAIL: no nvbit_release/core after untar ($(ls -d nvbit* | tr '\n' ' '))"; return 1; }
  grep -E "NVBit|driver|CUDA version" nvbit_release/README.md 2>/dev/null | head -6 | sed 's/^/    /' | tee -a "$STATUS"
  mkdir -p nvbit_release/tools; rm -rf nvbit_release/tools/detector; cp -r detector nvbit_release/tools/
  if [ -n "$cuda" ]; then
    export PATH="$cuda/bin:$PATH" CUDA_HOME="$cuda"
  fi
  local mlog="$WORK/iguard_make_${ver}.log"
  log "\$ (cd nvbit_release/tools/detector && make ARCH=$ARCH)   # output: $mlog"
  if ( cd nvbit_release/tools/detector && make ARCH="$ARCH" ) >"$mlog" 2>&1; then
    local so=nvbit_release/tools/detector/detector.so
    if [ -f "$so" ]; then
      cp "$so" "$DEST/iguard.so"
      echo "nvbit=$ver arch=$ARCH cuda=${cuda:-$CUDA_HOME} commit=$(git rev-parse --short HEAD) built=$(date -Is)" > "$DEST/iguard.version"
      log "OK -> $DEST/iguard.so (NVBit $ver, $ARCH)"
      # record any detector edits vs pristine
      ( cd "$WORK" && diff -ru iguard_detector_orig "$SRC/detector" > "$DIFFS/detector.diff" ); [ -s "$DIFFS/detector.diff" ] && log "detector diff recorded: $DIFFS/detector.diff" || rm -f "$DIFFS/detector.diff"
      return 0
    fi
    log "FAIL: make ok but no detector.so"; return 1
  fi
  log "FAIL: make (NVBit $ver) -- error lines from $mlog:"
  grep -E "error|Error|fatal|undefined" "$mlog" | head -12 | sed 's/^/    /' | tee -a "$STATUS"
  return 1
}

try_nvbit 1.8      && exit 0
try_nvbit 1.7.7.3  && exit 0
try_nvbit 1.7.6    && exit 0
try_nvbit 1.7.5 /usr/local/cuda-12.9 && exit 0
log "BLOCKED: every NVBit attempt failed (see above; verbatim make output in $STATUS)"
exit 3

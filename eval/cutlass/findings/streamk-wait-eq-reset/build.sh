#!/usr/bin/env bash
# Build repro / repro_fixed / repro_perturb for the stream-K wait_eq_reset finding.
# Usage: build.sh [outdir]   (run from anywhere; repro.cu, fix.patch, perturb.patch must sit next to this script)
# Env:   CUTLASS (default: ARC v4.8.1 tree), NVCC (default: /usr/local/cuda-13.3/bin/nvcc)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUTLASS="${CUTLASS:-/mnt/beegfs/fzheng4/cutlass/src/cutlass-v4.8.1}"
NVCC="${NVCC:-/usr/local/cuda-13.3/bin/nvcc}"
OUT="${1:-$HERE/build}"
mkdir -p "$OUT"
"$NVCC" --version | tail -n 2
FLAGS=(-arch=sm_89 -lineinfo -std=c++17 -O3 -cudart shared)   # never -G; shared cudart: the collector resolves cudart symbols at run time

# overlay <name> <patch>: $OUT/overlay_<name>/cutlass/barrier.h = patched copy of the tag's barrier.h
overlay() {
  local d="$OUT/overlay_$1"
  rm -rf "$d" && mkdir -p "$d/cutlass"
  cp "$CUTLASS/include/cutlass/barrier.h" "$d/cutlass/barrier.h"
  patch --no-backup-if-mismatch "$d/cutlass/barrier.h" < "$HERE/$2" >&2
  echo "$d"
}

build() {  # build <exe> [extra include dirs placed before CUTLASS]
  local exe="$1"; shift
  "$NVCC" "${FLAGS[@]}" "$@" -I "$CUTLASS/include" -I "$CUTLASS/tools/util/include" \
    -o "$OUT/$exe" "$HERE/repro.cu"
  "$NVCC" "${FLAGS[@]}" "$@" -I "$CUTLASS/include" -I "$CUTLASS/tools/util/include" \
    -cubin -o "$OUT/$exe.cubin" "$HERE/repro.cu"
  echo "built $OUT/$exe"
}

build repro
build repro_fixed   -I "$(overlay fixed fix.patch)"
build repro_perturb -I "$(overlay perturb perturb.patch)"

# Sanity: the fixed binary must contain a GPU-scope membar right after the CAS spin; stock must not.
CUOBJDUMP="$(dirname "$NVCC")/cuobjdump"
if [ -x "$CUOBJDUMP" ]; then
  for exe in repro repro_fixed repro_perturb; do
    "$CUOBJDUMP" -sass "$OUT/$exe.cubin" > "$OUT/$exe.sass"
    printf '%-14s ATOMG.CAS=%s  CAS->MEMBAR.ALL.GPU within 6 instrs (12 dump lines)=%s  NANOSLEEP=%s\n' "$exe" \
      "$(grep -c 'ATOMG.E.CAS' "$OUT/$exe.sass" || true)" \
      "$(grep -A12 'ATOMG.E.CAS' "$OUT/$exe.sass" | grep -c 'MEMBAR' || true)" \
      "$(grep -c 'NANOSLEEP' "$OUT/$exe.sass" || true)"
  done
fi

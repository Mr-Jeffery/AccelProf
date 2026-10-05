#!/bin/bash
# Step 2: build NVBit's tools/mem_trace unchanged for each downloaded release.
# Usage (inside the allocation): srun --jobid=<J> bash eval/nvbit_spike/build_mem_trace.sh
source "$(dirname "$0")/env.sh"
for d in "$NVBIT_ROOT/1.8/nvbit_release_x86_64" "$NVBIT_ROOT/1.7.1/nvbit_release"; do
  echo "=== $d"
  grep -m1 NVBIT_VERSION "$d/core/nvbit.h"
  ( cd "$d/tools/mem_trace" && make clean >/dev/null && make ARCH=sm_89 2>&1 | tail -5 )
  ls -la "$d/tools/mem_trace/mem_trace.so" 2>&1
done

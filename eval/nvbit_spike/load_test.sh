#!/bin/bash
# Step 2: load test of the unchanged mem_trace on the rtraw litmus binary.
# LD_PRELOAD is set directly on the app (never through timeout/env: NVBit strips
# LD_PRELOAD from the first process it sees).
source "$(dirname "$0")/env.sh"
APP=/home/fzheng4/AccelProf/ScoR/microbenchmarks/bin/race_interblock_fence_rtraw
OUT=$WORK/load_test; mkdir -p "$OUT"
echo "--- native"; "$APP" > "$OUT/native.txt" 2>&1; echo "rc=$?"; tail -3 "$OUT/native.txt"
for v in 1.8:1.8/nvbit_release_x86_64 1.7.1:1.7.1/nvbit_release; do
  ver=${v%%:*}; so=$NVBIT_ROOT/${v#*:}/tools/mem_trace/mem_trace.so
  echo "--- mem_trace $ver"
  LD_PRELOAD=$so "$APP" > "$OUT/mem_trace_$ver.txt" 2>&1; echo "rc=$?"
  grep -c '^MEMTRACE: CTX' "$OUT/mem_trace_$ver.txt" | sed 's/^/memtrace lines: /'
  grep -i -E 'nvbit|warn|error|fail' "$OUT/mem_trace_$ver.txt" | grep -v '^MEMTRACE: CTX' | head -8
  grep -m2 'LAUNCH' "$OUT/mem_trace_$ver.txt"
  grep -m3 'MEMTRACE: CTX.*grid_launch_id' "$OUT/mem_trace_$ver.txt" | cut -c1-200
done

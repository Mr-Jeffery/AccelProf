#!/bin/bash
# Step 3: build atom_after (against NVBit 1.8) and the test kernel; dump the
# test kernel's SASS so the atomic lowering is on record.
source "$(dirname "$0")/env.sh"
set -e
cd "$SPIKE/atom_after"
make clean >/dev/null
make ARCH=sm_89 2>&1 | grep -v '^nvcc\|^bin2c\|^rm ' || true
ls -la atom_after.so
cd "$SPIKE"
nvcc -O3 -arch=sm_89 -lineinfo -o "$WORK/atom_values" atom_values.cu
cuobjdump -sass "$WORK/atom_values" | grep -E 'Function|ATOM|RED|MEMBAR|CCTL' > "$WORK/atom_values.sass.txt"
cat "$WORK/atom_values.sass.txt"

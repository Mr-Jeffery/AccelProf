#!/bin/bash
# Assemble driver_buggy.cu and driver_fixed.cu (login node).  The kernels live in the cub TEST file, which the fix commit
# changed (two lines: a __syncthreads() after the read of tile_data[tile_idx]), so each variant has its own driver.
# Per variant: the licence header (lines 1-26) and the two kernels (lines 38-97 at the buggy commit, 38-99 at the fix
# commit) are copied verbatim from cub/test/catch2_test_device_decoupled_look_back.cu at that commit; the main is ours
# (main_part.cu, identical for both).  The script prints the diff of the two excerpts next to the fix commit's diff.
set -e
here=$(cd "$(dirname "$0")" && pwd)
repo=/home/fzheng4/incoming/realworld/cccl.git
f=cub/test/catch2_test_device_decoupled_look_back.cu
B=45f868f38fdf7a5e9746aa4074bf7da0c730a330; F=5dad0bff89d79d1bffb557f47eaa7a2229b3ae79
gen() {  # variant sha last_line
  { git -C $repo cat-file -p $2:$f | sed -n 1,26p
    printf '\n// T21a driver for cccl-4 (%s): the two kernels below (lines 38-%s of %s at %s) are verbatim.\n#undef NDEBUG\n#include <cub/device/device_scan.cuh>\n\n#include <cassert>\n\n' "$1" "$3" "$f" "$2"
    git -C $repo cat-file -p $2:$f | sed -n 38,$3p
    cat "$here/main_part.cu"; } > "$here/driver_$1.cu"
  git -C $repo cat-file -p $2:$f | sed -n 38,$3p > "/tmp/k_$1.$$"
}
gen buggy $B 97
gen fixed $F 99
echo "excerpt diff buggy -> fixed:"; diff /tmp/k_buggy.$$ /tmp/k_fixed.$$ || true
echo "fix commit diff of the test file:"; git -C $repo diff $B $F -- $f | grep -E '^@@|^[+-][^+-]'
rm -f /tmp/k_buggy.$$ /tmp/k_fixed.$$ "$here/driver.cu"

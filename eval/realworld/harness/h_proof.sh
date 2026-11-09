#!/bin/bash
# R1h proof (T21a step 2): the checkout's CCCL headers, not the toolkit's bundled ones, are the ones the compiler used.
# nvcc has no -H of its own: the log is `nvcc -Xcompiler -H ... -c` (the host compiler's include tree, stderr).
#   h_proof.sh <log with `nvcc -H` output> <checkout dir>      exit 0 iff >=1 header came from the checkout and none from the toolkit's CCCL
log=$1; ck=${2%/}
sed -nE 's/^\.+ (\/.*)$/\1/p' "$log" | sort -u > "$log.headers"
n_all=$(wc -l < "$log.headers")
n_ck=$(grep -c "^$ck/" "$log.headers")
n_tk=$(grep -v "^$ck/" "$log.headers" | grep -cE "/include/cccl/|/include/(cub|thrust)/|/include/cuda/(std|__)|/include/nv/(target|detail)")
n_ck_cccl=$(grep -E "^$ck/" "$log.headers" | grep -cE '/(cub|thrust|libcudacxx/include/(cuda|nv))/')
echo "h_proof: $n_all distinct headers; $n_ck from $ck ($n_ck_cccl CCCL: cub/thrust/libcudacxx); $n_tk from the toolkit's CCCL"
grep -E "^$ck/" "$log.headers" | head -3 | sed 's/^/  checkout: /'
grep -v "^$ck/" "$log.headers" | grep -E "/include/cccl/|/include/(cub|thrust)/|/include/cuda/(std|__)" | head -5 | sed "s/^/  TOOLKIT CCCL: /"
[ "$n_ck_cccl" -gt 0 ] && [ "$n_tk" -eq 0 ] && { echo "RESULT PASS"; exit 0; } || { echo "RESULT FAIL"; exit 1; }

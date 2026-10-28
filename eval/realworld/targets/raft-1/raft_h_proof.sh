#!/bin/bash
# R1h proof for raft-1 (raft is not a CCCL target): the raft headers the compiler used are the checkout's, and the kernel header
# select_radix.cuh is the checkout's file.   raft_h_proof.sh <log with `nvcc -Xcompiler -H` output> <$SRC>
# exit 0 iff: >=1 raft header from $SRC/raft/cpp/include, select_radix.cuh among them, and no raft/rmm/rapids_logger header from anywhere else.
log=$1; sd=${2%/}
sed -nE 's/^\.+ (\/.*)$/\1/p' "$log" | sort -u > "$log.headers"
n_all=$(wc -l < "$log.headers")
n_raft=$(grep -c "^$sd/raft/cpp/include/raft/" "$log.headers")
n_rmm=$(grep -c "^$sd/deps/rmm/cpp/include/rmm/" "$log.headers")
n_rlog=$(grep -c "^$sd/deps/rapids-logger/include/rapids_logger/" "$log.headers")
n_gen=$(grep -c "/gen/\(raft\|rmm\)/" "$log.headers")
n_radix=$(grep -c "^$sd/raft/cpp/include/raft/matrix/detail/select_radix.cuh$" "$log.headers")
# a raft/rmm/rapids_logger header resolved outside the checkout (e.g. an installed copy): must be none
n_foreign=$(grep -E "/(raft|rmm|rapids_logger)/[^/]+$|/(raft|rmm|rapids_logger)/" "$log.headers" | grep -v "^$sd/" | grep -vc "/gen/\(raft\|rmm\)/")
n_tk_cccl=$(grep -cE "/include/cccl/" "$log.headers")
echo "raft_h_proof: $n_all distinct headers: $n_raft raft + $n_rmm rmm + $n_rlog rapids_logger from the checkout tree $sd, $n_gen generated (raft/rmm), $n_tk_cccl toolkit CCCL (expected: raft is not a CCCL target)"
echo "  select_radix.cuh from checkout: $n_radix; raft/rmm/rapids_logger headers from outside the checkout: $n_foreign"
grep -E "^$sd/raft/" "$log.headers" | grep -E "select_(k|radix)" | head -4 | sed 's/^/  checkout: /'
grep -E "/(raft|rmm|rapids_logger)/" "$log.headers" | grep -v "^$sd/" | grep -v "/gen/" | head -5 | sed 's/^/  FOREIGN: /'
{ [ "$n_raft" -gt 0 ] && [ "$n_radix" -eq 1 ] && [ "$n_foreign" -eq 0 ]; } && { echo "RESULT PASS"; exit 0; } || { echo "RESULT FAIL"; exit 1; }

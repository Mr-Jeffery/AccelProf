#!/usr/bin/env bash
# T10: which SASS do the strong load/store forms lower to on this toolchain? Compiles
# lowering_probe.cu for sm_89 and prints its memory instructions (eval/SIDECAR_STRENGTH.md,
# "Lowering"). Run on a GPU node (nvcc is not on the login node):
#   srun -n 1 -p rtx4060ti16g -x c54,c2 --time=00:15:00 bash eval/baselines/setup/t10_lowering/lowering_probe.sh
set -e
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/usr/local/cuda-13.3/bin:$PATH
nvcc --version | tail -2
nvcc -arch=sm_89 -lineinfo -cubin -o /tmp/t10_lowering_probe.$$.cubin "$D/lowering_probe.cu"
nvdisasm -c /tmp/t10_lowering_probe.$$.cubin | grep -E "LD|ST|ATOM|RED|MEMBAR|CCTL|FENCE" | sed 's/^ *//'
rm -f /tmp/t10_lowering_probe.$$.cubin

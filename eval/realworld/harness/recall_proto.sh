#!/bin/bash
# T21b prototype job: the runtime hashes, which CUDA_HOME works, the nvdisasm line-info format, one tiny target
# end to end (cccl-1 buggy and fixed) under each toolkit that exists. Output only into the proto store.
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
echo "host=$(hostname) $(date -Is) nproc=$(nproc)"
ls -d /usr/local/cuda* 2>&1
readlink -f /usr/local/cuda
nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader
for CH in /usr/local/cuda-13.3 /usr/local/cuda-13.4; do
  echo "##### CUDA_HOME=$CH"
  [ -d $CH/bin ] || { echo "absent"; continue; }
  $CH/bin/nvcc --version | tail -2
  ls $CH/compute-sanitizer/ | head -5
  RW_CUDA_HOME=$CH FLAVOR=proto PROTO_STORE=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-proto/$(basename $CH) \
     IDS="cccl-1-buggy cccl-1-fixed" bash $W/eval/realworld/harness/recall_job.sh
  echo "rc=$?"
done
echo "##### nvdisasm samples"
export CUDA_HOME=/usr/local/cuda-13.3; [ -d $CUDA_HOME/bin ] || export CUDA_HOME=/usr/local/cuda-13.4
export PATH=$CUDA_HOME/bin:$PATH
T=$(mktemp -d /tmp/proto-XXXXXX); cd $T
cuobjdump -xelf all /mnt/beegfs/fzheng4/realworld/build/cccl-1/buggy/driver > /dev/null 2>&1
ls | head
nvdisasm --help | grep -i -B1 -A3 -E "line-info|function|print-instr|-gi\b"
C=$(ls *.cubin | head -1)
nvdisasm -lfun $C 2>&1 | head -10
F=$(nvdisasm -lfun $C 2>&1 | grep -i block_reduce | head -1 | tr -d ' ')
echo "func=$F"
for flag in --print-line-info --print-line-info-inline; do
  echo "----- $flag --function"
  nvdisasm $flag --function "$F" $C 2>&1 | grep -n -E "^\s*(//##|/\*[0-9a-f]{4,}\*/)|\.type|^[._A-Za-z0-9]+:" | head -70
done
rm -rf $T

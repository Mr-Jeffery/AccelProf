#!/bin/bash
# T21a GPU node: one sm_89 node held (native runs, nsys reach check, compute-sanitizer racecheck run as job steps inside it,
# see hrun.sh).  Single-GPU rtx4060ti8g nodes first (T21 rule); dual-GPU c21/c22/c34 excluded unless CUDA_VISIBLE_DEVICES is pinned.
# Stops itself when eval/x_logs/HOLD_GPU_STOP exists or at the time limit.
source ${T21_WT:-/home/fzheng4/wt-t21a}/eval/realworld/harness/job_header.sh
cc=$(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | head -3)
echo "GPUs: $cc"
echo "$cc" | grep -q ", 8.9$" || { echo "not an sm_89 node: $(hostname)" >&2; exit 98; }
echo "cuda: $(readlink -f /usr/local/cuda) sanitizer: $(compute-sanitizer --version 2>&1 | tail -1)"
ls /opt/nvidia/nsight-systems/*/bin/nsys 2>&1 | tail -1
echo "--- holding"
while [ ! -e "$WT/eval/x_logs/HOLD_GPU_STOP" ]; do sleep 30; done

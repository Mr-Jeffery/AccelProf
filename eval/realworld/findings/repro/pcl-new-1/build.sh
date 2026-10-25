#!/bin/bash
# Build the pcl-new-1 reproducers (sm_89, CUDA 13.4).  Run from this directory.
set -e
export PATH=/usr/local/cuda-13.4/bin:$PATH
cd "$(dirname "$0")"
for f in repro repro_fixed repro_perturb; do
  nvcc -arch=sm_89 -lineinfo --cudart shared -O3 -o $f $f.cu
done

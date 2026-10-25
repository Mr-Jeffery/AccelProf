#!/bin/bash
# llmc-new-3-2: build the three reproducers (CUDA 13.4, sm_89). Usage: bash build.sh   (binaries land next to the sources)
set -e
cd "$(dirname "$0")"
export PATH=/usr/local/cuda-13.4/bin:$PATH
for f in repro repro_fixed repro_perturb; do
  nvcc -arch=sm_89 -lineinfo --cudart shared -O3 -o $f $f.cu
done

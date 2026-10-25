#!/bin/bash
# Builds the three reproducers next to this script (CUDA 13.4 on ARC: export PATH=/usr/local/cuda-13.4/bin:$PATH).
set -e
cd "$(dirname "$0")"
nvcc -arch=sm_89 -lineinfo --cudart shared -O3 -o repro repro.cu
nvcc -arch=sm_89 -lineinfo --cudart shared -O3 -o repro_fixed repro_fixed.cu
nvcc -arch=sm_89 -lineinfo --cudart shared -O3 -o repro_perturb repro_perturb.cu

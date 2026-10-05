#!/usr/bin/env bash
# Shared environment for GPU-node runs of the baseline harness. Source this at the
# top of any srun invocation. Home is NFS (shared login<->compute); CUDA lives on
# the compute node only. See project memory 'accelprof-build-env'.
#
#   srun -p rtx3060ti -N1 -n1 -t 04:00:00 bash -c 'source eval/baselines/gpu_env.sh; ...'
export ACCEL_PROF_HOME="${ACCEL_PROF_HOME:-/home/fzheng4/AccelProf}"
export CUVEIN_HOME="$ACCEL_PROF_HOME"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export CUDA_PATH="$CUDA_HOME"
export PATH="$ACCEL_PROF_HOME/bin:$CUDA_HOME/bin:$PATH"
# compute-sanitizer/ carries libsanitizer-public.so (the detector lib needs it);
# torch/lib carries libtorch (tensor_scope dependency of the CS backend).
TORCH_LIB="/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/lib"
export LD_LIBRARY_PATH="$CUDA_HOME/compute-sanitizer:$CUDA_HOME/lib64:$TORCH_LIB:$LD_LIBRARY_PATH"
export PY="$ACCEL_PROF_HOME/.env/bin/python"

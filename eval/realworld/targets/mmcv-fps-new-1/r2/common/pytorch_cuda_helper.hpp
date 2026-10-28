// T21c include shim (not an upstream file): mmcv's pytorch_cuda_helper.hpp pulls in torch/extension.h and the ATen CUDA headers; the two
// furthest-point-sampling kernels in furthest_point_sample_cuda_kernel.cuh use nothing from it but CUDA's own min()/max() device builtins.
#pragma once
#include <cuda.h>
#include <cuda_runtime.h>

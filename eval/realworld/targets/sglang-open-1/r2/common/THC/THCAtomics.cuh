// Include shim (T21c sglang-open-1): THC/THCAtomics.cuh was removed from PyTorch (2.x); it only provided atomicAdd overloads for
// at::Half / at::BFloat16 etc.  moe_align_kernel.cu uses atomicAdd on int32_t only, which is a CUDA builtin.
#pragma once

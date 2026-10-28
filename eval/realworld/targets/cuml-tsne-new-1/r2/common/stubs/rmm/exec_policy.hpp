// R2 stub (T21c): rmm::exec_policy(stream) -> thrust's CUDA policy on that stream.
#pragma once
#include <thrust/execution_policy.h>
#include <cuda_runtime.h>
namespace rmm {
inline auto exec_policy(cudaStream_t stream = 0) { return thrust::cuda::par.on(stream); }
}  // namespace rmm

// R2 stub (T21c): RAFT_CUDA_TRY, raft::copy, raft::getMultiProcessorCount.
#pragma once
#include <raft/core/error.hpp>
#include <cuda_runtime.h>
#include <cstddef>
#define RAFT_CUDA_TRY(call)                                                                               \
  do {                                                                                                    \
    cudaError_t const _status = (call);                                                                   \
    if (_status != cudaSuccess) {                                                                         \
      RAFT_FAIL("CUDA error encountered at %s:%d: %s", __FILE__, __LINE__, cudaGetErrorString(_status));  \
    }                                                                                                     \
  } while (0)
namespace raft {
template <typename T>
void copy(T* dst, const T* src, std::size_t n, cudaStream_t stream)
{
  RAFT_CUDA_TRY(cudaMemcpyAsync(dst, src, n * sizeof(T), cudaMemcpyDefault, stream));
}
inline int getMultiProcessorCount()
{
  int dev = 0, n = 0;
  RAFT_CUDA_TRY(cudaGetDevice(&dev));
  RAFT_CUDA_TRY(cudaDeviceGetAttribute(&n, cudaDevAttrMultiProcessorCount, dev));
  return n;
}
}  // namespace raft

// R2 stub (T21c): raft::linalg::scalarMultiply (out = in * scalar), used by Barnes_Hut at the end of the exaggeration phase and by compute_kl_div.
#pragma once
#include <cuda_runtime.h>
#include <cstddef>
namespace raft {
namespace linalg {
template <typename T>
__global__ void stub_scalar_mul_kernel(T* out, const T* in, T scalar, std::size_t len)
{
  std::size_t i = std::size_t(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i < len) out[i] = in[i] * scalar;
}
template <typename T, typename IdxType = int>
void scalarMultiply(T* out, const T* in, T scalar, IdxType len, cudaStream_t stream)
{
  std::size_t n = static_cast<std::size_t>(len);
  stub_scalar_mul_kernel<T><<<(n + 255) / 256, 256, 0, stream>>>(out, in, scalar, n);
}
}  // namespace linalg
}  // namespace raft

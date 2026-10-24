// R2 stub (T21c): raft::WarpSize, raft::ceildiv, and the cub include the real header brings in (utils.cuh uses cub::BlockReduce).
#pragma once
#include <cub/cub.cuh>
#include <cuda_runtime.h>
namespace raft {
static constexpr int WarpSize = 32;
template <typename T>
constexpr __host__ __device__ T ceildiv(T a, T b)
{
  return (a + b - 1) / b;
}
}  // namespace raft

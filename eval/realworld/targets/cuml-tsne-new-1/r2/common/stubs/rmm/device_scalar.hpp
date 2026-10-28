// R2 stub (T21c): rmm::device_scalar and rmm::device_uvector as plain cudaMalloc/cudaFree owners (uninitialised memory, like the originals).
#pragma once
#include <raft/util/cudart_utils.hpp>
#include <cuda_runtime.h>
#include <cstddef>
namespace rmm {
template <typename T>
class device_uvector {
 public:
  device_uvector(std::size_t n, cudaStream_t = 0) : n_(n)
  {
    RAFT_CUDA_TRY(cudaMalloc(reinterpret_cast<void**>(&p_), (n ? n : 1) * sizeof(T)));
  }
  device_uvector(const device_uvector&)            = delete;
  device_uvector& operator=(const device_uvector&) = delete;
  ~device_uvector() { cudaFree(p_); }
  T* data() { return p_; }
  const T* data() const { return p_; }
  std::size_t size() const { return n_; }
 private:
  T* p_ = nullptr;
  std::size_t n_;
};
template <typename T>
class device_scalar {
 public:
  explicit device_scalar(cudaStream_t = 0) { RAFT_CUDA_TRY(cudaMalloc(reinterpret_cast<void**>(&p_), sizeof(T))); }
  device_scalar(const device_scalar&)            = delete;
  device_scalar& operator=(const device_scalar&) = delete;
  ~device_scalar() { cudaFree(p_); }
  T* data() { return p_; }
  const T* data() const { return p_; }
 private:
  T* p_ = nullptr;
};
}  // namespace rmm

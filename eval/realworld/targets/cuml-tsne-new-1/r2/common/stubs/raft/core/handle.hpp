// R2 stub (T21c): raft::handle_t reduced to a stream and a thrust policy on it (what Barnes_Hut uses).
#pragma once
#include <thrust/execution_policy.h>
#include <cuda_runtime.h>
namespace raft {
struct stream_view_stub {
  cudaStream_t s;
  cudaStream_t get() const { return s; }
};
class handle_t {
 public:
  explicit handle_t(cudaStream_t s = 0) : s_(s) {}
  stream_view_stub get_stream() const { return {s_}; }
  auto get_thrust_policy() const { return thrust::cuda::par.on(s_); }
 private:
  cudaStream_t s_;
};
}  // namespace raft

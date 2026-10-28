// R2 stub (T21c): raft::random::Rng::uniform, used only by random_vector() for TSNE_INIT::RANDOM; the driver uses TSNE_INIT::PCA (host-supplied Y), so this is compiled but never executed.
#pragma once
#include <cuda_runtime.h>
namespace raft {
namespace random {
template <typename T>
__global__ void stub_uniform_kernel(T* out, int len, T lo, T hi, unsigned long long seed)
{
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= len) return;
  unsigned long long z = seed + 0x9E3779B97F4A7C15ull * (i + 1);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
  z ^= z >> 31;
  out[i] = lo + (hi - lo) * T((z >> 11) * (1.0 / 9007199254740992.0));
}
class Rng {
 public:
  explicit Rng(unsigned long long seed) : seed_(seed) {}
  template <typename T>
  void uniform(T* out, int len, T lo, T hi, cudaStream_t stream)
  {
    stub_uniform_kernel<T><<<(len + 255) / 256, 256, 0, stream>>>(out, len, lo, hi, seed_);
  }
 private:
  unsigned long long seed_;
};
}  // namespace random
}  // namespace raft

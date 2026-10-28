// T21a pytorch-1 host main (identical for the buggy and the fixed variant).
// The verbatim Embedding.cu of the revision is #included so that the kernel in the anonymous namespace
// at::native::{anon} is reachable; the ATen host code of that file is compiled (against the installed PyTorch headers)
// but never called.  The kernel is launched exactly as embedding_dense_backward_cuda does for
// num_indices <= 3072 && !scale_grad_by_freq: grid = ceil(D/32), block = (32, BLOCKDIMY=32),
// dynamic shared memory = sizeof(accscalar_t)*32*32 + sizeof(int)*32*32.
#include <aten/src/ATen/native/cuda/Embedding.cu>

#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // N = number of indices (2017..3072 reaches the second batch far enough to hit the racing last chunk), D = embedding dim,
  // V = number of embedding rows.  Defaults: N=2048 (two batches of 1024), D=32 (one 32x32 block), V=64.
  const int N = argc > 1 ? std::atoi(argv[1]) : 2048;
  const int D = argc > 2 ? std::atoi(argv[2]) : 32;
  const int V = argc > 3 ? std::atoi(argv[3]) : 64;
  const int padding_idx = -1;

  std::vector<int64_t> h_idx(N);
  std::vector<float> h_grad((size_t)N * D);
  unsigned s = 12345u;
  for (int i = 0; i < N; ++i) {
    s = s * 1664525u + 1013904223u;
    h_idx[i] = (int64_t)((s >> 8) % (unsigned)V);
  }
  // small integers: every partial sum is exactly representable in float, so any difference to the reference
  // is a manifested race, not rounding
  for (int i = 0; i < N; ++i)
    for (int f = 0; f < D; ++f) h_grad[(size_t)i * D + f] = (float)(((i * 13 + f * 7) % 5) - 2);

  int64_t* d_idx = nullptr; float* d_grad = nullptr; float* d_gw = nullptr;
  CK(cudaMalloc(&d_idx, sizeof(int64_t) * N));
  CK(cudaMalloc(&d_grad, sizeof(float) * (size_t)N * D));
  CK(cudaMalloc(&d_gw, sizeof(float) * (size_t)V * D));
  CK(cudaMemcpy(d_idx, h_idx.data(), sizeof(int64_t) * N, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_grad, h_grad.data(), sizeof(float) * (size_t)N * D, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_gw, 0, sizeof(float) * (size_t)V * D));

  const int warp_size = 32;
  const int64_t stride = D;
  dim3 grid((unsigned)((stride + warp_size - 1) / warp_size));
  dim3 block(warp_size, at::native::BLOCKDIMY);
  size_t shmem = sizeof(float) * warp_size * at::native::BLOCKDIMY + sizeof(int) * warp_size * at::native::BLOCKDIMY;
  at::native::embedding_backward_feature_kernel<float, float, int64_t><<<grid, block, shmem>>>(
      d_idx, d_grad, d_gw, N, stride, padding_idx);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<float> h_gw((size_t)V * D), ref((size_t)V * D, 0.0f);
  CK(cudaMemcpy(h_gw.data(), d_gw, sizeof(float) * (size_t)V * D, cudaMemcpyDeviceToHost));
  for (int i = 0; i < N; ++i)
    for (int f = 0; f < D; ++f) ref[(size_t)h_idx[i] * D + f] += h_grad[(size_t)i * D + f];
  long bad = 0;
  for (size_t k = 0; k < ref.size(); ++k) bad += (h_gw[k] != ref[k]);
  std::printf("embedding_backward_feature_kernel N=%d D=%d V=%d grid=%u block=(%u,%u) shmem=%zu mismatches=%ld/%zu\n",
              N, D, V, grid.x, block.x, block.y, shmem, bad, ref.size());
  return 0;
}

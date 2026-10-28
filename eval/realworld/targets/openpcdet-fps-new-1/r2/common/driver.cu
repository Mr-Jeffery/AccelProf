// T21c openpcdet-fps-new-1 host main (R2).  The verbatim pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu and
// pcdet/ops/pointnet2/pointnet2_stack/src/sampling_gpu.cu of the pinned commit 233f8498 (each with its own cuda_utils.h and sampling_gpu.h, also copied)
// are #included.  Upstream they are two separate extensions (pointnet2_batch_cuda, pointnet2_stack_cuda); both define farthest_point_sampling_kernel,
// __update, opt_n_threads, farthest_point_sampling_kernel_launcher, so a single binary needs one namespace per extension.  The shim is only the
// `namespace { #include }` wrapper below: the torch/CUDA system headers the two files pull in are included first, so their include guards turn the
// nested system #includes into no-ops and the namespace contains upstream code only.  sampling_gpu.h's guard _SAMPLING_GPU_H is the same in both
// directories and is #undef'd between them.  The upstream launchers called here use no libtorch (plain <<<>>> launches); the torch-tensor
// wrappers (sampling.cpp, not compiled) are never needed.
#include <stdio.h>
#include <stdlib.h>
#include <cmath>
#include <vector>
#include <torch/serialize/tensor.h>
#include <ATen/cuda/CUDAContext.h>

namespace pcdet_batch {
#include <pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu>
}
#undef _SAMPLING_GPU_H
namespace pcdet_stack {
#include <pcdet/ops/pointnet2/pointnet2_stack/src/sampling_gpu.cu>
}

#include <cstdint>
#include <cstdio>
#include <cstdlib>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

// host FPS reference for one batch: xyz points (n,3), m samples, temp init 1e10; idx offset `base` is added to every reference index (stack variant)
static int fps_ref(const float* p, int n, int m, const int* idx, int base_idx, int first) {
  std::vector<float> temp(n, 1e10f); int old = 0, bad = (idx[0] != first);
  for (int j = 1; j < m; ++j) {
    float best = -1.f; int bi = 0;
    for (int k = 0; k < n; ++k) {
      float x = p[k * 3] - p[old * 3], y = p[k * 3 + 1] - p[old * 3 + 1], z = p[k * 3 + 2] - p[old * 3 + 2];
      float d2 = std::fmin(x * x + y * y + z * z, temp[k]); temp[k] = d2;
      if (d2 > best) { best = d2; bi = k; }
    }
    old = bi; bad += (idx[j] != bi + base_idx);
  }
  return bad;
}

int main(int argc, char** argv) {
  // farthest_point_sample(xyz[B,N,3], npoint): default B=2, N=2048, M=256 for the batch kernel (block opt_n_threads(2048) = 1024); the two stack-file
  // kernels run with M2 sampled points (default 64) to keep the total access count near 1.7e7.
  const int B = argc > 1 ? std::atoi(argv[1]) : 2;
  const int N = argc > 2 ? std::atoi(argv[2]) : 2048;
  const int M = argc > 3 ? std::atoi(argv[3]) : 256;
  const int M2 = argc > 4 ? std::atoi(argv[4]) : 64;

  std::vector<float> h_pts((size_t)B * N * 3);
  uint32_t s = 5u;
  for (auto& v : h_pts) { s = s * 1664525u + 1013904223u; v = (float)(s >> 8) / (float)(1u << 24) * 2.f - 1.f; }
  std::vector<float> h_temp((size_t)B * N, 1e10f);
  float *d_pts, *d_temp; int *d_idx_b, *d_idx_s, *d_idx_t, *d_cnt, *d_np;
  CK(cudaMalloc(&d_pts, h_pts.size() * 4)); CK(cudaMalloc(&d_temp, h_temp.size() * 4));
  CK(cudaMalloc(&d_idx_b, (size_t)B * M * 4)); CK(cudaMalloc(&d_idx_s, (size_t)B * M2 * 4)); CK(cudaMalloc(&d_idx_t, (size_t)B * M2 * 4));
  CK(cudaMalloc(&d_cnt, B * 4)); CK(cudaMalloc(&d_np, B * 4));
  CK(cudaMemcpy(d_pts, h_pts.data(), h_pts.size() * 4, cudaMemcpyHostToDevice));
  std::vector<int> h_cnt(B, N), h_np(B, M2);
  CK(cudaMemcpy(d_cnt, h_cnt.data(), B * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_np, h_np.data(), B * 4, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_idx_b, 0xff, (size_t)B * M * 4)); CK(cudaMemset(d_idx_s, 0xff, (size_t)B * M2 * 4)); CK(cudaMemset(d_idx_t, 0xff, (size_t)B * M2 * 4));

  // 1. pointnet2_batch: farthest_point_sampling_kernel<1024><<<B, 1024>>>  (upstream launcher)
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));
  pcdet_batch::farthest_point_sampling_kernel_launcher(B, N, M, d_pts, d_temp, d_idx_b);
  CK(cudaGetLastError()); CK(cudaDeviceSynchronize());
  // 2. pointnet2_stack: farthest_point_sampling_kernel<1024><<<B, 1024>>>  (upstream launcher, same (B,N,3) layout)
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));
  pcdet_stack::farthest_point_sampling_kernel_launcher(B, N, M2, d_pts, d_temp, d_idx_s);
  CK(cudaGetLastError()); CK(cudaDeviceSynchronize());
  // 3. pointnet2_stack: stack_farthest_point_sampling_kernel<1024><<<batch_size, 1024>>>  (upstream launcher; points of all batches stacked, N = B*N)
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));
  pcdet_stack::stack_farthest_point_sampling_kernel_launcher(B * N, B, d_pts, d_temp, d_cnt, d_idx_t, d_np);
  CK(cudaGetLastError()); CK(cudaDeviceSynchronize());

  std::vector<int> h_b((size_t)B * M), h_s((size_t)B * M2), h_t((size_t)B * M2);
  CK(cudaMemcpy(h_b.data(), d_idx_b, h_b.size() * 4, cudaMemcpyDeviceToHost));
  CK(cudaMemcpy(h_s.data(), d_idx_s, h_s.size() * 4, cudaMemcpyDeviceToHost));
  CK(cudaMemcpy(h_t.data(), d_idx_t, h_t.size() * 4, cudaMemcpyDeviceToHost));
  int bad_b = 0, bad_s = 0, bad_t = 0;
  for (int b = 0; b < B; ++b) {
    const float* p = &h_pts[(size_t)b * N * 3];
    bad_b += fps_ref(p, N, M, &h_b[(size_t)b * M], 0, 0);
    bad_s += fps_ref(p, N, M2, &h_s[(size_t)b * M2], 0, 0);
    bad_t += fps_ref(p, N, M2, &h_t[(size_t)b * M2], b * N, b * N);   // stack kernel returns indices into the stacked array
  }
  std::printf("pointnet2_batch farthest_point_sampling_kernel<1024> B=%d N=%d M=%d grid=%d block=1024 idx[0..2]=%d,%d,%d mismatches=%d/%d\n", B, N, M, B, h_b[0], h_b[1], h_b[2], bad_b, B * M);
  std::printf("pointnet2_stack farthest_point_sampling_kernel<1024> B=%d N=%d M=%d grid=%d block=1024 idx[0..2]=%d,%d,%d mismatches=%d/%d\n", B, N, M2, B, h_s[0], h_s[1], h_s[2], bad_s, B * M2);
  std::printf("pointnet2_stack stack_farthest_point_sampling_kernel<1024> batch_size=%d N=%d M=%d grid=%d block=1024 idx[0..2]=%d,%d,%d mismatches=%d/%d\n", B, B * N, M2, B, h_t[0], h_t[1], h_t[2], bad_t, B * M2);
  return 0;
}

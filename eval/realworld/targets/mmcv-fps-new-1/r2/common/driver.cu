// T21c mmcv-fps-new-1 host main (R2).  The verbatim mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh of the pinned commit d2111bda
// is #included (its "pytorch_cuda_helper.hpp" is the include shim in common/: the kernels use only CUDA's min/max builtins).
// Launches follow FurthestPointSamplingForwardCUDAKernelLauncher / ...WithDistForwardCUDAKernelLauncher (mmcv/ops/csrc/pytorch/cuda/
// furthest_point_sample_cuda.cu at the commit): n_threads = opt_n_threads(n) = min(2^floor(log2 n), 1024) -> kernel<n_threads><<<b, n_threads>>>.
#include <mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

// copy of the launcher file's opt_n_threads (that file needs torch for its stream, so it is not included)
inline int opt_n_threads(int work_size) {
  const int pow_2 = std::log(static_cast<double>(work_size)) / std::log(2.0);
  return max(min(1 << pow_2, 1024), 1);
}

// host FPS reference over a distance function; returns the number of idx mismatches against `idx`
template <class Dist>
static int fps_ref(int B, int N, int M, const std::vector<int>& idx, Dist dist) {
  int bad = 0;
  for (int b = 0; b < B; ++b) {
    std::vector<float> temp(N, 1e10f); int old = 0;
    bad += (idx[(size_t)b * M] != 0);
    for (int j = 1; j < M; ++j) {
      float best = -1.f; int bi = 0;
      for (int k = 0; k < N; ++k) { float d2 = std::fmin(dist(b, old, k), temp[k]); temp[k] = d2; if (d2 > best) { best = d2; bi = k; } }
      old = bi; bad += (idx[(size_t)b * M + j] != bi);
    }
  }
  return bad;
}

int main(int argc, char** argv) {
  // furthest_point_sample(xyz[B,N,3], M): default B=2, N=2048, M=256 (block 1024).  The with_dist kernel (dataset (B,N,N) pairwise squared distances)
  // runs with M2 sampled points (default 64) to keep the total access count near 1.3e7.
  const int B = argc > 1 ? std::atoi(argv[1]) : 2;
  const int N = argc > 2 ? std::atoi(argv[2]) : 2048;
  const int M = argc > 3 ? std::atoi(argv[3]) : 256;
  const int M2 = argc > 4 ? std::atoi(argv[4]) : 64;

  std::vector<float> h_pts((size_t)B * N * 3);
  uint32_t s = 11u;
  for (auto& v : h_pts) { s = s * 1664525u + 1013904223u; v = (float)(s >> 8) / (float)(1u << 24); }
  auto sq = [&](int b, int i, int k) {
    const float* p = &h_pts[(size_t)b * N * 3];
    float x = p[k * 3] - p[i * 3], y = p[k * 3 + 1] - p[i * 3 + 1], z = p[k * 3 + 2] - p[i * 3 + 2];
    return x * x + y * y + z * z;
  };
  std::vector<float> h_dmat((size_t)B * N * N);
  for (int b = 0; b < B; ++b) for (int i = 0; i < N; ++i) for (int k = 0; k < N; ++k) h_dmat[((size_t)b * N + i) * N + k] = sq(b, i, k);
  std::vector<float> h_temp((size_t)B * N, 1e10f);

  float *d_pts, *d_dmat, *d_temp; int *d_idx, *d_idx2;
  CK(cudaMalloc(&d_pts, h_pts.size() * 4)); CK(cudaMalloc(&d_dmat, h_dmat.size() * 4)); CK(cudaMalloc(&d_temp, h_temp.size() * 4));
  CK(cudaMalloc(&d_idx, (size_t)B * M * 4)); CK(cudaMalloc(&d_idx2, (size_t)B * M2 * 4));
  CK(cudaMemcpy(d_pts, h_pts.data(), h_pts.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_dmat, h_dmat.data(), h_dmat.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_idx, 0xff, (size_t)B * M * 4)); CK(cudaMemset(d_idx2, 0xff, (size_t)B * M2 * 4));

  const unsigned int n_threads = opt_n_threads(N);
  if (n_threads != 1024) { std::fprintf(stderr, "this driver instantiates the 1024-thread kernels only (N=%d -> %u threads)\n", N, n_threads); return 1; }
  furthest_point_sampling_forward_cuda_kernel<1024><<<B, n_threads>>>(B, N, M, d_pts, d_temp, d_idx);
  CK(cudaGetLastError()); CK(cudaDeviceSynchronize());
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));        // fresh temp for the second kernel
  furthest_point_sampling_with_dist_forward_cuda_kernel<1024><<<B, n_threads>>>(B, N, M2, d_dmat, d_temp, d_idx2);
  CK(cudaGetLastError()); CK(cudaDeviceSynchronize());

  std::vector<int> h_idx((size_t)B * M), h_idx2((size_t)B * M2);
  CK(cudaMemcpy(h_idx.data(), d_idx, h_idx.size() * 4, cudaMemcpyDeviceToHost));
  CK(cudaMemcpy(h_idx2.data(), d_idx2, h_idx2.size() * 4, cudaMemcpyDeviceToHost));
  const int bad1 = fps_ref(B, N, M, h_idx, sq);
  const int bad2 = fps_ref(B, N, M2, h_idx2, [&](int b, int i, int k) { return h_dmat[((size_t)b * N + i) * N + k]; });
  std::printf("furthest_point_sampling_forward_cuda_kernel<1024> B=%d N=%d M=%d grid=%d block=%u idx[0..3]=%d,%d,%d,%d mismatches=%d/%d\n",
              B, N, M, B, n_threads, h_idx[0], h_idx[1], h_idx[2], h_idx[3], bad1, B * M);
  std::printf("furthest_point_sampling_with_dist_forward_cuda_kernel<1024> B=%d N=%d M=%d grid=%d block=%u idx[0..3]=%d,%d,%d,%d mismatches=%d/%d\n",
              B, N, M2, B, n_threads, h_idx2[0], h_idx2[1], h_idx2[2], h_idx2[3], bad2, B * M2);
  return 0;
}

// T21c pointnet2pt-fps-new-1 host main (R2).  The verbatim pointnet2_ops/_ext-src/src/sampling_gpu.cu of the pinned commit b5ceb6d9 (with its own
// include/cuda_utils.h, also copied) is #included; the host wrappers in it (need libtorch: at::cuda::getCurrentCUDAStream) are compiled but never
// called.  The kernel is launched as furthest_point_sampling_kernel_wrapper() launches it at this size:
//   n_threads = opt_n_threads(n) (cuda_utils.h, TOTAL_THREADS 512) -> furthest_point_sampling_kernel<512><<<b, n_threads>>>(b, n, m, dataset, temp, idxs).
#include <pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // furthest_point_sample(torch.rand(B, N, 3).cuda(), M): dataset (B,N,3) float, temp (B,N) filled with 1e10, idxs (B,M) int.
  const int B = argc > 1 ? std::atoi(argv[1]) : 2;
  const int N = argc > 2 ? std::atoi(argv[2]) : 2048;
  const int M = argc > 3 ? std::atoi(argv[3]) : 256;

  std::vector<float> h_pts((size_t)B * N * 3);
  uint32_t s = 7u;
  for (auto& v : h_pts) { s = s * 1664525u + 1013904223u; v = (float)(s >> 8) / (float)(1u << 24); }   // torch.rand: [0,1)
  std::vector<float> h_temp((size_t)B * N, 1e10f);
  float *d_pts, *d_temp; int* d_idx;
  CK(cudaMalloc(&d_pts, h_pts.size() * 4)); CK(cudaMalloc(&d_temp, h_temp.size() * 4)); CK(cudaMalloc(&d_idx, (size_t)B * M * 4));
  CK(cudaMemcpy(d_pts, h_pts.data(), h_pts.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_temp, h_temp.data(), h_temp.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_idx, 0xff, (size_t)B * M * 4));

  const unsigned int n_threads = opt_n_threads(N);
  switch (n_threads) {       // the wrapper's switch; only the instantiation reached at this size is written out
    case 512: furthest_point_sampling_kernel<512><<<B, n_threads>>>(B, N, M, d_pts, d_temp, d_idx); break;
    case 256: furthest_point_sampling_kernel<256><<<B, n_threads>>>(B, N, M, d_pts, d_temp, d_idx); break;
    default:  furthest_point_sampling_kernel<512><<<B, n_threads>>>(B, N, M, d_pts, d_temp, d_idx);
  }
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<int> h_idx((size_t)B * M);
  CK(cudaMemcpy(h_idx.data(), d_idx, h_idx.size() * 4, cudaMemcpyDeviceToHost));
  int bad = 0;                // host FPS reference (random floats: no ties; device FMA may flip a near-tie, reported not fatal)
  for (int b = 0; b < B; ++b) {
    const float* p = &h_pts[(size_t)b * N * 3]; std::vector<float> temp(N, 1e10f); int old = 0;
    bad += (h_idx[(size_t)b * M] != 0);
    for (int j = 1; j < M; ++j) {
      float best = -1.f; int bi = 0;
      for (int k = 0; k < N; ++k) {
        float x = p[k * 3] - p[old * 3], y = p[k * 3 + 1] - p[old * 3 + 1], z = p[k * 3 + 2] - p[old * 3 + 2];
        float mag = p[k * 3] * p[k * 3] + p[k * 3 + 1] * p[k * 3 + 1] + p[k * 3 + 2] * p[k * 3 + 2];
        if (mag <= 1e-3f) continue;
        float d2 = std::fmin(x * x + y * y + z * z, temp[k]); temp[k] = d2;
        if (d2 > best) { best = d2; bi = k; }
      }
      old = bi; bad += (h_idx[(size_t)b * M + j] != bi);
    }
  }
  std::printf("furthest_point_sampling_kernel<%u> B=%d N=%d M=%d grid=%d block=%u idx[0..3]=%d,%d,%d,%d mismatches=%d/%d\n",
              n_threads, B, N, M, B, n_threads, h_idx[0], h_idx[1], h_idx[2], h_idx[3], bad, B * M);
  return 0;
}

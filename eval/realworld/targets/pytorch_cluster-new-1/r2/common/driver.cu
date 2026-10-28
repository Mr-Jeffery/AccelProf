// T21c pytorch_cluster-new-1 host main (R2).  The verbatim csrc/cuda/fps_cuda.cu of the pinned commit e9a855c2 (with its own fps_cuda.h,
// utils.cuh, extensions.h, macros.h, also copied) is #included; fps_cuda() (host, needs libtorch) is compiled but never called.
// The kernel is launched as fps_cuda() launches it: fps_kernel<float><<<batch_size, THREADS=256>>>(src, ptr, out_ptr, start, dist, out, dim).
#include <csrc/cuda/fps_cuda.cu>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // B batches of N random 3-d points each (ptr = {0,N,2N,..}); M samples per batch (out_ptr = {0,M,2M,..}, i.e. ratio = M/N), start = first point.
  // N=512 gives every one of the 256 threads two real points, so the reduction's compare-and-overwrite really executes at every stride
  // (i = 1..128), including the cross-warp strides 32, 64, 128; the repo test (8 points / 2 batches) would leave threads >= 4 at -1 and never write cross-warp.
  const int B = argc > 1 ? std::atoi(argv[1]) : 2;
  const int N = argc > 2 ? std::atoi(argv[2]) : 512;
  const int M = argc > 3 ? std::atoi(argv[3]) : 128;
  const int dim = 3;

  std::vector<float> h_src((size_t)B * N * dim);
  uint32_t s = 2024u;
  for (auto& v : h_src) { s = s * 1664525u + 1013904223u; v = (float)(s >> 8) / (float)(1u << 24) * 2.f - 1.f; }
  std::vector<int64_t> h_ptr(B + 1), h_optr(B + 1), h_start(B, 0);
  for (int b = 0; b <= B; ++b) { h_ptr[b] = (int64_t)b * N; h_optr[b] = (int64_t)b * M; }
  std::vector<float> h_dist((size_t)B * N, 5e4f);      // fps_cuda(): torch::full(src.size(0), 5e4, ...)

  float *d_src, *d_dist; int64_t *d_ptr, *d_optr, *d_start, *d_out;
  CK(cudaMalloc(&d_src, h_src.size() * 4)); CK(cudaMalloc(&d_dist, h_dist.size() * 4));
  CK(cudaMalloc(&d_ptr, (B + 1) * 8)); CK(cudaMalloc(&d_optr, (B + 1) * 8)); CK(cudaMalloc(&d_start, B * 8)); CK(cudaMalloc(&d_out, (size_t)B * M * 8));
  CK(cudaMemcpy(d_src, h_src.data(), h_src.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_dist, h_dist.data(), h_dist.size() * 4, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_ptr, h_ptr.data(), (B + 1) * 8, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_optr, h_optr.data(), (B + 1) * 8, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_start, h_start.data(), B * 8, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_out, 0xff, (size_t)B * M * 8));

  fps_kernel<float><<<B, THREADS>>>(d_src, d_ptr, d_optr, d_start, d_dist, d_out, dim);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<int64_t> h_out((size_t)B * M);
  CK(cudaMemcpy(h_out.data(), d_out, h_out.size() * 8, cudaMemcpyDeviceToHost));
  // Host reference: plain farthest-point sampling (first maximum on ties; random floats have none).
  int bad = 0;
  for (int b = 0; b < B; ++b) {
    std::vector<float> dist(N, 5e4f); int64_t old = 0;
    if (h_out[(size_t)b * M] != (int64_t)b * N) ++bad;
    for (int m = 1; m < M; ++m) {
      float best = -1.f; int64_t bi = 0;
      for (int n = 0; n < N; ++n) {
        float dd = 0.f;
        for (int d = 0; d < dim; ++d) { float t = h_src[((size_t)b * N + old) * dim + d] - h_src[((size_t)b * N + n) * dim + d]; dd += t * t; }
        dd = std::fmin(dist[n], dd); dist[n] = dd;
        if (dd > best) { best = dd; bi = n; }
      }
      old = bi;
      bad += (h_out[(size_t)b * M + m] != (int64_t)b * N + bi);
    }
  }
  std::printf("fps_kernel<float> B=%d N=%d M=%d dim=%d grid=%d block=%d out[0..3]=%lld,%lld,%lld,%lld mismatches=%d/%d\n",
              B, N, M, dim, B, THREADS, (long long)h_out[0], (long long)h_out[1], (long long)h_out[2], (long long)h_out[3], bad, B * M);
  return 0;
}

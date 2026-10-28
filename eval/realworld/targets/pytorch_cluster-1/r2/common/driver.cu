// T21a pytorch_cluster-1 host main (identical for the buggy and the fixed variant).
// The verbatim csrc/cuda/nearest_cuda.cu of the revision (with its own nearest_cuda.h and utils.cuh, also copied
// from the revision) is #included; nearest_cuda() (host, needs libtorch) is compiled but never called.
// The kernel is launched exactly as nearest_cuda() launches it: nearest_kernel<float><<<x.size(0), THREADS=1024>>>.
#include <csrc/cuda/nearest_cuda.cu>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // N query points (= grid size), M reference points, dim = 2, ONE batch (ptr_x = {0,N}, ptr_y = {0,M}).
  // Reference points lie on a line so that their distance to every query DEcreases along the index (V-shaped with the
  // minimum at the end): in the in-place reduction (best_dist[t] > best_dist[t+i] -> overwrite) almost every thread then
  // really executes the racy write in every iteration.  Thread w only holds a real distance if w < M, so the cross-warp
  // iterations (i >= 32) need M > 32 + 32: the default M = 128 exercises i = 1,2,4,...,512 with writes up to i = 64.
  const int N = argc > 1 ? std::atoi(argv[1]) : 8;
  const int M = argc > 2 ? std::atoi(argv[2]) : 128;
  const int dim = 2;

  std::vector<float> h_x((size_t)N * dim), h_y((size_t)M * dim);
  for (int q = 0; q < N; ++q) { h_x[(size_t)q * dim + 0] = 0.25f * (float)q + 0.1f; h_x[(size_t)q * dim + 1] = 1.0f; }
  for (int j = 0; j < M; ++j) { h_y[(size_t)j * dim + 0] = (float)(M - j); h_y[(size_t)j * dim + 1] = 0.0f; }
  int64_t h_ptr_x[2] = {0, N}, h_ptr_y[2] = {0, M};

  float *d_x = nullptr, *d_y = nullptr; int64_t *d_px = nullptr, *d_py = nullptr, *d_out = nullptr;
  CK(cudaMalloc(&d_x, sizeof(float) * h_x.size()));
  CK(cudaMalloc(&d_y, sizeof(float) * h_y.size()));
  CK(cudaMalloc(&d_px, sizeof(h_ptr_x)));
  CK(cudaMalloc(&d_py, sizeof(h_ptr_y)));
  CK(cudaMalloc(&d_out, sizeof(int64_t) * N));
  CK(cudaMemcpy(d_x, h_x.data(), sizeof(float) * h_x.size(), cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_y, h_y.data(), sizeof(float) * h_y.size(), cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_px, h_ptr_x, sizeof(h_ptr_x), cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_py, h_ptr_y, sizeof(h_ptr_y), cudaMemcpyHostToDevice));
  CK(cudaMemset(d_out, 0xff, sizeof(int64_t) * N));

  nearest_kernel<float><<<N, THREADS>>>(d_x, d_y, d_px, d_py, d_out, /*batch_size=*/1, dim);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<int64_t> h_out(N);
  CK(cudaMemcpy(h_out.data(), d_out, sizeof(int64_t) * N, cudaMemcpyDeviceToHost));
  int bad = 0;
  for (int q = 0; q < N; ++q) {
    int64_t best_j = 0; float best = 1e38f;
    for (int j = 0; j < M; ++j) {
      float dist = 0;
      for (int d = 0; d < dim; ++d) dist += (h_x[(size_t)q * dim + d] - h_y[(size_t)j * dim + d]) * (h_x[(size_t)q * dim + d] - h_y[(size_t)j * dim + d]);
      if (dist < best) { best = dist; best_j = j; }
    }
    bad += (h_out[q] != best_j);
  }
  std::printf("nearest_kernel<float> N=%d M=%d dim=%d grid=%d block=%d out[0..3]=%lld,%lld,%lld,%lld mismatches=%d/%d\n",
              N, M, dim, N, THREADS, (long long)h_out[0], (long long)h_out[N > 1 ? 1 : 0], (long long)h_out[N > 2 ? 2 : 0],
              (long long)h_out[N > 3 ? 3 : 0], bad, N);
  return 0;
}

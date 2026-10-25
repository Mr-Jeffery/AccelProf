// pytorch_cluster-new-1 FIXED (reduction loop replaced, marked FIX): kernel copied from pytorch_cluster e9a855c284b45edcbf0282cf70ac09bee0ce4e49, csrc/cuda/fps_cuda.cu L7-L65 (fps_kernel<float>).
// Trimmed: blank lines, the torch host function fps_cuda (launch <<<batch_size, THREADS>>> kept). Statements joined (whitespace only).
#include <cstdio>
#include <cstdint>
#include <vector>
#include <algorithm>
#define THREADS 256
template <typename scalar_t>
__global__ void fps_kernel(const scalar_t *src, const int64_t *ptr, const int64_t *out_ptr, const int64_t *start, scalar_t *dist, int64_t *out, int64_t dim) {
  const int64_t thread_idx = threadIdx.x; const int64_t batch_idx = blockIdx.x;
  const int64_t start_idx = ptr[batch_idx]; const int64_t end_idx = ptr[batch_idx + 1];
  __shared__ scalar_t best_dist[THREADS]; __shared__ int64_t best_dist_idx[THREADS];
  if (thread_idx == 0) { out[out_ptr[batch_idx]] = start_idx + start[batch_idx]; }
  for (int64_t m = out_ptr[batch_idx] + 1; m < out_ptr[batch_idx + 1]; m++) {
    __syncthreads();
    int64_t old = out[m - 1];
    scalar_t best = (scalar_t)-1.; int64_t best_idx = 0;
    for (int64_t n = start_idx + thread_idx; n < end_idx; n += THREADS) {
      scalar_t tmp, dd = (scalar_t)0.;
      for (int64_t d = 0; d < dim; d++) { tmp = src[dim * old + d] - src[dim * n + d]; dd += tmp * tmp; }
      dd = min(dist[n], dd); dist[n] = dd;
      if (dd > best) { best = dd; best_idx = n; }
    }
    best_dist[thread_idx] = best; best_dist_idx[thread_idx] = best_idx;
    for (int64_t u = 0; (1 << u) < THREADS; u++) {  // FIX: the pairwise tree of upstream a5abfee (nearest_cuda.cu), with < for the max
      __syncthreads();
      if (thread_idx < (THREADS >> (u + 1))) { int64_t idx_1 = (thread_idx * 2) << u; int64_t idx_2 = (thread_idx * 2 + 1) << u;
        if (best_dist[idx_1] < best_dist[idx_2]) { best_dist[idx_1] = best_dist[idx_2]; best_dist_idx[idx_1] = best_dist_idx[idx_2]; } }  // writes even multiples of 2^(u+1), reads odd multiples of 2^u
    }
    __syncthreads();
    if (thread_idx == 0) { out[m] = best_dist_idx[0]; }
  }
}
static int check(const float *p, const int64_t *o, int B, int N, int M) {  // counts picks that are not a farthest point
  int bad = 0; std::vector<float> t(N);
  for (int b = 0; b < B; b++) { std::fill(t.begin(), t.end(), 5e4f); bad += o[b * M] != (int64_t)b * N;
    for (int j = 1; j < M; j++) { int64_t a = o[b * M + j - 1], c = o[b * M + j] - (int64_t)b * N; float mx = -1;
      for (int k = 0; k < N; k++) { float dd = 0; for (int d = 0; d < 3; d++) { float tmp = p[3 * a + d] - p[3 * ((int64_t)b * N + k) + d]; dd += tmp * tmp; }
        t[k] = std::min(t[k], dd); mx = std::max(mx, t[k]); }
      if (c < 0 || c >= N) { bad++; break; } bad += t[c] != mx; } }
  return bad; }
int main() {
  const int B = 2, N = 512, M = 128;  // as the T21c driver: 2 batches, 256 threads, 2 real points per thread
  std::vector<float> h(B * N * 3), d0(B * N, 5e4f); std::vector<int64_t> ptr = {0, N, 2 * N}, optr = {0, M, 2 * M}, st = {0, 0}, o(B * M);
  srand(1); for (auto &v : h) v = (float)(rand() % 100);  // integer coords: distances exact in fp32 and below 5e4 (fps_cuda's dist init)
  float *s, *dist; int64_t *dp, *dop, *dst, *out; cudaMalloc(&s, h.size() * 4); cudaMalloc(&dist, d0.size() * 4);
  cudaMalloc(&dp, 24); cudaMalloc(&dop, 24); cudaMalloc(&dst, 16); cudaMalloc(&out, o.size() * 8);
  cudaMemcpy(s, h.data(), h.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(dist, d0.data(), d0.size() * 4, cudaMemcpyHostToDevice);
  cudaMemcpy(dp, ptr.data(), 24, cudaMemcpyHostToDevice); cudaMemcpy(dop, optr.data(), 24, cudaMemcpyHostToDevice); cudaMemcpy(dst, st.data(), 16, cudaMemcpyHostToDevice);
  fps_kernel<float><<<B, THREADS>>>(s, dp, dop, dst, dist, out, 3);
  cudaError_t e = cudaDeviceSynchronize(); cudaMemcpy(o.data(), out, o.size() * 8, cudaMemcpyDeviceToHost); int bad = check(h.data(), o.data(), B, N, M);
  printf("pytorch_cluster-new-1 FIXED fps_kernel<float> B=%d N=%d M=%d %s out[0..3]=%lld,%lld,%lld,%lld invalid=%d/%d -> %s\n", B, N, M, cudaGetErrorString(e),
         (long long)o[0], (long long)o[1], (long long)o[2], (long long)o[3], bad, B * M, bad ? "WRONG OUTPUT" : "OK");
  return bad ? 1 : 0; }

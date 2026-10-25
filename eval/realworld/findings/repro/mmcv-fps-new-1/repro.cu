// mmcv-fps-new-1: kernel copied from mmcv d2111bda571f3b3eb53954af6f9cff25f34e626f, furthest_point_sample_cuda_kernel.cuh L11-L83.
// Trimmed: comments, blank lines, the with_dist kernel (same race, L134/L147), the torch launcher. Statements joined (whitespace only).
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
__device__ void __update(float *__restrict__ dists, int *__restrict__ dists_i, int idx1, int idx2) {
  const float v1 = dists[idx1], v2 = dists[idx2]; const int i1 = dists_i[idx1], i2 = dists_i[idx2];
  dists[idx1] = max(v1, v2);
  dists_i[idx1] = v2 > v1 ? i2 : i1;
}
template <unsigned int block_size>
__global__ void furthest_point_sampling_forward_cuda_kernel(int b, int n, int m, const float *__restrict__ dataset, float *__restrict__ temp, int *__restrict__ idxs) {
  if (m <= 0) return; __shared__ float dists[block_size]; __shared__ int dists_i[block_size];
  int batch_index = blockIdx.x; dataset += batch_index * n * 3; temp += batch_index * n; idxs += batch_index * m;
  int tid = threadIdx.x; const int stride = block_size;
  int old = 0; if (threadIdx.x == 0) idxs[0] = old;
  __syncthreads();
  for (int j = 1; j < m; j++) {
    int besti = 0; float best = -1;
    float x1 = dataset[old * 3 + 0]; float y1 = dataset[old * 3 + 1]; float z1 = dataset[old * 3 + 2];
    for (int k = tid; k < n; k += stride) {
      float x2, y2, z2; x2 = dataset[k * 3 + 0]; y2 = dataset[k * 3 + 1]; z2 = dataset[k * 3 + 2];
      float d = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1) + (z2 - z1) * (z2 - z1);
      float d2 = min(d, temp[k]); temp[k] = d2;
      besti = d2 > best ? k : besti; best = d2 > best ? d2 : best;
    }
    dists[tid] = best;
    dists_i[tid] = besti;  // upstream L67: WRITE dists_i[0] by thread 0 (iteration j+1)
    __syncthreads();
#pragma unroll
    for (int block_size_thres = 1024; block_size_thres >= 2; block_size_thres >>= 1) {
      const int tid_thres = block_size_thres / 2;
      if (block_size >= block_size_thres && tid < tid_thres) { __update(dists, dists_i, tid, tid + tid_thres); }
      __syncthreads();
    }
    old = dists_i[0];  // upstream L80: READ dists_i[0] by every thread (iteration j); no barrier before the next L67
    if (tid == 0) idxs[j] = old;
  }
}
static int check(const float *p, const int *o, int B, int N, int M) {  // counts picks that are not a farthest point
  int bad = 0; std::vector<float> t(N);
  for (int b = 0; b < B; b++) { const float *q = p + b * N * 3; std::fill(t.begin(), t.end(), 1e10f); bad += o[b * M] != 0;
    for (int j = 1; j < M; j++) { int a = o[b * M + j - 1], c = o[b * M + j]; float mx = -1;
      for (int k = 0; k < N; k++) { float dx = q[k*3] - q[a*3], dy = q[k*3+1] - q[a*3+1], dz = q[k*3+2] - q[a*3+2];
        t[k] = std::min(t[k], dx * dx + dy * dy + dz * dz); mx = std::max(mx, t[k]); }
      bad += (c < 0 || c >= N || t[c] != mx); } }
  return bad; }
int main(int argc, char **argv) {
  const int B = 2, N = 2048, M = argc > 1 ? atoi(argv[1]) : 256;  // launcher: opt_n_threads(2048) = 1024 -> kernel<1024>
  std::vector<float> h(B * N * 3), t0(B * N, 1e10f); std::vector<int> o(B * M);
  srand(1); for (auto &v : h) v = (float)(1 + rand() % 1000);  // integer coordinates: every distance is exact in fp32
  float *d, *t; int *ix; cudaMalloc(&d, h.size() * 4); cudaMalloc(&t, t0.size() * 4); cudaMalloc(&ix, o.size() * 4);
  cudaMemcpy(d, h.data(), h.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(t, t0.data(), t0.size() * 4, cudaMemcpyHostToDevice);
  furthest_point_sampling_forward_cuda_kernel<1024><<<B, 1024>>>(B, N, M, d, t, ix);
  cudaError_t e = cudaDeviceSynchronize(); cudaMemcpy(o.data(), ix, o.size() * 4, cudaMemcpyDeviceToHost); int bad = check(h.data(), o.data(), B, N, M);
  printf("mmcv-fps-new-1 fps<1024> B=%d N=%d M=%d %s idx[0..3]=%d,%d,%d,%d invalid=%d/%d -> %s\n", B, N, M, cudaGetErrorString(e), o[0], o[1], o[2], o[3], bad, B * M, bad ? "WRONG OUTPUT" : "OK");
  return bad ? 1 : 0; }

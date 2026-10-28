// openpcdet-fps-new-1 PERTURBED (warp 1 delayed before the dists_i[0] read, marked PERTURB): kernel copied from OpenPCDet 233f849829b6ac19afb8af8837a0246890908755, pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu L92-L216.
// Trimmed: comments (incl. the commented-out mag check), blank lines, the launcher, the two stack-file kernels (same race). Statements joined (whitespace only).
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
__device__ void __update(float *__restrict__ dists, int *__restrict__ dists_i, int idx1, int idx2) {
  const float v1 = dists[idx1], v2 = dists[idx2]; const int i1 = dists_i[idx1], i2 = dists_i[idx2];
  dists[idx1] = max(v1, v2);
  dists_i[idx1] = v2 > v1 ? i2 : i1;
}
__device__ __forceinline__ void delay(long long cyc) { asm volatile("" ::: "memory"); long long t0 = clock64(); while (clock64() - t0 < cyc) __nanosleep(1000); asm volatile("" ::: "memory"); }
template <unsigned int block_size>
__global__ void farthest_point_sampling_kernel(int b, int n, int m, const float *__restrict__ dataset, float *__restrict__ temp, int *__restrict__ idxs) {
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
    dists_i[tid] = besti;  // upstream L147: WRITE dists_i[0] by thread 0 (iteration j+1)
    __syncthreads();
    if (block_size >= 1024) { if (tid < 512) { __update(dists, dists_i, tid, tid + 512); } __syncthreads(); } if (block_size >= 512) { if (tid < 256) { __update(dists, dists_i, tid, tid + 256); } __syncthreads(); }
    if (block_size >= 256) { if (tid < 128) { __update(dists, dists_i, tid, tid + 128); } __syncthreads(); } if (block_size >= 128) { if (tid < 64) { __update(dists, dists_i, tid, tid + 64); } __syncthreads(); }
    if (block_size >= 64) { if (tid < 32) { __update(dists, dists_i, tid, tid + 32); } __syncthreads(); } if (block_size >= 32) { if (tid < 16) { __update(dists, dists_i, tid, tid + 16); } __syncthreads(); }
    if (block_size >= 16) { if (tid < 8) { __update(dists, dists_i, tid, tid + 8); } __syncthreads(); } if (block_size >= 8) { if (tid < 4) { __update(dists, dists_i, tid, tid + 4); } __syncthreads(); }
    if (block_size >= 4) { if (tid < 2) { __update(dists, dists_i, tid, tid + 2); } __syncthreads(); } if (block_size >= 2) { if (tid < 1) { __update(dists, dists_i, tid, tid + 1); } __syncthreads(); }
    if (tid >= 32 && tid < 64) delay(200000);  // PERTURB: warp 1 reaches the read ~100 us late; thread 0 runs ahead to the write
    old = dists_i[0];  // upstream L212: READ dists_i[0] by every thread (iteration j); no barrier before the next L147
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
  farthest_point_sampling_kernel<1024><<<B, 1024>>>(B, N, M, d, t, ix);
  cudaError_t e = cudaDeviceSynchronize(); cudaMemcpy(o.data(), ix, o.size() * 4, cudaMemcpyDeviceToHost); int bad = check(h.data(), o.data(), B, N, M);
  printf("openpcdet-fps-new-1 PERTURBED fps<1024> B=%d N=%d M=%d %s idx[0..3]=%d,%d,%d,%d invalid=%d/%d -> %s\n", B, N, M, cudaGetErrorString(e), o[0], o[1], o[2], o[3], bad, B * M, bad ? "WRONG OUTPUT" : "OK");
  return bad ? 1 : 0; }

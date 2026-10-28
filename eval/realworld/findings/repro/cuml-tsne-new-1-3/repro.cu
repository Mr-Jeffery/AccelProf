// cuml-tsne-new-1-3 reproducer. Kernel copied from ML::TSNE::BH::BoundingBoxKernel, rapidsai/cuml c7e7738bb6386186bc031d821e71ce1c1abfe3c8
// cpp/src/tsne/barnes_hut_kernels.cuh L81-L142: the shared-memory min/max reduction whose __syncthreads sits inside
// `for (j = THREADS1 / 2; j > i; j /= 2)`, a loop whose trip count depends on threadIdx.x. Launched <<<FACTOR1 * SMs, THREADS1>>>
// (barnes_hut_tsne.cuh). Trimmed: the cross-block combine L143-L166 (__threadfence, atomicInc, last block) and the unused
// pointer arguments; each block's thread 0 writes its result (L139-L142) and the host checks every block.
#include <cstdio>
#include <cmath>
#define THREADS1 512
#define FACTOR1 3
__global__ __launch_bounds__(THREADS1) void BoundingBoxKernel(float* posxd, float* posyd, float* maxxd, float* maxyd,
                                                               float* minxd, float* minyd, const int N) {
  float val, minx, maxx, miny, maxy;
  __shared__ float sminx[THREADS1], smaxx[THREADS1], sminy[THREADS1], smaxy[THREADS1];
  minx = maxx = posxd[0];
  miny = maxy = posyd[0];
  const auto i   = threadIdx.x;
  const auto inc = THREADS1 * gridDim.x;
  for (auto j = i + blockIdx.x * THREADS1; j < N; j += inc) {
    val = posxd[j];
    if (val < minx) minx = val; else if (val > maxx) maxx = val;
    val = posyd[j];
    if (val < miny) miny = val; else if (val > maxy) maxy = val;
  }
  sminx[i] = minx; smaxx[i] = maxx; sminy[i] = miny; smaxy[i] = maxy;           // L122-L125
  for (auto j = THREADS1 / 2; j > i; j /= 2) {                                  // L127
    __syncthreads();                                                             // L128
    const auto k = i + j;
    sminx[i] = minx = fminf(minx, sminx[k]);                                     // L130
    smaxx[i] = maxx = fmaxf(maxx, smaxx[k]);
    sminy[i] = miny = fminf(miny, sminy[k]);
    smaxy[i] = maxy = fmaxf(maxy, smaxy[k]);                                     // L133
  }
  if (i == 0) {
    const auto k = blockIdx.x;
    minxd[k] = minx; maxxd[k] = maxx; minyd[k] = miny; maxyd[k] = maxy;          // L139-L142
  }
}
int main() {
  int sms = 0; cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0);
  const int N = 1 << 20, G = FACTOR1 * sms, reps = 20; float *hx = new float[N], *hy = new float[N], *r = new float[4 * G], *o = new float[4 * G];
  unsigned s = 7u; for (int j = 0; j < N; j++) { s = s * 1664525u + 1013904223u; hx[j] = (s >> 8) / 1e5f; s = s * 1664525u + 1013904223u; hy[j] = (s >> 8) / 1e5f; }
  for (int b = 0; b < G; b++) { r[b] = hx[0]; r[G + b] = hy[0]; r[2 * G + b] = hx[0]; r[3 * G + b] = hy[0]; }   // max x, max y, min x, min y
  for (int j = 0; j < N; j++) { int b = (j / THREADS1) % G; r[b] = fmaxf(r[b], hx[j]); r[G + b] = fmaxf(r[G + b], hy[j]); r[2 * G + b] = fminf(r[2 * G + b], hx[j]); r[3 * G + b] = fminf(r[3 * G + b], hy[j]); }
  float *dx, *dy, *dr; cudaMalloc(&dx, N * 4); cudaMalloc(&dy, N * 4); cudaMalloc(&dr, 16 * G);
  cudaMemcpy(dx, hx, N * 4, cudaMemcpyHostToDevice); cudaMemcpy(dy, hy, N * 4, cudaMemcpyHostToDevice); int bad_runs = 0, bad = 0;
  for (int k = 0; k < reps; k++) {
    cudaMemset(dr, 0, 16 * G); BoundingBoxKernel<<<G, THREADS1>>>(dx, dy, dr, dr + G, dr + 2 * G, dr + 3 * G, N);
    cudaMemcpy(o, dr, 16 * G, cudaMemcpyDeviceToHost);
    int b = 0; for (int q = 0; q < 4 * G; q++) b += o[q] != r[q]; bad_runs += b != 0; bad += b;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("cuml-tsne-new-1-3 N=%d grid=%d block=%d reps=%d runs_with_mismatches=%d total_mismatches=%d err=%s\n", N, G, THREADS1, reps, bad_runs, bad, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

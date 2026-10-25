// droidslam-new-1 reproducer.  warpReduce / blockReduce are copied verbatim from DROID-SLAM 2dfd39f0dcad44012ca7bbb8aa70b55edbfa9c99
// src/droid_kernels.cu L45-L64.  The kernel keeps frame_distance_kernel's reduction tail (L570 accum[thread_id] = ..., L657
// "__syncthreads(); blockReduce(accum);", L663-L664 thread 0 reads accum[0]).  Trimmed: the pose/projection math and the pixel
// loop (L539-L656), which only produce the per-thread partial sums; here accum[] is filled with known integers instead.
#include <cstdio>
#define THREADS 256

__device__ void warpReduce(volatile float *sdata, unsigned int tid) {
  sdata[tid] += sdata[tid + 32];
  sdata[tid] += sdata[tid + 16];
  sdata[tid] += sdata[tid +  8];
  sdata[tid] += sdata[tid +  4];
  sdata[tid] += sdata[tid +  2];
  sdata[tid] += sdata[tid +  1];
}

__device__ void blockReduce(volatile float *sdata) {
  unsigned int tid = threadIdx.x;
  __syncthreads();

  // if (threadIdx.x < 256) {sdata[tid] += sdata[tid + 256]; } __syncthreads();
  if (threadIdx.x < 128) {sdata[tid] += sdata[tid + 128]; } __syncthreads();
  if (threadIdx.x <  64) {sdata[tid] += sdata[tid +  64]; } __syncthreads();

  if (tid < 32) warpReduce(sdata, tid);
  __syncthreads();
}

__global__ void frame_distance_tail(float *dist) {
  __shared__ float accum[THREADS];
  accum[threadIdx.x] = (float)(threadIdx.x % 7 + 1 + blockIdx.x % 5);   // stands in for the pixel loop's partial sums
  __syncthreads(); blockReduce(accum);
  __syncthreads();
  if (threadIdx.x == 0) dist[blockIdx.x] = accum[0];
}

int main() {
  const int NB = 4096;
  float *d, h[NB];
  cudaMalloc(&d, NB * sizeof(float));
  frame_distance_tail<<<NB, THREADS>>>(d);
  if (cudaDeviceSynchronize() != cudaSuccess) { printf("CUDA error\n"); return 2; }
  cudaMemcpy(h, d, sizeof h, cudaMemcpyDeviceToHost);
  int wrong = 0;
  for (int b = 0; b < NB; ++b) {
    float ref = 0; for (int t = 0; t < THREADS; ++t) ref += (float)(t % 7 + 1 + b % 5);   // exact: integers < 2^24
    if (h[b] != ref) { if (wrong < 5) printf("block %d: got %g expected %g\n", b, h[b], ref); ++wrong; }
  }
  printf("droidslam-new-1 repro: blocks=%d wrong=%d -> %s\n", NB, wrong, wrong ? "WRONG OUTPUT" : "output correct");
  return 0;
}

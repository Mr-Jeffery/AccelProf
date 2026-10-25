// droidslam-new-1 perturbation test: repro.cu (DROID-SLAM 2dfd39f0 warpReduce/blockReduce, verbatim) with __nanosleep on the
// WRITER side of the L46->L47 RAW: lane 16 is delayed before its L46 store sdata[16] += sdata[48]; lane 0 reads sdata[16] at L47.
//   mode 1 (faithful): "if (tid == 16) __nanosleep(NS);" inserted as the first statement of warpReduce.  ptxas reconverges the
//          warp after the if (or predicates it), so the six steps still run converged: expected output correct.
//   mode 2 (forced divergence, a schedule PTX allows): lane 16 enters warpReduce through its own call (warpReduceP<1>, noinline,
//          identical body), so the other 31 lanes run all six steps without it: expected WRONG output (sdata[48] etc. missed).
//   mode 0: no perturbation.  Usage: repro_perturb [mode=1] [ns=100000]
#include <cstdio>
#include <cstdlib>
#define THREADS 256

template <int P> __device__ __noinline__ void warpReduceP(volatile float *sdata, unsigned int tid, int mode, unsigned ns) {
  if (P == 0 && mode == 1 && tid == 16) __nanosleep(ns);          // perturbation (mode 1); the six lines below are L46-L51
  sdata[tid] += sdata[tid + 32];
  sdata[tid] += sdata[tid + 16];
  sdata[tid] += sdata[tid +  8];
  sdata[tid] += sdata[tid +  4];
  sdata[tid] += sdata[tid +  2];
  sdata[tid] += sdata[tid +  1];
}

__device__ void blockReduce(volatile float *sdata, int mode, unsigned ns) {
  unsigned int tid = threadIdx.x;
  __syncthreads();
  if (threadIdx.x < 128) {sdata[tid] += sdata[tid + 128]; } __syncthreads();
  if (threadIdx.x <  64) {sdata[tid] += sdata[tid +  64]; } __syncthreads();
  if (mode == 2 && tid == 16) { __nanosleep(ns); warpReduceP<1>(sdata, tid, mode, ns); }   // perturbation (mode 2)
  else if (tid < 32) warpReduceP<0>(sdata, tid, mode, ns);
  __syncthreads();
}

__global__ void frame_distance_tail(float *dist, int mode, unsigned ns) {
  __shared__ float accum[THREADS];
  accum[threadIdx.x] = (float)(threadIdx.x % 7 + 1 + blockIdx.x % 5);
  __syncthreads(); blockReduce(accum, mode, ns);
  __syncthreads();
  if (threadIdx.x == 0) dist[blockIdx.x] = accum[0];
}

int main(int argc, char **argv) {
  const int mode = argc > 1 ? atoi(argv[1]) : 1;  const unsigned ns = argc > 2 ? atoi(argv[2]) : 100000;
  const int NB = 1024;
  float *d, h[NB];
  cudaMalloc(&d, NB * sizeof(float));
  frame_distance_tail<<<NB, THREADS>>>(d, mode, ns);
  if (cudaDeviceSynchronize() != cudaSuccess) { printf("CUDA error\n"); return 2; }
  cudaMemcpy(h, d, sizeof h, cudaMemcpyDeviceToHost);
  int wrong = 0;
  for (int b = 0; b < NB; ++b) {
    float ref = 0; for (int t = 0; t < THREADS; ++t) ref += (float)(t % 7 + 1 + b % 5);
    if (h[b] != ref) { if (wrong < 3) printf("block %d: got %g expected %g\n", b, h[b], ref); ++wrong; }
  }
  printf("droidslam-new-1 perturb mode=%d ns=%u: blocks=%d wrong=%d -> %s\n", mode, ns, NB, wrong, wrong ? "WRONG OUTPUT" : "output correct");
  return 0;
}

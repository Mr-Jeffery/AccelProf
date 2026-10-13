// barrier_exited_threads.cu (T3, eval/CRS_CUDA_TRIAGE.md): the HeCBench crs-cuda idiom.
// With w = 5 and 128 threads per block, threads 125..127 return before the loop's
// __syncthreads(). A thread that has exited no longer takes part in a CTA barrier, so the
// barrier completes for the 125 that remain: every store to s[] is ordered before the
// group's loads of it, and the kernel is race-free (crs-cuda's gcrs_m_1_w_5_coding_dotprod).
#include <cstdio>
#include <cuda_runtime.h>

__global__ void dotprod(const long* in, long* out, int k, int size) {
  extern __shared__ long s[];
  const int w = 5;
  const int work = blockDim.x / w * w;
  const unsigned idx = work * blockIdx.x + threadIdx.x;
  if (threadIdx.x >= work) return;
  if (idx >= size) return;
  const int group = (threadIdx.x / w) * w;
  long r = 0;
  for (int i = 0; i < k; i++) {
    s[threadIdx.x] = in[i * size + idx];
    __syncthreads();
    for (int j = 0; j < w; j++) r ^= s[group + j];
    __syncthreads();
  }
  out[idx] = r;
}

int main() {
  const int k = 2, blocks = 2, threads = 128, size = blocks * (threads / 5 * 5);
  long *in, *out;
  cudaMalloc(&in, sizeof(long) * k * size);
  cudaMalloc(&out, sizeof(long) * size);
  cudaMemset(in, 1, sizeof(long) * k * size);
  dotprod<<<blocks, threads, threads * sizeof(long)>>>(in, out, k, size);
  cudaError_t e = cudaDeviceSynchronize();
  printf("barrier_exited_threads: %s\n", cudaGetErrorString(e));
  return e != cudaSuccess;
}

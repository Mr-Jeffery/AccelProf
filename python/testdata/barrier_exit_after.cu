// barrier_exit_after.cu (T3b, positive control of python/test_barrier_exit.py): a thread
// that exits AFTER a __syncthreads() took part in it. 64 threads per block, 2 blocks. Every
// thread writes its slot of s[] and arrives at barrier 1; threads 60..63 then return; the
// rest read the slot of thread 63 - tid (threads 0..3 read the slots of the exited threads),
// meet at barrier 2 (which completes for the 60 that remain) and overwrite their own slot.
// Race-free: barrier 1 orders every write before every read (the exited threads arrived at
// it), barrier 2 orders every read before the overwrites.
#include <cstdio>
#include <cuda_runtime.h>

__global__ void exit_after(int* out) {
  __shared__ int s[64];
  s[threadIdx.x] = threadIdx.x + blockIdx.x;
  __syncthreads();
  if (threadIdx.x >= 60) return;
  const int r = s[63 - threadIdx.x];
  __syncthreads();
  s[threadIdx.x] = r;
  out[blockIdx.x * 64 + threadIdx.x] = r;
}

int main() {
  int* out;
  cudaMalloc(&out, sizeof(int) * 128);
  exit_after<<<2, 64>>>(out);
  cudaError_t e = cudaDeviceSynchronize();
  printf("barrier_exit_after: %s\n", cudaGetErrorString(e));
  return e != cudaSuccess;
}

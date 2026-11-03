// Probe: lowering of cutlass::Semaphore (v4.8.1) split-K serial hand-off on sm_89.
#include "cutlass/semaphore.h"

__global__ void probe(int *lock, float *D, int nk) {
  int k = blockIdx.z;
  cutlass::Semaphore semaphore(lock + blockIdx.x, threadIdx.x);
  if (nk > 1) semaphore.fetch();
  float acc = threadIdx.x * 1.0f;
  if (nk > 1) semaphore.wait(k);
  float *p = D + blockIdx.x * blockDim.x + threadIdx.x;
  float src = k ? *p : 0.f;   // source load (D for k>0)
  *p = src + acc;             // epilogue store
  if (nk > 1) semaphore.release(nk == k + 1 ? 0 : k + 1);
}

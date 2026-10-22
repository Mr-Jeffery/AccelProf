// T24 (eval/SYNCWARP_INSTANCE.md): X5b's counterfactual (eval/X5_BYTE_PAIRS.md section 4) as a
// kernel of its own. The shape is ECL-CC's cc_vertex_data (Indigo3Suite CC-CUDA, X5b section 2.1):
// lane 0 clears the warp's flag updated[warp], another lane of the warp sets it, and every lane
// reads it after a __syncwarp(). The first __syncwarp() of that kernel (between the clear and the
// sets) is removed, and the warp reaches the remaining one diverged, in two groups at one call
// site: lanes 0..15 in round 0, lanes 16..31 in round 1. Compute Sanitizer then reports the
// WARPSYNC once per group: two `syncwarp` records, sync_mask 0xffffffff, active masks 0x0000ffff
// and 0xffff0000.
//
// FIRST_SYNCWARP=1 (testdata/syncwarp_converged_clean.cu) puts the first __syncwarp() back: the
// positive control, where a converged __syncwarp() orders the clear before the set.
//
// Without it, the clear (lane 0, before its group's arrival) and the set (lane 16, before its
// group's arrival) are unordered: the WAW on updated[warp] is a data race. A join of every lane of
// sync_mask at the FIRST group's record orders them (the per-record join of 38af04e); the warp
// barrier instance, complete at the second group's record, does not.
#include <cstdio>
#include <cuda_runtime.h>

#ifndef FIRST_SYNCWARP
#define FIRST_SYNCWARP 0
#endif
#define TPB 64
#define BLOCKS 4

__global__ void cc_vertex_data(const int* nlab, int* out) {
  __shared__ bool updated[TPB / 32];
  const int lane = threadIdx.x % 32, warp = threadIdx.x / 32;
  const int v = blockIdx.x * TPB + threadIdx.x;
  if (lane == 0) updated[warp] = false;                       // clear (u of the WAW)
#if FIRST_SYNCWARP
  __syncwarp();                                               // converged: orders the clear
#endif
#pragma unroll 1
  for (int round = 0; round < 2; ++round) {
    if ((lane < 16) == (round == 0)) {                        // lanes 0..15, then 16..31
      if (lane == 16 && nlab[v] >= 0) updated[warp] = true;   // set (v of the WAW)
      __syncwarp();                                           // one call site, two groups
    }
  }
  if (updated[warp]) out[v] = 1;                              // read
}

int main() {
  int *nlab = nullptr, *out = nullptr;
  cudaMalloc(&nlab, BLOCKS * TPB * sizeof(int));
  cudaMalloc(&out, BLOCKS * TPB * sizeof(int));
  cudaMemset(nlab, 0, BLOCKS * TPB * sizeof(int));
  cudaMemset(out, 0, BLOCKS * TPB * sizeof(int));
  cc_vertex_data<<<BLOCKS, TPB>>>(nlab, out);
  int h[BLOCKS * TPB];
  cudaMemcpy(h, out, sizeof(h), cudaMemcpyDeviceToHost);
  const cudaError_t e = cudaDeviceSynchronize();
  int n = 0;
  for (int k = 0; k < BLOCKS * TPB; ++k) n += h[k];
  printf("cc_vertex_data: %d of %d set, %s\n", n, BLOCKS * TPB, cudaGetErrorString(e));
  cudaFree(nlab);
  cudaFree(out);
  return e == cudaSuccess ? 0 : 1;
}

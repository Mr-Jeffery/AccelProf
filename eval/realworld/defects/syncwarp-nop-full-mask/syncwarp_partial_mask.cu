// Minimal failing input (T21b triage, cccl-1): a __syncwarp with a partial constant mask inside a
// divergent branch. ptxas lowers it to `BRA.CONV UR, skip; CALL $__cuda_sm70_warpsync; skip: NOP`.
// Every kernel below is race-free: each lane reads s[t] and, after __syncwarp(mask), lane t+1
// overwrites it (WAR), so the warp barrier orders every conflicting pair.
#include <cstdio>
#define N 22                                   // as cub RAKING_THREADS for BlockReduce<uint8_t,65>
#define MASK ((1u << N) - 1)                   // 0x3fffff, as cub WARP_SYNC((1<<RAKING_THREADS)-1)

// (A) the failing form: partial mask, lanes N..31 diverged away
__global__ void partial_mask(int *out) {
  __shared__ int s[32];
  int t = threadIdx.x;
  s[t] = t;
  __syncthreads();
  if (t < N) {
    int v = s[t];                              // read s[t]
    __syncwarp(MASK);
    s[(t + 1) % N] = v + 1;                    // write s[t+1]: WAR with lane t+1's read, ordered
    __syncwarp(MASK);
    out[t] = s[t];
  }
  // lanes N..31 stay alive (parked at the reconvergence point) until here, as in cub BlockReduce
  if (t == 0) out[32] = t;
}

// (B) control: full mask, converged warp (same accesses, all 32 lanes)
__global__ void full_mask(int *out) {
  __shared__ int s[32];
  int t = threadIdx.x;
  s[t] = t;
  __syncthreads();
  int v = s[t];
  __syncwarp();
  s[(t + 1) % 32] = v + 1;
  __syncwarp();
  out[t] = s[t];
}

int main() {
  int *d; cudaMalloc(&d, 33 * sizeof(int));
  partial_mask<<<1, 32>>>(d);
  full_mask<<<1, 32>>>(d);
  cudaError_t e = cudaDeviceSynchronize();
  int h[32]; cudaMemcpy(h, d, sizeof h, cudaMemcpyDeviceToHost);
  printf("%s out[0]=%d\n", cudaGetErrorString(e), h[0]);
  return 0;
}

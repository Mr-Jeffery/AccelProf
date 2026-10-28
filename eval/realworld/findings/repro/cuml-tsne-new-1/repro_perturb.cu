// cuml-tsne-new-1 PERTURBED reproducer (repro.cu + __nanosleep before the L596 copy in warp 0 and in lanes 16..31 of every warp). Kernel = the prologue of ML::TSNE::BH::RepulsionKernel, rapidsai/cuml
// c7e7738bb6386186bc031d821e71ce1c1abfe3c8 cpp/src/tsne/barnes_hut_kernels.cuh L565-L599 (dq table built by thread 0, __syncthreads,
// per-warp copy dq[diff + sbase] = dq[diff] with the __syncthreads commented out, __threadfence_block), launched like
// barnes_hut_tsne.cuh L266 (<<<blocks * FACTOR5, THREADS5>>>, FACTOR5 = 2, THREADS5 = 1024, blocks = SM count).
// Trimmed: the tree walk L601-L678 is replaced by a walk over the levels that reads dq[depth] exactly as L647 does
// (depth = sbase .. sbase + max_depth - 1); pos/node (unused here) are dropped; value_t = float.
#include <cstdio>
#include <cmath>
#define THREADS5 1024
__global__ void repulsion_prologue(const float epssqd, const float theta_squared, const float* radiusd_squared,
                                   const int* maxdepthd, float* out) {
  __shared__ float dq[THREADS5];                                     // L568
  if (threadIdx.x == 0) {                                            // L570-L583
    const auto max_depth = maxdepthd[0];
    dq[0]                = __fdividef(radiusd_squared[0], theta_squared);
    for (auto i = 1; i < max_depth; i++) { dq[i] = dq[i - 1] * 0.25f; dq[i - 1] += epssqd; }
    dq[max_depth - 1] += epssqd;
    for (auto i = 0; i < max_depth; i++) dq[i] += 1.0f;
  }
  __syncthreads();                                                   // L585
  const int sbase = (threadIdx.x / 32) * 32;                         // L589
  const int diff = threadIdx.x - sbase;                              // L592
  if (sbase == 0 || diff >= 16) { __nanosleep(100000); dq[diff + sbase] = dq[diff]; } else { dq[diff + sbase] = dq[diff]; }  // L596 + PERTURB
  //__syncthreads();                                                 // L598 (commented out upstream)
  __threadfence_block();                                             // L599
  float acc = 0.0f;                                                  // trimmed walk: the dq[depth] reads of L647
  for (int depth = sbase; depth < sbase + maxdepthd[0]; depth++) acc += dq[depth];
  out[blockIdx.x * blockDim.x + threadIdx.x] = acc;
}
int main() {
  int sms = 0; cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0);
  const int grid = sms * 2, nt = grid * THREADS5, reps = 20, md = 12;      // max depth <= 32 (TreeBuildingKernel L321)
  const float r2 = 0.37f, th2 = 0.25f, eps = 0.0025f;                       // radius^2, theta^2 (0.5^2), epssq (TSNEParams)
  float *dr2, *out, *h = new float[nt]; int *dmd; cudaMalloc(&dr2, 4); cudaMalloc(&dmd, 4); cudaMalloc(&out, nt * 4);
  cudaMemcpy(dr2, &r2, 4, cudaMemcpyHostToDevice); cudaMemcpy(dmd, &md, 4, cudaMemcpyHostToDevice);
  double q[32], ref = 0; q[0] = r2 / th2; for (int i = 1; i < md; i++) { q[i] = q[i-1] * 0.25; q[i-1] += eps; } q[md-1] += eps;
  for (int i = 0; i < md; i++) ref += q[i] + 1.0;
  int bad_runs = 0, bad = 0;
  for (int r = 0; r < reps; r++) {
    repulsion_prologue<<<grid, THREADS5>>>(eps, th2, dr2, dmd, out);
    cudaMemcpy(h, out, nt * 4, cudaMemcpyDeviceToHost);
    int b = 0; for (int i = 0; i < nt; i++) b += (h[i] != h[0]) || fabs(h[i] - ref) > 1e-4 * ref;   // every warp's copy must equal warp 0's
    bad_runs += b != 0; bad += b;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("cuml-tsne-new-1 grid=%d block=%d reps=%d acc[0]=%.7g ref=%.7g runs_with_mismatches=%d total_mismatches=%d err=%s\n", grid, THREADS5, reps, h[0], ref, bad_runs, bad, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

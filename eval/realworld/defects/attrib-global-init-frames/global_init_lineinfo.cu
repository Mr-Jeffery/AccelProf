// Minimal failing input (T21b triage, lit-fbgemm-1): a cubin whose last .text section is followed by
// .nv.global.init (an initialised __device__ array, as curand's mrg32k3a tables in fbgemm's fast_gemv.cu).
// `nvdisasm --print-line-info-inline <cubin>` (no -c) prints that section's bytes as "/*OFFSET*/ .byte ..."
// lines; rw_attribute.cubin_frames keeps the last .text function current there, so every pc of the kernel
// below that is also an offset of the data dump gets the frames of the kernel's last //## group.
#include <cstdio>
__device__ unsigned int table[4096] = {1};     // 16 KiB of .nv.global.init: covers offsets 0x0000-0x3ff0

__global__ void k(unsigned int *out) {
  __shared__ unsigned int s[256];
  unsigned int t = threadIdx.x;
  s[t] = t;                                    // STS: expected frame global_init_lineinfo.cu:12
  __syncthreads();
  out[t] = s[255 - t] + table[t];              // LDS: expected frame global_init_lineinfo.cu:14
}

int main() {
  unsigned int *d; cudaMalloc(&d, 256 * sizeof(unsigned int));
  k<<<1, 256>>>(d);
  printf("%s\n", cudaGetErrorString(cudaDeviceSynchronize()));
  return 0;
}

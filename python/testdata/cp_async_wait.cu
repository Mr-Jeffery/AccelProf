// cp_async_wait.cu (T1a, eval/CP_ASYNC_REPORT.md): cp.async (LDGSTS) global->shared copies and
// the waits that complete them. Every thread copies its own element and then reads it.
//   default    the read comes BEFORE cp.async.wait_all            -> race (copy vs the read)
//   -DFIXED    the read comes after cp.async.wait_all             -> no race
//   -DGROUPS   two commit groups (A -> s[t], B -> s[64+t]), then cp.async.wait_group 1: A is
//              complete, B may still be in flight -> reading s[t] is ordered, s[64+t] races
#include <cstdio>
#include <cuda_runtime.h>

__device__ __forceinline__ void cp_async4(void* smem, const void* gmem) {
  unsigned s = static_cast<unsigned>(__cvta_generic_to_shared(smem));
  asm volatile("cp.async.ca.shared.global [%0], [%1], 4;\n" :: "r"(s), "l"(gmem) : "memory");
}

__global__ void copy_then_read(const int* in, int* out) {
  __shared__ int s[128];
  const int t = threadIdx.x;
#ifdef GROUPS
  cp_async4(&s[t], &in[t]);
  asm volatile("cp.async.commit_group;\n" ::: "memory");
  cp_async4(&s[64 + t], &in[64 + t]);
  asm volatile("cp.async.commit_group;\n" ::: "memory");
  asm volatile("cp.async.wait_group 1;\n" ::: "memory");
  out[t] = s[t];              // group A: complete
  out[64 + t] = s[64 + t];    // group B: may still be in flight
  asm volatile("cp.async.wait_group 0;\n" ::: "memory");
#else
  cp_async4(&s[t], &in[t]);
#ifdef FIXED
  asm volatile("cp.async.wait_all;\n" ::: "memory");
  out[t] = s[t];
#else
  out[t] = s[t];              // read before the copy is waited for
  asm volatile("cp.async.wait_all;\n" ::: "memory");
#endif
#endif
}

int main() {
  int *in, *out;
  cudaMalloc(&in, 128 * sizeof(int));
  cudaMalloc(&out, 128 * sizeof(int));
  cudaMemset(in, 1, 128 * sizeof(int));
  copy_then_read<<<1, 64>>>(in, out);
  cudaError_t e = cudaDeviceSynchronize();
  printf("cp_async_wait: %s\n", cudaGetErrorString(e));
  return e != cudaSuccess;
}

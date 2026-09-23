// cp_async_wait.cu (T1a, eval/CP_ASYNC_REPORT.md): cp.async (LDGSTS) global->shared copies and
// the waits that complete them. 64 threads (two warps); every thread copies its own element.
//   default    the read comes BEFORE cp.async.wait_all            -> race (copy vs the read)
//   -DFIXED    the read comes after cp.async.wait_all             -> no race
//   -DGROUPS   two commit groups (A -> s[t], B -> s[64+t]), then cp.async.wait_group 1: A is
//              complete, B may still be in flight -> reading s[t] is ordered, s[64+t] races
// T1a review (a barrier does not complete a copy; two copies are unordered; a
// copy completed through an mbarrier):
//   -DBARRIER  __syncthreads() between the copy and a read of the OTHER warp's element (with
//              -DOWN: of the thread's own element), the wait after the read -> race; with
//              -DFIXED the wait comes before the barrier. (A __syncwarp() would do too, but
//              on a converged warp it compiles to a NOP.)
//   -DTWICE    two copies of one thread into s[t] in two groups, no wait between -> race
//              (write-write); with -DFIXED a wait_group 0 separates them
//   -DMBARRIER cuda::memcpy_async completed through a cuda::barrier (cp.async.mbarrier.arrive):
//              the read after arrive_and_wait is ordered -> no race
#include <cstdio>
#include <cuda_runtime.h>
#ifdef MBARRIER
#include <cuda/barrier>
#endif

__device__ __forceinline__ void cp_async4(void* smem, const void* gmem) {
  unsigned s = static_cast<unsigned>(__cvta_generic_to_shared(smem));
  asm volatile("cp.async.ca.shared.global [%0], [%1], 4;\n" :: "r"(s), "l"(gmem) : "memory");
}
#define COMMIT() asm volatile("cp.async.commit_group;\n" ::: "memory")
#define WAIT_ALL() asm volatile("cp.async.wait_all;\n" ::: "memory")

__global__ void copy_then_read(const int* in, int* out) {
  __shared__ int s[128];
  const int t = threadIdx.x;
#if defined(GROUPS)
  cp_async4(&s[t], &in[t]);
  COMMIT();
  cp_async4(&s[64 + t], &in[64 + t]);
  COMMIT();
  asm volatile("cp.async.wait_group 1;\n" ::: "memory");
  out[t] = s[t];              // group A: complete
  out[64 + t] = s[64 + t];    // group B: may still be in flight
  asm volatile("cp.async.wait_group 0;\n" ::: "memory");
#elif defined(BARRIER)
#ifdef OWN
  const int r = t;            // the thread's own element
#else
  const int r = t ^ 32;       // the other warp's element
#endif
  cp_async4(&s[t], &in[t]);
#ifdef FIXED
  WAIT_ALL();
  __syncthreads();
  out[t] = s[r];
#else
  __syncthreads();            // completes no copy: it publishes nothing about one in flight
  out[t] = s[r];              // the copy may not have landed
  WAIT_ALL();
#endif
#elif defined(TWICE)
  cp_async4(&s[t], &in[t]);
  COMMIT();
#ifdef FIXED
  asm volatile("cp.async.wait_group 0;\n" ::: "memory");
#endif
  cp_async4(&s[t], &in[64 + t]);   // unordered with the first copy unless it was waited for
  COMMIT();
  WAIT_ALL();
  out[t] = s[t];
#elif defined(MBARRIER)
  __shared__ cuda::barrier<cuda::thread_scope_block> bar;
  if (t == 0) init(&bar, blockDim.x);
  __syncthreads();
  cuda::memcpy_async(&s[t], &in[t], cuda::aligned_size_t<4>(sizeof(int)), bar);
  bar.arrive_and_wait();      // completes the copy (and orders it for every thread)
  out[t] = s[t];
#else
  cp_async4(&s[t], &in[t]);
#ifdef FIXED
  WAIT_ALL();
  out[t] = s[t];
#else
  out[t] = s[t];              // read before the copy is waited for
  WAIT_ALL();
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

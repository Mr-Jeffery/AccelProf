// T10: what SASS do the strong load/store forms lower to on this toolchain (sm_89, CUDA 13.3)?
// ld/st.relaxed.{cta,gpu,sys}.global, volatile global and shared, ld/st.relaxed.cta.shared,
// cuda::atomic_ref block/device relaxed load/store. Built by lowering_probe.sh; never run.
#include <cuda/atomic>
#include <cstdio>

__device__ __forceinline__ void st_cta_g(unsigned *p, unsigned v) { asm volatile("st.relaxed.cta.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void st_gpu_g(unsigned *p, unsigned v) { asm volatile("st.relaxed.gpu.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void st_sys_g(unsigned *p, unsigned v) { asm volatile("st.relaxed.sys.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ unsigned ld_cta_g(unsigned *p) { unsigned v; asm volatile("ld.relaxed.cta.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_gpu_g(unsigned *p) { unsigned v; asm volatile("ld.relaxed.gpu.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_sys_g(unsigned *p) { unsigned v; asm volatile("ld.relaxed.sys.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }

__global__ void probe(unsigned *g, unsigned *out) {
    __shared__ unsigned s[64];
    unsigned t = threadIdx.x;
    st_cta_g(g + 0, t); out[0] = ld_cta_g(g + 1);
    st_gpu_g(g + 2, t); out[1] = ld_gpu_g(g + 3);
    st_sys_g(g + 4, t); out[2] = ld_sys_g(g + 5);
    ((volatile unsigned *)g)[6] = t; out[3] = ((volatile unsigned *)g)[7];
    ((volatile unsigned *)s)[t] = t; __syncthreads(); out[4] = ((volatile unsigned *)s)[63 - t];
    unsigned v;
    asm volatile("st.relaxed.cta.shared.u32 [%0], %1;" :: "r"((unsigned)__cvta_generic_to_shared(&s[t])), "r"(t) : "memory");
    asm volatile("ld.relaxed.cta.shared.u32 %0, [%1];" : "=r"(v) : "r"((unsigned)__cvta_generic_to_shared(&s[63 - t])) : "memory");
    out[5] = v;
    cuda::atomic_ref<unsigned, cuda::thread_scope_block> ab(g[8]);
    ab.store(t, cuda::memory_order_relaxed); out[6] = ab.load(cuda::memory_order_relaxed);
    cuda::atomic_ref<unsigned, cuda::thread_scope_device> ad(g[9]);
    ad.store(t, cuda::memory_order_relaxed); out[7] = ad.load(cuda::memory_order_relaxed);
}

int main() { unsigned *g, *o; cudaMalloc(&g, 64 * 4); cudaMalloc(&o, 64 * 4); probe<<<1, 64>>>(g, o); cudaDeviceSynchronize(); printf("ok\n"); return 0; }

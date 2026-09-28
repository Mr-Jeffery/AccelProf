// T10 (D9): one strong-store / strong-load litmus per scope. The accesses are PTX
// ld/st.relaxed.<scope>.global, which lower on sm_89 (CUDA 13.3) to the address-spaced
// LDG/STG.E.STRONG.{SM,GPU,SYS} -- the form the pre-T10 `generic` policy called weak (it is
// also what `volatile` lowers to, at SYS). Each pair is unsynchronized, so it is reportable;
// its class is the definition's (hb_proof.tex Definitions "Scope inclusion, moral strength"
// and "Verdicts"): morally strong iff both accesses are strong and each scope covers the
// other thread.
//
//   <scope>_interwarp   thread 0 stores, thread 32 (warp 1, same block) loads -> SC at every
//                       scope (cta covers the block)
//   <scope>_interblock  block 1 stores, block 0 loads                        -> SC for gpu
//                       and sys, DR for cta (cta does not cover another block)
//   plain_interblock    the same with a plain STG.E / LDG.E                   -> DR (control)
//
// Under the pre-T10 `generic` policy every strong pair here is weak and a DR. The load
// waits ~10 ms (clock64, no memory access) so that the store comes first in the trace.
// Build:  nvcc -arch=native -lineinfo --cudart shared strong_ldst_scopes.cu
#include <cstdio>

#define STRONG(scope)                                                                      \
    __device__ __forceinline__ void st_##scope(unsigned* p, unsigned v) {                  \
        asm volatile("st.relaxed." #scope ".global.u32 [%0], %1;" :: "l"(p), "r"(v)         \
                     : "memory");                                                          \
    }                                                                                      \
    __device__ __forceinline__ unsigned ld_##scope(unsigned* p) {                          \
        unsigned v;                                                                        \
        asm volatile("ld.relaxed." #scope ".global.u32 %0, [%1];" : "=r"(v) : "l"(p)        \
                     : "memory");                                                          \
        return v;                                                                          \
    }
STRONG(cta)
STRONG(gpu)
STRONG(sys)

__device__ __forceinline__ void spin() {
    const long long t0 = clock64();
    while (clock64() - t0 < 20000000LL) {}
}

#define LITMUS(scope)                                                                      \
    __global__ void scope##_interwarp(unsigned* x, unsigned* out) {                        \
        if (threadIdx.x == 0) st_##scope(x, 1);                                            \
        else if (threadIdx.x == 32) { spin(); out[0] = ld_##scope(x); }                    \
    }                                                                                      \
    __global__ void scope##_interblock(unsigned* x, unsigned* out) {                       \
        if (threadIdx.x != 0) return;                                                      \
        if (blockIdx.x == 1) st_##scope(x, 1);                                             \
        else { spin(); out[0] = ld_##scope(x); }                                           \
    }
LITMUS(cta)
LITMUS(gpu)
LITMUS(sys)

__global__ void plain_interblock(unsigned* x, unsigned* out) {
    if (threadIdx.x != 0) return;
    if (blockIdx.x == 1) x[0] = 1;
    else { spin(); out[0] = x[0]; }
}

int main() {
    unsigned *x, *out;
    cudaMalloc(&x, 64 * sizeof(unsigned));
    cudaMalloc(&out, 64 * sizeof(unsigned));
    cudaMemset(x, 0, 64 * sizeof(unsigned));
    cta_interwarp<<<1, 64>>>(x, out);     cudaDeviceSynchronize();
    gpu_interwarp<<<1, 64>>>(x, out);     cudaDeviceSynchronize();
    sys_interwarp<<<1, 64>>>(x, out);     cudaDeviceSynchronize();
    cta_interblock<<<2, 32>>>(x, out);    cudaDeviceSynchronize();
    gpu_interblock<<<2, 32>>>(x, out);    cudaDeviceSynchronize();
    sys_interblock<<<2, 32>>>(x, out);    cudaDeviceSynchronize();
    plain_interblock<<<2, 32>>>(x, out);  cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

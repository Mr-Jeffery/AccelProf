// Coherent load/store + barrier-ordered litmus (FP_DIAGNOSIS RC1 / RC2).
//
// RC1: cuda::atomic<T>::load()/store() do not lower to an ATOM* RMW opcode but to an
// ordinary load/store carrying the atomic's coherence scope: LD|ST.E.STRONG.<scope>
// (seq_cst adds a MEMBAR fence in front). A `volatile` access lowers to the same
// qualifier in the address-spaced form LDG/STG. The default --strong-ldst=generic
// policy treats only the generic LD/ST form as a language-level atomic; these kernels
// pin both the verdicts and that lowering assumption:
//
//   atomic_seqcst   cuda::atomic store vs load, seq_cst               -> NORACE
//   atomic_relaxed  Indigo-style cast + memory_order_relaxed          -> NORACE
//   atomic_rmw_load exchange (ATOM* RMW) vs relaxed load              -> NORACE
//   atomic_vs_plain plain store vs relaxed atomic load (Indigo RaceBug) -> RACE
//   volatile_pair   volatile store vs volatile load, unsynchronized   -> RACE
//
// RC2: the shared-memory tree reduction. Read and write sit in one sync region of a
// loop; same-iteration instances are index-disjoint and cross-iteration ones are
// separated by the in-loop barrier — no PC-level static proof, but the engine's
// barrier-only clock orders every observed conflict:
//
//   reduce_barrier    __syncthreads() inside the stride loop           -> NORACE
//   reduce_nobarrier  the same loop without it                         -> RACE
//
// Producer = thread 0 (warp 0), consumer = thread 32 (warp 1): inter-warp distance.
// Build:  nvcc -arch=native -lineinfo --cudart shared coherent_ldst.cu -o <out>
#include <cuda/atomic>
#include <cstdio>

static const int TPB = 64;

__global__ void atomic_seqcst(cuda::atomic<int>* a, int* out) {
    const int t = threadIdx.x;
    if (t == 0) a[0].store(7);
    else if (t == 32) out[t] = a[0].load();
}

__global__ void atomic_relaxed(int* p, int* out) {
    const int t = threadIdx.x;
    if (t == 0) ((cuda::atomic<int>*)p)->store(7, cuda::memory_order_relaxed);
    else if (t == 32) out[t] = ((cuda::atomic<int>*)p)->load(cuda::memory_order_relaxed);
}

__global__ void atomic_rmw_load(int* p, int* out) {
    const int t = threadIdx.x;
    if (t == 0) out[t] = ((cuda::atomic<int>*)p)->exchange(7);
    else if (t == 32) out[t] = ((cuda::atomic<int>*)p)->load(cuda::memory_order_relaxed);
}

__global__ void atomic_vs_plain(int* p, int* out) {
    const int t = threadIdx.x;
    if (t == 0) p[0] = 7;                                            // plain store
    else if (t == 32) out[t] = ((cuda::atomic<int>*)p)->load(cuda::memory_order_relaxed);
}

__global__ void volatile_pair(volatile int* p, int* out) {
    const int t = threadIdx.x;
    if (t == 0) p[0] = 7;
    else if (t == 32) out[t] = p[0];
}

__global__ void reduce_barrier(const int* in, int* out, const int n) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    s[t] = in[t];
    __syncthreads();
    for (int stride = n / 2; stride > 0; stride >>= 1) {   // runtime bound: no unrolling
        if (t < stride) s[t] = s[t] + s[t + stride];
        __syncthreads();
    }
    if (t == 0) out[0] = s[0];
}

__global__ void reduce_nobarrier(const int* in, int* out, const int n) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    s[t] = in[t];
    __syncthreads();
    for (int stride = n / 2; stride > 0; stride >>= 1) {   // runtime bound: no unrolling
        if (t < stride) s[t] = s[t] + s[t + stride];                 // no barrier: races
    }
    __syncthreads();
    if (t == 0) out[0] = s[0];
}

int main() {
    int *p, *out, *in;
    cudaMalloc((void**)&p, sizeof(int) * TPB);
    cudaMalloc((void**)&out, sizeof(int) * TPB);
    cudaMalloc((void**)&in, sizeof(int) * TPB);
    cudaMemset(p, 0, sizeof(int) * TPB);
    cudaMemset(in, 0, sizeof(int) * TPB);
    atomic_seqcst<<<1, TPB>>>((cuda::atomic<int>*)p, out);   cudaDeviceSynchronize();
    atomic_relaxed<<<1, TPB>>>(p, out);                      cudaDeviceSynchronize();
    atomic_rmw_load<<<1, TPB>>>(p, out);                     cudaDeviceSynchronize();
    atomic_vs_plain<<<1, TPB>>>(p, out);                     cudaDeviceSynchronize();
    volatile_pair<<<1, TPB>>>(p, out);                       cudaDeviceSynchronize();
    reduce_barrier<<<1, TPB>>>(in, out, TPB);                   cudaDeviceSynchronize();
    reduce_nobarrier<<<1, TPB>>>(in, out, TPB);                 cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

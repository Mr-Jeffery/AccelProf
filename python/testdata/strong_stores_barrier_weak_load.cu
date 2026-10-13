// T6 (c), substitution I2 of design/proof/hb_proof.tex section 7 (Remark "Why one bucket per
// key"): A = block 1 and B = block 0 thread 0 store x with relaxed cuda::atomic stores (strong,
// ST.E.STRONG.SYS: a coherent access under the default --strong-ldst generic policy), A first;
// a __syncthreads() joins B with C = block 0 thread 32 (warp 1); C then loads x with a plain
// (weak) load. (A's store, C's load) is a data race: nothing orders A's store before C's load.
// With one last write per location the check sees only B's store, which the barrier orders
// before C's load, and A's store is gone; the (A, B) pair is morally strong and not reported
// either (SC dropped), so nothing at x is reported in either clock.
// Build:  nvcc -arch=native -lineinfo --cudart shared strong_stores_barrier_weak_load.cu
#include <cuda/atomic>
#include <cstdio>

__global__ void kmain(int *x, int *out) {
    if (blockIdx.x == 1) {
        if (threadIdx.x == 0)
            ((cuda::atomic<int>*)x)->store(1, cuda::memory_order_relaxed);   // A: w0
        return;
    }
    if (threadIdx.x == 0) {
        const long long t0 = clock64();
        while (clock64() - t0 < 200000000LL) {}   // ~0.1 s: A stores first
        ((cuda::atomic<int>*)x)->store(2, cuda::memory_order_relaxed);       // B: w1
    }
    __syncthreads();                                                         // B -> C
    if (threadIdx.x == 32)
        out[0] = x[0];                                                       // C: weak read
}

int main() {
    int *x, *out;
    cudaMalloc(&x, sizeof(int));
    cudaMalloc(&out, sizeof(int));
    cudaMemset(x, 0, sizeof(int));
    kmain<<<2, 64>>>(x, out);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

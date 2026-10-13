// T9 (D12): an unordered strong conflict. Block 1 thread 0 stores x with a relaxed
// cuda::atomic store (ST.E.STRONG.SYS), block 0 thread 0 later loads it with a relaxed
// cuda::atomic load (LD.E.STRONG.SYS); nothing orders the two. Both are strong at sys scope
// (morally strong under the default --strong-ldst generic policy), so the pair is not a data
// race but an unordered strong conflict (hb_proof.tex Definition "Verdicts"): HbClock
// reports it with class SC and the verdict layer calls it `sc` -- never `model_bug` (R2 no
// longer certifies an order, D12) and never a RACE.
// Build:  nvcc -arch=native -lineinfo --cudart shared strong_store_strong_load.cu
#include <cuda/atomic>
#include <cstdio>

__global__ void kmain(int *x, int *out) {
    if (threadIdx.x != 0) return;
    if (blockIdx.x == 1) {
        ((cuda::atomic<int>*)x)->store(1, cuda::memory_order_relaxed);        // strong store
        return;
    }
    const long long t0 = clock64();
    while (clock64() - t0 < 200000000LL) {}   // ~0.1 s: the store comes first
    out[0] = ((cuda::atomic<int>*)x)->load(cuda::memory_order_relaxed);       // strong load
}

int main() {
    int *x, *out;
    cudaMalloc(&x, sizeof(int));
    cudaMalloc(&out, sizeof(int));
    cudaMemset(x, 0, sizeof(int));
    kmain<<<2, 32>>>(x, out);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

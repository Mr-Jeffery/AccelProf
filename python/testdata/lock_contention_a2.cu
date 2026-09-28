// T14 (design/a2_flag.md): the lock idiom of write_after_unlock_other_schedule.cu (the ScoR
// rtraw lock: device-scope CAS / EXCH, fenced critical section), race-free, with contention
// forced: lane 0 of 16 warps (4 blocks x 4 warps) takes the lock ITERS times each and
// increments data[0] inside. Every critical section is ordered by the lock hand-off, so a DR
// reported between two of them can only come from an A2 inversion on the trace (the
// successful CAS recorded before the unlock it read from; T9's matrix-multiplication case,
// T13's 4 % of hand-offs at 16 warps) -- and each such instance must carry a2_uncertain.
// Build:  nvcc -arch=native -lineinfo --cudart shared lock_contention_a2.cu
#include <cstdio>

#ifndef ITERS
#define ITERS 32
#endif

__device__ int lock = 0;

__global__ void kmain(volatile unsigned int *data) {
    if (threadIdx.x % 32 != 0) return;
    for (int i = 0; i < ITERS; ++i) {
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        data[0] = data[0] + 1;                    // the critical section
        __threadfence();
        atomicExch(&lock, 0);
    }
}

int main() {
    unsigned int *d, h = 0;
    cudaMalloc(&d, sizeof(unsigned int));
    cudaMemset(d, 0, sizeof(unsigned int));
    kmain<<<4, 128>>>(d);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    cudaMemcpy(&h, d, sizeof(unsigned int), cudaMemcpyDeviceToHost);
    printf("data %u (expected %d)\n", h, 16 * ITERS);
    return h == 16u * ITERS ? 0 : 2;
}

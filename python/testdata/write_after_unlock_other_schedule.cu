// T6 (c), substitution I1 of design/proof/hb_proof.tex section 7: the ScoR
// race_interblock_none-lock_rtraw pattern in the schedule where block 0 takes the lock
// first. Block 0 writes data AFTER its unlock; block 1 then locks and reads data. Nothing
// orders the write before the read (the lock hand-off happened before the write), so the
// pair is a race of this run. Tick-before-publish (I1) publishes block 0's post-release
// epoch and hides it (Proposition "Missed class of I1"); publish-then-tick reports it.
//
// Block 0 is made to run first by a busy wait in block 1 that issues no memory access (a
// flag would add an access, and an atomic flag would order the pair). Fences and lock as in
// the ScoR kernel, so every hand-off is fenced on both sides.
// Build:  nvcc -arch=native -lineinfo --cudart shared write_after_unlock_other_schedule.cu
#include <cstdio>

__device__ int lock = 0;
__device__ int dummy = 0;

__global__ void kmain(volatile unsigned int *data) {
    if (blockIdx.x == 0) {
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        dummy = data[0];
        __threadfence();
        atomicExch(&lock, 0);
        data[0] = 1;                              // after the unlock
    } else {
        const long long t0 = clock64();
        while (clock64() - t0 < 200000000LL) {}   // ~0.1 s: block 0 finishes first
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        dummy = data[0];                          // races with block 0's data[0] = 1
        __threadfence();
        atomicExch(&lock, 0);
    }
}

int main() {
    unsigned int *d;
    cudaMalloc(&d, sizeof(unsigned int));
    cudaMemset(d, 0, sizeof(unsigned int));
    kmain<<<2, 1>>>(d);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

// T12 (hb_proof.tex section 5, R3's write-before-lock decline): the mirror of the ScoR rtraw
// kernel. Block 0 writes data BEFORE taking the lock (fenced), then locks and unlocks; block 1
// locks and reads data. In this run block 0 locks first (T18: block 1 spins on a plain volatile
// flag that block 0 raises after its unlock; the flag forces the hand-off order, so the two
// blocks' RMW windows on the lock cannot overlap). The flag is deliberately NOT an atomic here,
// unlike write_after_unlock_other_schedule.cu: an atomic flag is a sync node R3 would chain
// through, and the pair would then be ordered in every schedule -- the point of this kernel is
// that only the lock hand-off orders it. A volatile flag is a strong access, not an RMW: no
// sync node, no chain, no HB edge (its own store/load pair is an SC on the flag word, which the
// tests do not look at). So the lock hand-off orders the write
// before the read -- in this schedule only: had block 1 locked first, its read would precede
// the write with nothing between them. R3 must not certify the pair (the chain's first hop
// leaves from the lock the writer takes AFTER the write): vector-clock `latent`, scalar-clock
// RACE. The data is a plain int (weak), so the pair is a data race, not an SC.
// Build:  nvcc -arch=native -lineinfo --cudart shared write_before_lock.cu
#include <cstdio>

__device__ int lock = 0;
__device__ volatile int go = 0;

__global__ void kmain(int *data, int *out) {
    if (blockIdx.x == 0) {
        data[0] = 1;                              // before the lock
        __threadfence();
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        atomicExch(&lock, 0);
        go = 1;                                   // plain volatile store: orders nothing
    } else {
        while (go == 0) {}                        // block 0 has unlocked (plain spin)
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        out[0] = data[0];                         // ordered after the write in this run only
        __threadfence();
        atomicExch(&lock, 0);
    }
}

int main() {
    int *d, *o;
    cudaMalloc(&d, sizeof(int));
    cudaMalloc(&o, sizeof(int));
    cudaMemset(d, 0, sizeof(int));
    kmain<<<2, 1>>>(d, o);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

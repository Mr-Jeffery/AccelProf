// T6 (c), substitution I1 of design/proof/hb_proof.tex section 7: the ScoR
// race_interblock_none-lock_rtraw pattern in the schedule where block 0 takes the lock
// first. Block 0 writes data AFTER its unlock; block 1 then locks and reads data. Nothing
// orders the write before the read (the lock hand-off happened before the write), so the
// pair is a race of this run. Tick-before-publish (I1) publishes block 0's post-release
// epoch and hides it (Proposition "Missed class of I1"); publish-then-tick reports it.
//
// Block 0 is made to run first by a spin of block 1 on a flag (T18; the clock64 wait it
// replaces forced the order by timing only, so the RMW windows of the two blocks could in
// principle overlap -- assumption A2, eval/A2_WINDOWS.md). Block 0 raises `go` with an
// UNFENCED atomicExch after its last access and block 1 spins on it with an unfenced
// atomicAdd and no fence after the spin: under the instance gate neither side is a release or
// an acquire (rel = acq = 0, as in gate_held.cu), so the flag orders nothing and adds no
// conflict (RMW against RMW). It forces the order: block 1's first lock CAS is issued after
// `go` took effect, hence after block 0's unlock window closed (the unlock's next record is
// data[0] = 1, before `go`). Fences and lock as in the ScoR kernel, so every lock hand-off
// is fenced on both sides.
// Build:  nvcc -arch=native -lineinfo --cudart shared write_after_unlock_other_schedule.cu
#include <cstdio>

__device__ int lock = 0;
__device__ int dummy = 0;
__device__ int go = 0;

__global__ void kmain(volatile unsigned int *data) {
    if (blockIdx.x == 0) {
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        dummy = data[0];
        __threadfence();
        atomicExch(&lock, 0);
        data[0] = 1;                              // after the unlock
        atomicExch(&go, 1);                       // unfenced: orders nothing
    } else {
        while (atomicAdd(&go, 0) == 0) {}         // block 0 has finished (unfenced spin)
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

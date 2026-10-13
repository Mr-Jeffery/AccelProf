// T14 (design/a2_flag.md): the lock idiom of write_after_unlock_other_schedule.cu (the ScoR
// rtraw lock: device-scope CAS / EXCH, fenced critical section) in two kernels. The data is
// plain (not volatile), so every pair is a data race under each --strong-ldst policy (T10's
// `token` policy makes volatile LDG/STG .STRONG.SYS accesses strong: those pairs are SC).
//   kcontend -- race-free, contention forced: lane 0 of 16 warps (NB=4 blocks x NW=4 warps) takes
//               the lock ITERS times each and increments data[0] inside. A report between two
//               critical sections can only come from an A2 inversion on the trace (the
//               successful CAS recorded before the unlock it read from; T9's
//               matrix-multiplication case, T13's 4 % of hand-offs at 16 warps under NVBit),
//               and each of its instances must carry a2_uncertain.
//   kcontrol -- a genuine race no coherence order explains away: block 0 writes data[1] after its
//               unlock; block 1 waits ~0.1 s (clock64, no memory access), then locks and reads
//               it. Every window on the lock closed long before block 1's CAS: not flagged.
// Build:  nvcc -arch=native -lineinfo --cudart shared lock_contention_a2.cu
#include <cstdio>

#ifndef ITERS
#define ITERS 32
#endif
#ifndef NB                  // kcontend: NB blocks x NW warps contend (eval/A2_WINDOWS.md uses
#define NB 4                // 1x2, 1x4 and 4x4, T13's contention levels)
#endif
#ifndef NW
#define NW 4
#endif

__device__ int lock = 0;

__global__ void kcontend(unsigned int *data) {
    if (threadIdx.x % 32 != 0) return;
    for (int i = 0; i < ITERS; ++i) {
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        data[0] = data[0] + 1;                    // the critical section
        __threadfence();
        atomicExch(&lock, 0);
    }
}

__global__ void kcontrol(unsigned int *data) {
    if (threadIdx.x != 0) return;
    if (blockIdx.x == 0) {
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        atomicExch(&lock, 0);
        __threadfence();
        data[1] = 1;                              // after the unlock
    } else {
        const long long t0 = clock64();
        while (clock64() - t0 < 200000000LL) {}   // ~0.1 s: block 0 finishes first
        while (atomicCAS(&lock, 0, 1) != 0) {}
        __threadfence();
        data[2] = data[1];                        // races with block 0's data[1] = 1
        __threadfence();
        atomicExch(&lock, 0);
    }
}

int main() {
    unsigned int *d, h = 0;
    cudaMalloc(&d, 3 * sizeof(unsigned int));
    cudaMemset(d, 0, 3 * sizeof(unsigned int));
    kcontend<<<NB, 32 * NW>>>(d);
    kcontrol<<<2, 32>>>(d);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    cudaMemcpy(&h, d, sizeof(unsigned int), cudaMemcpyDeviceToHost);
    printf("data %u (expected %d)\n", h, NB * NW * ITERS);
    return h == unsigned(NB * NW * ITERS) ? 0 : 2;
}

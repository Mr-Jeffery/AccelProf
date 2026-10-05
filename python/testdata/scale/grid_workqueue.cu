// Phase 4 grid-scope atomic app: a single global work counter dispensed to ALL blocks
// via atomicAdd at GPU (grid) scope -- a cross-block work queue. Each dispensed index i
// writes out[i] (a distinct location, so no data race); the point is the heavy grid-scope
// atomic traffic on one address, whose observed cross-block coherence order is exactly the
// profile Pi (Phase 3) made concrete. Correctly-scoped and race-free -> another
// false-positive test at scale (expect 0 races).  Build: nvcc -arch=native --cudart shared
#include <cstdio>
#include <cstdlib>

__device__ int g_next;                     // global work counter (grid-scope atomic)

__global__ void workq(int* out, int total) {
    for (;;) {
        int i = atomicAdd(&g_next, 1);     // grid-scope dispense (ATOMG ... STRONG.GPU)
        if (i >= total) break;
        out[i] = i * i;                    // process: distinct location -> no data race
    }
}

int main(int argc, char** argv) {
    int total = (argc > 1) ? atoi(argv[1]) : 4096;
    int blocks = (argc > 2) ? atoi(argv[2]) : 64;
    int tpb = (argc > 3) ? atoi(argv[3]) : 128;
    int* out;
    cudaMallocManaged(&out, (size_t)total * sizeof(int));
    for (int i = 0; i < total; ++i) out[i] = -1;
    int zero = 0; cudaMemcpyToSymbol(g_next, &zero, sizeof(int));
    workq<<<blocks, tpb>>>(out, total);
    cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    // spot check: every index processed exactly once
    long bad = 0; for (int i = 0; i < total; ++i) if (out[i] != (long)i * i) bad++;
    printf("workq total=%d blocks=%d tpb=%d mismatches=%ld\n", total, blocks, tpb, bad);
    cudaFree(out);
    return 0;
}

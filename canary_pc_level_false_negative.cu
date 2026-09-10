#include <cstdio>

__device__ int data[2];      // data[0], data[1] — the contested globals
__device__ int flag[2];      // per-pair handoff flags

__global__ void kmain() {
    int pair = blockIdx.x >> 1;         // 0 or 1
    int role = blockIdx.x & 1;          // 0 = producer, 1 = consumer

    if (role == 0) {                    // PRODUCER of this pair
        data[pair] = pair;              // PC_Wp : write own data[pair]
        __threadfence();
        atomicExch(&flag[pair], 1);     // PC_rel: release own flag[pair]
    } else {                            // CONSUMER of this pair
        while (atomicAdd(&flag[pair], 0) == 0) { /* spin */ }  // PC_acq: acquire own flag
        data[pair ^ 1] = 100 + blockIdx.x;                    // PC_Wc : write the OTHER pair's data
    }
}

int main() {
    kmain<<<4, 1>>>();                  // 2 independent producer/consumer pairs
    cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done (canary: 2 real WAW races on data[0]/data[1]; PC-level reports 0)\n");
    return 0;
}

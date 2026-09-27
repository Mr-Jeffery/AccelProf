// T6 (c), substitution I5 of design/proof/hb_proof.tex section 7: local memory. Every thread
// of two blocks fills and reads its own dynamically indexed array (placed in local memory,
// STL/LDL). No two threads share a local location, so any local-space report is spurious.
// The collector stores (flat thread id in the block << 54) | pointer for a local access
// (gpu_patch_pc_dependency.cu); the engine and hb_oracle key it (local, addr) with no block,
// so threads with the same flat id in different blocks collide iff the pointer is the same.
// Build:  nvcc -arch=native -lineinfo --cudart shared local_mem_blocks.cu
#include <cstdio>

__global__ void kmain(int *out, int n) {
    int buf[64];
    for (int i = 0; i < 64; i++) buf[(i * 7 + threadIdx.x) & 63] = i + threadIdx.x;
    int s = 0;
    for (int i = 0; i < n; i++) s += buf[(i * 13 + blockIdx.x) & 63];
    out[blockIdx.x * blockDim.x + threadIdx.x] = s;
}

int main() {
    int *out;
    cudaMalloc(&out, 64 * sizeof(int));
    kmain<<<2, 32>>>(out, 64);
    cudaError_t e = cudaDeviceSynchronize();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done\n");
    return 0;
}

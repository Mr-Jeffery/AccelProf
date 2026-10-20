// T22 cont. method regression, the bfs shape (HeCBench bfs-cuda Kernel2, `*d_over = 1;`): every
// thread of a 16-block grid writes one flag word at one pc, so the location holds one writer slot
// per thread and each write meets every earlier writer. Expected (scalar-clock hb_sync_pass): the
// flag store with itself at grid distance (other blocks' writers), and the flag store with the
// flag load at grid distance (thread 0 of each block reads the flag after a barrier, which orders
// it after its own block's writers only). No other pair: `out` and `frontier` are per thread or
// per block.
#include <cstdio>
#include <cuda_runtime.h>

__global__ void flag_writers(int* flag, const int* frontier, int* out, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n && frontier[i]) *flag = 1;
    __syncthreads();
    if (threadIdx.x == 0) out[blockIdx.x] = *flag;
}

int main() {
    const int blocks = 16, threads = 256, n = blocks * threads;
    int *flag, *frontier, *out;
    cudaMalloc(&flag, sizeof(int));
    cudaMalloc(&frontier, n * sizeof(int));
    cudaMalloc(&out, blocks * sizeof(int));
    cudaMemset(flag, 0, sizeof(int));
    cudaMemset(out, 0, blocks * sizeof(int));
    int* h = new int[n];
    for (int i = 0; i < n; ++i) h[i] = 1;
    cudaMemcpy(frontier, h, n * sizeof(int), cudaMemcpyHostToDevice);
    flag_writers<<<blocks, threads>>>(flag, frontier, out, n);
    int f = 0;
    cudaMemcpy(&f, flag, sizeof(int), cudaMemcpyDeviceToHost);
    printf("flag=%d\n", f);
    delete[] h;
    cudaFree(flag); cudaFree(frontier); cudaFree(out);
    return cudaDeviceSynchronize() != cudaSuccess;
}

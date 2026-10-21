// T22 cont. method regression, the nbody shape (HeCBench nbody-cuda accelerate_particles,
// `auto pj = p[j];`): every thread reads every particle, so each particle word holds one reader
// slot per thread (1,024 here) -- the broadcast-read regime whose slot insertion the adaptive tail
// targets. Each thread writes only its own `acc` word, and the last thread then stores to `m[0]`
// with no grid-wide synchronisation. Expected (scalar-clock hb_sync_pass): exactly one pair, the
// `m[j]` load with that store, at grid distance (the other blocks' readers of m[0]).
#include <cstdio>
#include <cuda_runtime.h>

__global__ void broadcast_read(float* x, float* m, float* acc, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const float xi = x[i];
    float a = 0.0f;
    for (int j = 0; j < n; ++j) a += m[j] * (x[j] - xi);
    acc[i] = a;
    if (i == n - 1) m[0] = a;
}

int main() {
    const int blocks = 4, threads = 256, n = blocks * threads;
    float *x, *m, *acc;
    cudaMalloc(&x, n * sizeof(float));
    cudaMalloc(&m, n * sizeof(float));
    cudaMalloc(&acc, n * sizeof(float));
    float* h = new float[n];
    for (int i = 0; i < n; ++i) h[i] = 0.001f * i;
    cudaMemcpy(x, h, n * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(m, h, n * sizeof(float), cudaMemcpyHostToDevice);
    broadcast_read<<<blocks, threads>>>(x, m, acc, n);
    cudaMemcpy(h, acc, n * sizeof(float), cudaMemcpyDeviceToHost);
    printf("acc[0]=%f\n", h[0]);
    delete[] h;
    cudaFree(x); cudaFree(m); cudaFree(acc);
    return cudaDeviceSynchronize() != cudaSuccess;
}

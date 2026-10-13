// Phase 4 large __syncthreads-heavy app: canonical tiled GEMM. block = TILE x TILE =
// 32x32 = 1024 threads = 32 WARPS per block, two __syncthreads per tile iteration, and
// heavy CROSS-WARP shared-memory reuse (each thread reads As[ty][k]/Bs[k][tx] written by
// OTHER warps, ordered only by the barrier). This is exactly the shape whose pre-fix
// per-warp barrier join produced a ~23K-spurious-race blast radius; post-fix it must be
// clean (0 races). It also stresses barrier-instance assembly (32 warps assembled per
// instance) and the growing per-thread vector clocks (each clock joins its whole block).
//
// Correctly synchronized, so it doubles as the large RACE-FREE app (false-positive test
// at scale). Size N (matrix dim, multiple of 32) from argv so we can push toward the
// exact-oracle memory wall.  Build: nvcc -arch=native -lineinfo --cudart shared ...
#include <cstdio>
#include <cstdlib>

#ifndef TILE
#define TILE 32
#endif

__global__ void tiled_gemm(const float* __restrict__ A, const float* __restrict__ B,
                           float* __restrict__ C, int N) {
    __shared__ float As[TILE][TILE];
    __shared__ float Bs[TILE][TILE];
    int ty = threadIdx.y, tx = threadIdx.x;
    int row = blockIdx.y * TILE + ty;
    int col = blockIdx.x * TILE + tx;
    float acc = 0.0f;
    for (int t = 0; t < N / TILE; ++t) {
        As[ty][tx] = A[row * N + (t * TILE + tx)];        // warp ty writes a shared row
        Bs[ty][tx] = B[(t * TILE + ty) * N + col];
        __syncthreads();                                   // 32-warp barrier instance
        for (int k = 0; k < TILE; ++k)
            acc += As[ty][k] * Bs[k][tx];                  // cross-warp shared reads
        __syncthreads();                                   // 32-warp barrier instance
    }
    C[row * N + col] = acc;
}

int main(int argc, char** argv) {
    int N = (argc > 1) ? atoi(argv[1]) : 128;              // matrix dim (multiple of TILE)
    if (N % TILE) { printf("N must be a multiple of %d\n", TILE); return 1; }
    size_t bytes = (size_t)N * N * sizeof(float);
    float *A, *B, *C;
    cudaMallocManaged(&A, bytes); cudaMallocManaged(&B, bytes); cudaMallocManaged(&C, bytes);
    for (size_t i = 0; i < (size_t)N * N; ++i) { A[i] = 1.0f; B[i] = 2.0f; C[i] = 0.0f; }
    dim3 block(TILE, TILE);
    dim3 grid(N / TILE, N / TILE);
    tiled_gemm<<<grid, block>>>(A, B, C, N);
    cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    // spot check: C[0] should be N * (1*2)
    printf("tiled_gemm N=%d grid=(%d,%d) block=(%d,%d) C[0]=%.1f (expect %.1f)\n",
           N, grid.x, grid.y, block.x, block.y, C[0], (float)N * 2.0f);
    cudaFree(A); cudaFree(B); cudaFree(C);
    return 0;
}

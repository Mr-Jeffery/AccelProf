// Multi-warp __syncthreads soundness control.
//
// Single block, 2 warps (64 threads). Warp 0 (lanes 0..31) produces a __shared__
// tile; a block-wide __syncthreads() orders those writes before warp 1 (lanes
// 32..63) consumes them (a cross-warp RAW). __syncthreads is the ONLY
// synchronization -- no atomics, no fences. This is the most common CUDA idiom.
//
// A correct happens-before model reports ZERO races: the barrier orders warp 0's
// writes before warp 1's reads. A per-warp barrier join (the soundness bug this
// control guards against) gives warp 0 and warp 1 no cross-warp edge and reports a
// spurious RAW on the shared tile.
#include <stdio.h>
#include <stdlib.h>

#define NBLOCKS  1
#define TPERBLK  64      // 2 warps

void errCheck()
{
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("Error %d: %s\n", err, cudaGetErrorString(err));
        exit(1);
    }
}

__global__ void kmain(unsigned int *out)
{
    __shared__ unsigned int tile[TPERBLK];
    int tid = threadIdx.x;

    if (tid < 32)                 // warp 0 loads the tile
        tile[tid] = tid + 1;

    __syncthreads();              // block barrier: warp 0's writes precede all reads

    if (tid >= 32)                // warp 1 consumes what warp 0 wrote (cross-warp)
        out[tid] = tile[tid - 32];
}

int main()
{
    unsigned int *d_out;
    cudaMalloc(&d_out, TPERBLK * sizeof(unsigned int));
    kmain<<<NBLOCKS, TPERBLK>>>(d_out);
    cudaDeviceSynchronize();
    errCheck();
    cudaFree(d_out);
    return 0;
}

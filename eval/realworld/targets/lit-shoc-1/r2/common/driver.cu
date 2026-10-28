// cuRace T21a lit-shoc-1 (R2): host driver for the verbatim SHOC header src/cuda/level1/scan/scan_kernel.h
// (buggy 785d9ee6 / fixed 700ab826).  Identical for both variants.
// It repeats what RunTest<T, vecT>() of SHOC's src/cuda/level1/scan/Scan.cu does for size class 1 (-s 1: 1 MiB per type = 262144 floats,
// 131072 doubles), one pass, one iteration, for the single-precision then the double-precision test:
//   reduce<T,256><<<64,256,smem>>>  ->  scan_single_block<T,256><<<1,256,2*smem>>>  ->  bottom_scan<T,vecT,256><<<64,256,2*smem>>>
// with smem = sizeof(T)*256, input h_idata[i] = i % 2, and checks the result against a sequential scan (scanCPU of Scan.cu).
// bottom_scan processes 1024 vec4 per block = 4 windows of 256 vec4 per block: the s_seed pair occurs in windows 1..3.
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "src/cuda/level1/scan/scan_kernel.h"

#define CHECK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); exit(1); } } while (0)

template <class T, class vecT>
static bool RunTest(const char *name)
{
    int size = (1 * 1024 * 1024) / sizeof(T);     // probSizes[0] = 1 (MiB)
    unsigned int bytes = size * sizeof(T);

    std::vector<T> h_idata(size), reference(size), h_odata(size);
    for (int i = 0; i < size; i++) {
        h_idata[i] = i % 2;
        h_odata[i] = -1;
    }

    int num_blocks = 64;
    int num_threads = 256;
    int smem_size = sizeof(T) * num_threads;

    T *d_idata, *d_odata, *d_block_sums;
    CHECK(cudaMalloc((void**) &d_idata, bytes));
    CHECK(cudaMalloc((void**) &d_odata, bytes));
    CHECK(cudaMalloc((void**) &d_block_sums, num_blocks * sizeof(T)));
    CHECK(cudaMemcpy(d_idata, h_idata.data(), bytes, cudaMemcpyHostToDevice));

    // as in Scan.cu: reduce-then-scan
    reduce<T, 256><<<num_blocks, num_threads, smem_size>>>(d_idata, d_block_sums, size);
    scan_single_block<T, 256><<<1, num_threads, smem_size*2>>>(d_block_sums, num_blocks);
    bottom_scan<T, vecT, 256><<<num_blocks, num_threads, 2*smem_size>>>(d_idata, d_odata, d_block_sums, size);
    CHECK(cudaGetLastError());
    CHECK(cudaDeviceSynchronize());

    CHECK(cudaMemcpy(h_odata.data(), d_odata, bytes, cudaMemcpyDeviceToHost));

    // scanCPU of Scan.cu
    T last = 0.0f;
    for (int i = 0; i < size; ++i) {
        reference[i] = h_idata[i] + last;
        last = reference[i];
    }
    long bad = 0;
    for (int i = 0; i < size; ++i)
        if (reference[i] != h_odata[i])
            ++bad;
    printf("%s: size %d, Test %s (%ld mismatches)\n", name, size, bad == 0 ? "Passed" : "---FAILED---", bad);

    CHECK(cudaFree(d_idata));
    CHECK(cudaFree(d_odata));
    CHECK(cudaFree(d_block_sums));
    return bad == 0;
}

int main()
{
    int ndev = 0;
    if (cudaGetDeviceCount(&ndev) != cudaSuccess || ndev == 0) {
        printf("no CUDA device, nothing to do\n");
        return 0;
    }
    RunTest<float, float4>("Scan (single precision)");
    RunTest<double, double4>("Scan-DP (double precision)");
    printf("lit-shoc-1 driver done\n");
    return 0;
}

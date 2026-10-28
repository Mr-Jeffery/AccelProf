// cuRace T21a cmssw-1 (R2): host driver for the verbatim CMSSW header HeterogeneousCore/CUDAUtilities/interface/prefixScan.h
// (buggy 37a05c6b / fixed d1ce91e5): launches cms::cuda::multiBlockPrefixScan<uint32_t> exactly as the commit's own unit test
// HeterogeneousCore/CUDAUtilities/test/prefixScan_t.cu does for its multi-block part (1024 threads per block, dynamic shared
// memory 4 * nblocks bytes, input all ones, block counter memset to 0), for num_items = 2000 (2 blocks) and 20000 (20 blocks),
// and checks the result on the host (out[i] == i + 1).  The warp-/block-level kernels of that test are not run (the block-level
// loop of the test alone launches 65536 kernels).   usage: driver [num_items ...]   (default: 2000 20000)
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "HeterogeneousCore/CUDAUtilities/interface/cudaCheck.h"
#include "HeterogeneousCore/CUDAUtilities/interface/prefixScan.h"

using namespace cms::cuda;

// same as the test's init kernel (without the printf)
__global__ void init(uint32_t *v, uint32_t val, uint32_t n) {
  auto i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n)
    v[i] = val;
}

int main(int argc, char **argv) {
  int ndev = 0;
  if (cudaGetDeviceCount(&ndev) != cudaSuccess || ndev == 0) {
    printf("no CUDA device, nothing to do\n");
    return 0;
  }
  std::vector<int> sizes;
  for (int a = 1; a < argc; ++a)
    sizes.push_back(atoi(argv[a]));
  if (sizes.empty()) {
    sizes.push_back(2000);
    sizes.push_back(20000);
  }
  long totalBad = 0;
  for (int num_items : sizes) {
    uint32_t *d_in;
    uint32_t *d_out1;
    cudaCheck(cudaMalloc(&d_in, num_items * sizeof(uint32_t)));
    cudaCheck(cudaMalloc(&d_out1, num_items * sizeof(uint32_t)));
    cudaCheck(cudaMemset(d_out1, 0, num_items * sizeof(uint32_t)));

    auto nthreads = 256;
    auto nblocks = (num_items + nthreads - 1) / nthreads;
    init<<<nblocks, nthreads, 0>>>(d_in, 1, num_items);
    cudaCheck(cudaGetLastError());

    // the block counter
    int32_t *d_pc;
    cudaCheck(cudaMalloc(&d_pc, sizeof(int32_t)));
    cudaCheck(cudaMemset(d_pc, 0, sizeof(int32_t)));

    nthreads = 1024;
    nblocks = (num_items + nthreads - 1) / nthreads;
    multiBlockPrefixScan<<<nblocks, nthreads, 4 * nblocks>>>(d_in, d_out1, num_items, d_pc);
    cudaCheck(cudaGetLastError());
    cudaCheck(cudaDeviceSynchronize());

    std::vector<uint32_t> h(num_items);
    cudaCheck(cudaMemcpy(h.data(), d_out1, num_items * sizeof(uint32_t), cudaMemcpyDeviceToHost));
    long bad = 0;
    uint64_t sum = 0;
    for (int i = 0; i < num_items; ++i) {
      if (h[i] != (uint32_t)(i + 1))
        ++bad;
      sum = sum * 1315423911ull + h[i];
    }
    totalBad += bad;
    printf("multiBlockPrefixScan num_items %d blocks %d x %d threads: mismatches vs i+1: %ld, checksum %016llx\n",
           num_items, (int)nblocks, (int)nthreads, bad, (unsigned long long)sum);
    cudaCheck(cudaFree(d_in));
    cudaCheck(cudaFree(d_out1));
    cudaCheck(cudaFree(d_pc));
  }
  printf("cmssw-1 driver done, total mismatches %ld\n", totalBad);
  return 0;
}

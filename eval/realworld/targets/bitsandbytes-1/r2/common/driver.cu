// cuRace T21a bitsandbytes-1 (R2): host driver for the verbatim csrc/kernels.cu (buggy 344e8516 / fixed 5b28fd3f), which it #includes.
// Identical for both variants.  It launches
//   kEstimateQuantiles<float><<<num_blocks, 512>>>(A, code, offset, FLT_MAX, n)
// exactly as csrc/ops.cu estimateQuantiles<float> (called by F.estimate_quantiles via lib.cestimate_quantiles_fp32) does, for
// n = 16384 floats (default; argv[1] overrides): num_blocks = 4, 512 threads, offset = 1/512, 256 quantiles.
// The 256 estimates are compared with a host reference (per-block sort, same index arithmetic); mismatches are printed.
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <algorithm>
#include <limits>

#include <cub/cub.cuh>

// CCCL 3 (CUDA 13) removed cub::Max and cub::Sum, which csrc/kernels.cu uses (Reduce(x, cub::Max()), cub::Sum()).
// Stand-ins with the CCCL 2.x definitions (thread_operators.cuh), declared before the verbatim kernels.cu is included.
namespace cub {
struct Max {
  template <typename T, typename U>
  __host__ __device__ __forceinline__ ::cuda::std::common_type_t<T, U> operator()(T&& t, U&& u) const {
    return ((u) > (t)) ? (u) : (t);
  }
};
struct Sum {
  template <typename T, typename U>
  __host__ __device__ __forceinline__ auto operator()(T&& t, U&& u) const
      -> decltype(::cuda::std::forward<T>(t) + ::cuda::std::forward<U>(u)) {
    return ::cuda::std::forward<T>(t) + ::cuda::std::forward<U>(u);
  }
};
}  // namespace cub

#include "csrc/kernels.cu"

#define CHECK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); exit(1); } } while (0)

int main(int argc, char **argv) {
  int ndev = 0;
  if (cudaGetDeviceCount(&ndev) != cudaSuccess || ndev == 0) {
    printf("no CUDA device, nothing to do\n");
    return 0;
  }
  const int n = argc > 1 ? atoi(argv[1]) : 16384;
  const float offset = 1.0f / 512.0f;

  // deterministic roughly normal data (sum of 4 uniforms from an LCG), like torch.randn for the estimator
  std::vector<float> h(n);
  unsigned long long s = 12345;
  auto u01 = [&]() { s = s * 6364136223846793005ull + 1442695040888963407ull; return (float)((s >> 40) & 0xFFFFFF) / 16777216.0f; };
  for (int i = 0; i < n; ++i)
    h[i] = (u01() + u01() + u01() + u01() - 2.0f) * 1.7320508f;

  float *d_A = NULL, *d_code = NULL;
  CHECK(cudaMalloc((void **)&d_A, n * sizeof(float)));
  CHECK(cudaMalloc((void **)&d_code, 256 * sizeof(float)));
  CHECK(cudaMemcpy(d_A, h.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  // csrc/ops.cu, estimateQuantiles<float>
  int num_blocks = n / 4096;
  num_blocks = n % 4096 == 0 ? num_blocks : num_blocks + 1;
  CHECK(cudaMemset(d_code, 0, 256 * sizeof(float)));
  kEstimateQuantiles<float><<<num_blocks, 512>>>(d_A, d_code, offset, std::numeric_limits<float>::max(), n);
  CHECK(cudaPeekAtLastError());
  CHECK(cudaDeviceSynchronize());

  std::vector<float> code(256);
  CHECK(cudaMemcpy(code.data(), d_code, 256 * sizeof(float), cudaMemcpyDeviceToHost));

  // host reference (full 4096-element blocks only, as the kernel skips half blocks when n > 4096)
  std::vector<float> ref(256, 0.0f);
  const float recip = 1.0f / (n < 4096 ? 1.0f : (float)(n / 4096));
  for (int b = 0; b < num_blocks; ++b) {
    int valid = (b + 1 == num_blocks) ? n - b * 4096 : 4096;
    if (valid < 4096 && n > 4096) continue;
    std::vector<float> blk(h.begin() + b * 4096, h.begin() + b * 4096 + valid);
    for (int j = 0; j < valid; ++j) blk[j] *= recip;
    std::sort(blk.begin(), blk.end());
    for (int q = 0; q < 256; ++q) {
      float q_interval = (1.0f - (2.0f * offset)) / 255.0f;
      int local_idx = (int)std::round(((offset + (q * q_interval)) * (valid - 1)));
      ref[q] += blk[local_idx];
    }
  }
  // the 4 blocks add into code[] with float atomicAdd in a timing-dependent order, so the low bits of code[] vary between runs
  // even without the race; the checksum is therefore taken over the values quantised to 1e-4 (stable unless a quantile is lost).
  int bad = 0, zeros = 0;
  unsigned long long sum = 0;
  for (int q = 0; q < 256; ++q) {
    double e = std::fabs((double)code[q] - (double)ref[q]);
    if (e > 1e-4) ++bad;
    if (code[q] == 0.0f) ++zeros;
    long long qv = (long long)std::llround((double)code[q] * 1e4);
    sum = sum * 1315423911ull + (unsigned long long)qv;
  }
  printf("kEstimateQuantiles<float> n %d blocks %d x 512 threads: quantiles differing from host reference (|d| > 1e-4): %d of 256, "
         "zero entries %d, checksum(1e-4) %016llx\n", n, num_blocks, bad, zeros, sum);
  printf("bitsandbytes-1 driver done\n");
  cudaFree(d_A);
  cudaFree(d_code);
  return 0;
}

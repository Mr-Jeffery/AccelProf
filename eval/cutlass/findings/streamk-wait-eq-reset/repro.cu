// repro.cu: CUTLASS v4.8.1 GemmUniversalStreamk, sm_89. Peer partials (block_striped.h:194) are read with plain
// LDG (SK:813 / SK:920) after Barrier::wait_eq_reset (relaxed atomicCAS + bar.sync, no acquire). Kernel = the
// CUTLASS instantiation below; no CUTLASS code is copied.  usage: repro [reps=1] [split ...]  (default splits: 2 3)
// split=2 -> 2 peers/tile, cooperative path (finisher: SK:809 wait_eq_reset, SK:813 load_add)
// split=3 -> 3 peers/tile, separate-reduction path (reduction block: SK:885 wait_eq_reset, SK:920 reduce)
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <vector>
#include "cutlass/gemm/device/gemm_universal.h"

// Same Mma/Epilogue as SM50_device_sgemm_nt.64x64x8_64x32x1_8x8_8x4_1x2 (which TestAllGemm re-runs as stream-K).
using Swizzle = cutlass::gemm::threadblock::ThreadblockSwizzleStreamK;
using Gemm = cutlass::gemm::device::GemmUniversal<
    float, cutlass::layout::ColumnMajor, float, cutlass::layout::RowMajor, float, cutlass::layout::RowMajor, float,
    cutlass::arch::OpClassSimt, cutlass::arch::Sm50,
    cutlass::gemm::GemmShape<64, 64, 8>, cutlass::gemm::GemmShape<64, 32, 8>, cutlass::gemm::GemmShape<1, 1, 1>,
    cutlass::epilogue::thread::LinearCombination<float, 1, float, float>, Swizzle, 2>;

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
  printf("CUDA error %s at line %d\n", cudaGetErrorString(e_), __LINE__); return 2; } } while (0)

int main(int argc, char **argv) {
  const int M = 128, N = 128, K = 256;  // 2x2 output tiles of 64x64, 32 k-iterations (of 8) per tile
  int reps = argc > 1 ? atoi(argv[1]) : 1;
  std::vector<int> splits;
  for (int i = 2; i < argc; ++i) splits.push_back(atoi(argv[i]));
  if (splits.empty()) splits = {2, 3};
  std::vector<float> hA(M * K), hB(K * N), hD(M * N);
  std::vector<double> ref(M * N, 0.0);
  srand(1);  // small integers: every fp32 partial sum is exact, so the expected max error is exactly 0
  for (auto &v : hA) v = float(rand() % 5 - 2);
  for (auto &v : hB) v = float(rand() % 5 - 2);
  for (int m = 0; m < M; ++m)
    for (int n = 0; n < N; ++n)
      for (int k = 0; k < K; ++k) ref[m * N + n] += double(hA[m + k * M]) * double(hB[k * N + n]);
  float *A, *B, *C, *D;
  CK(cudaMalloc(&A, 4 * M * K)); CK(cudaMalloc(&B, 4 * K * N)); CK(cudaMalloc(&C, 4 * M * N)); CK(cudaMalloc(&D, 4 * M * N));
  CK(cudaMemcpy(A, hA.data(), 4 * M * K, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(B, hB.data(), 4 * K * N, cudaMemcpyHostToDevice));
  CK(cudaMemset(C, 0, 4 * M * N));
  int sms = 0;
  CK(cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0));
  double max_err = 0.0;
  int bad_runs = 0, runs = 0;
  for (int split : splits) {
    typename Gemm::Arguments args(cutlass::gemm::GemmUniversalMode::kGemm, {M, N, K}, split, {1.0f, 0.0f},
                                  A, B, C, D, 0, 0, 0, 0, M, N, N, N);
    Swizzle sw(cutlass::gemm::GemmUniversalMode::kGemm, {M, N, K}, {64, 64, 8}, split, Gemm::maximum_active_blocks(),
               sms, sms, 4, 4, 4, Gemm::GemmKernel::Epilogue::kAccumulatorFragments);  // host copy of the block mapping
    printf("split=%d: blocks=%d sk_tiles=%d sk_regions=%d sk_blocks/region=%d dp_blocks=%d reduction_blocks=%d -> %s\n",
           split, sw.get_num_blocks(), sw.sk_tiles, sw.sk_regions(), sw.sk_blocks_per_region(), sw.dp_blocks,
           sw.reduction_blocks, sw.reduction_blocks ? "separate reduction (SK:885/920)" : "cooperative finisher (SK:809/813)");
    void *ws = nullptr;
    CK(cudaMalloc(&ws, std::max<size_t>(Gemm::get_workspace_size(args), 4)));
    Gemm gemm;
    if (gemm.can_implement(args) != cutlass::Status::kSuccess) { printf("can_implement failed\n"); return 2; }
    for (int r = 0; r < reps; ++r, ++runs) {
      CK(cudaMemset(D, 0xff, 4 * M * N));  // NaN sentinel: an unwritten element counts as an error
      if (gemm.initialize(args, ws) != cutlass::Status::kSuccess || gemm.run() != cutlass::Status::kSuccess) {
        printf("initialize/run failed\n"); return 2;
      }
      CK(cudaDeviceSynchronize());
      CK(cudaMemcpy(hD.data(), D, 4 * M * N, cudaMemcpyDeviceToHost));
      double e = 0.0;
      for (int i = 0; i < M * N; ++i) { double d = std::fabs(double(hD[i]) - ref[i]); e = std::max(e, d != d ? INFINITY : d); }
      if (e > 0.0) { ++bad_runs; printf("  split=%d rep=%d max_err=%g\n", split, r, e); }
      max_err = std::max(max_err, e);
    }
    CK(cudaFree(ws));
  }
  printf("%s: %d/%d runs wrong, max_err=%g\n", bad_runs ? "FAIL" : "PASS", bad_runs, runs, max_err);
  return bad_runs ? 1 : 0;
}

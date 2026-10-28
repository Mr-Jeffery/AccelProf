// T21a pytorch-4 host main (identical for the buggy and the fixed variant).
// The verbatim Sorting.cu of the revision is #included so that the kernel in the anonymous namespace
// at::native::{anon} is reachable (its radixSelect / TensorInfo / SortingCommon dependencies are the revision's own
// headers, copied byte-for-byte next to it); the ATen host code of that file is compiled (against the installed PyTorch
// headers) but never called.  The kernel is launched the way run_launcher + KthValueLauncher::launch do for
// torch.zeros(4096, device='cuda').kthvalue(5): 1-D contiguous slice, index_t = int32_t, Dim = 1, one slice,
// grid = (1,1,1), block = min(round_up(4096, 32), 1024) = 1024.
#include <aten/src/ATen/native/cuda/Sorting.cu>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <vector>

// TensorInfo::collapseDims (host, header) calls TORCH_CHECK whose failure handler lives in libc10, which is not linked:
// minimal stand-in (only reached on a failed check, never in this driver)
namespace c10::detail {
[[noreturn]] void torchCheckFail(const char* func, const char* file, uint32_t line, const char* msg) {
  std::fprintf(stderr, "TORCH_CHECK failed in %s (%s:%u): %s\n", func, file, line, msg);
  std::abort();
}
}  // namespace c10::detail

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // n = slice size, k = 1-based rank.  All elements are equal (0.0f), so every thread finds a match: with many matching
  // threads in different warps the buggy kernel has them all store kthValue[0] and indices[0].
  const int n = argc > 1 ? std::atoi(argv[1]) : 4096;
  const int k = argc > 2 ? std::atoi(argv[2]) : 5;

  std::vector<float> h_in(n, 0.0f);
  float* d_in = nullptr; float* d_val = nullptr; int64_t* d_idx = nullptr;
  CK(cudaMalloc(&d_in, sizeof(float) * n));
  CK(cudaMalloc(&d_val, sizeof(float)));
  CK(cudaMalloc(&d_idx, sizeof(int64_t)));
  CK(cudaMemcpy(d_in, h_in.data(), sizeof(float) * n, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_val, 0xff, sizeof(float)));       // NaN pattern: shows a missing write
  CK(cudaMemset(d_idx, 0xff, sizeof(int64_t)));     // -1: shows a missing write

  // TensorInfo setup as in run_launcher (getTensorInfo -> reduceDim(dim) -> collapseDims(dim))
  int32_t in_sz[MAX_TENSORINFO_DIMS] = {n}, in_st[MAX_TENSORINFO_DIMS] = {1};
  int32_t out_sz[MAX_TENSORINFO_DIMS] = {1}, out_st[MAX_TENSORINFO_DIMS] = {1};
  at::cuda::detail::TensorInfo<const float, int32_t> self_info(d_in, 1, in_sz, in_st);
  at::cuda::detail::TensorInfo<float, int32_t> values_info(d_val, 1, out_sz, out_st);
  at::cuda::detail::TensorInfo<int64_t, int32_t> indices_info(d_idx, 1, out_sz, out_st);
  self_info.reduceDim(0);
  values_info.reduceDim(0);
  indices_info.reduceDim(0);
  int collapse_self_dim = self_info.collapseDims(0);
  int64_t num_slices = 1;
  for (int i = 0; i < self_info.dims; ++i) num_slices *= self_info.sizes[i];

  dim3 grid;
  if (!at::native::getGridFromTiles(num_slices, grid)) { std::fprintf(stderr, "slices are too many\n"); return 2; }
  dim3 block((unsigned)std::min(((n + 31) / 32) * 32, 1024));

  at::native::gatherKthValue<float, int32_t, 1><<<grid, block, 0>>>(
      self_info, (int32_t)n, (int32_t)k, (int32_t)num_slices, self_info.strides[collapse_self_dim], values_info, indices_info);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  float h_val = -1.0f; int64_t h_idx = -2;
  CK(cudaMemcpy(&h_val, d_val, sizeof(float), cudaMemcpyDeviceToHost));
  CK(cudaMemcpy(&h_idx, d_idx, sizeof(int64_t), cudaMemcpyDeviceToHost));
  // every element equals the k-th value; the fixed kernel returns the smallest matching index (0), the buggy kernel
  // leaves whichever matching thread stored last (a thread's first match is its own threadIdx.x, so 0..block-1)
  std::printf("gatherKthValue<float,int,1> n=%d k=%d grid=%u block=%u kthvalue=%g index=%lld (valid value: %s; index == 0: %s)\n",
              n, k, grid.x, block.x, h_val, (long long)h_idx, h_val == 0.0f ? "yes" : "NO", h_idx == 0 ? "yes" : "no");
  return 0;
}

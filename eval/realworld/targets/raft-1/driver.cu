// raft-1 driver: raft::matrix::select_k with the multi-block radix select (radix_kernel, last-block-done pattern).
// Compiled against the checkout's headers (route R1h); the kernel source is raft/matrix/detail/select_radix.cuh of the checkout.
//
//   driver [batch=2] [len=50000] [k=64] [algo=8|11|112] [iters=1]
//     algo 8   = SelectAlgo::kRadix8bits   (radix_kernel<float, int64_t, 8, 512, fused_last_filter, dense_layout>)
//     algo 11  = SelectAlgo::kRadix11bits  (11 bits per pass, last filter fused)
//     algo 112 = SelectAlgo::kRadix11bitsExtraPass
//   The multi-block kernel is used only when len > BlockSize*32 = 16384 and calc_grid_dim() > 1 (select_radix.cuh, select_k()
//   at the end of the file); otherwise radix_topk_one_block runs and the race cannot occur.  The driver evaluates the very same
//   function (impl::calc_grid_dim) before the call and refuses to run (rc 3) if the multi-block path would not be taken.
//   Default input: 2 rows x 50000 float keys (random bit patterns: the top byte, i.e. the first 8-bit radix digit, is spread over
//   ~254 buckets, so many threads of the block take part in the histogram merge), k = 64, select the k smallest, unsorted.
//   Output: the result is checked against a host reference (sorted k smallest per row, indices must point at the value).
//   rc 0: ran (the printed line says OK or MISMATCH: a mismatch is the observable symptom of the race, not a driver failure),
//   rc 2: CUDA/raft error, rc 3: multi-block path not taken.
#include <raft/core/device_mdspan.hpp>
#include <raft/core/resource/cuda_stream.hpp>
#include <raft/core/resource/device_properties.hpp>
#include <raft/core/resources.hpp>
#include <raft/matrix/select_k.cuh>
#include <raft/matrix/select_k_types.hpp>

#include <cuda_runtime.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <optional>
#include <random>
#include <vector>

#define CK(call)                                                                        \
  do {                                                                                  \
    cudaError_t e_ = (call);                                                            \
    if (e_ != cudaSuccess) {                                                            \
      std::fprintf(stderr, "CUDA error %s at %s:%d: %s\n", #call, __FILE__, __LINE__,   \
                   cudaGetErrorString(e_));                                             \
      return 2;                                                                         \
    }                                                                                   \
  } while (0)

using T    = float;
using IdxT = int64_t;

int main(int argc, char** argv)
{
  const int64_t batch = argc > 1 ? std::atoll(argv[1]) : 2;
  const int64_t len   = argc > 2 ? std::atoll(argv[2]) : 50000;
  const int k         = argc > 3 ? std::atoi(argv[3]) : 64;
  const int algo_arg  = argc > 4 ? std::atoi(argv[4]) : 8;
  const int iters     = argc > 5 ? std::atoi(argv[5]) : 1;

  raft::matrix::SelectAlgo algo = raft::matrix::SelectAlgo::kRadix8bits;
  if (algo_arg == 11) algo = raft::matrix::SelectAlgo::kRadix11bits;
  if (algo_arg == 112) algo = raft::matrix::SelectAlgo::kRadix11bitsExtraPass;

  try {
    raft::resources handle;
    const auto stream = raft::resource::get_cuda_stream(handle);
    const int sm_cnt  = raft::resource::get_device_properties(handle).multiProcessorCount;

    // dispatch check: the same conditions as raft::matrix::detail::select::radix::select_k()
    constexpr int kBlock = 512, kItems = 32;
    unsigned grid_dim = 0;
    if (len > kBlock * kItems) {
      grid_dim = (algo_arg == 8)
                   ? raft::matrix::detail::select::radix::impl::calc_grid_dim<T, IdxT, 8, kBlock>(
                       static_cast<int>(batch), static_cast<IdxT>(len), sm_cnt)
                   : raft::matrix::detail::select::radix::impl::calc_grid_dim<T, IdxT, 11, kBlock>(
                       static_cast<int>(batch), static_cast<IdxT>(len), sm_cnt);
    }
    const bool multi_block = grid_dim > 1;
    std::printf("raft-1: batch=%lld len=%lld k=%d algo=%d sm_count=%d  len>%d: %s  calc_grid_dim=%u  path=%s\n",
                (long long)batch, (long long)len, k, algo_arg, sm_cnt, kBlock * kItems,
                len > kBlock * kItems ? "yes" : "no", grid_dim,
                multi_block ? "radix_kernel (multi-block, grid=(grid_dim,batch))" : "radix_topk_one_block");
    if (!multi_block) return 3;

    // input: random float bit patterns (finite), fixed seed
    std::vector<T> h_in(static_cast<size_t>(batch * len));
    std::mt19937 rng(12345u);
    for (auto& v : h_in) {
      uint32_t u = rng();
      if (((u >> 23) & 0xFFu) == 0xFFu) u &= ~(1u << 30);  // no inf/nan: clear one exponent bit
      std::memcpy(&v, &u, sizeof(u));
    }

    T* d_in      = nullptr;
    T* d_out     = nullptr;
    IdxT* d_oidx = nullptr;
    CK(cudaMalloc(&d_in, h_in.size() * sizeof(T)));
    CK(cudaMalloc(&d_out, static_cast<size_t>(batch * k) * sizeof(T)));
    CK(cudaMalloc(&d_oidx, static_cast<size_t>(batch * k) * sizeof(IdxT)));
    CK(cudaMemcpy(d_in, h_in.data(), h_in.size() * sizeof(T), cudaMemcpyHostToDevice));

    auto in_view   = raft::make_device_matrix_view<const T, int64_t, raft::row_major>(d_in, batch, len);
    auto out_view  = raft::make_device_matrix_view<T, int64_t, raft::row_major>(d_out, batch, k);
    auto oidx_view = raft::make_device_matrix_view<IdxT, int64_t, raft::row_major>(d_oidx, batch, k);

    // host reference: the k smallest values of every row
    std::vector<T> ref(static_cast<size_t>(batch * k));
    for (int64_t b = 0; b < batch; ++b) {
      std::vector<T> row(h_in.begin() + b * len, h_in.begin() + (b + 1) * len);
      std::partial_sort(row.begin(), row.begin() + k, row.end());
      std::copy(row.begin(), row.begin() + k, ref.begin() + b * k);
    }

    long long bad_total = 0;
    std::vector<T> h_out(static_cast<size_t>(batch * k));
    std::vector<IdxT> h_oidx(static_cast<size_t>(batch * k));
    for (int it = 0; it < iters; ++it) {
      CK(cudaMemsetAsync(d_out, 0xFF, static_cast<size_t>(batch * k) * sizeof(T), stream));
      CK(cudaMemsetAsync(d_oidx, 0xFF, static_cast<size_t>(batch * k) * sizeof(IdxT), stream));
      raft::matrix::select_k<T, IdxT>(handle, in_view, std::nullopt, out_view, oidx_view,
                                      /*select_min=*/true, /*sorted=*/false, algo);
      CK(cudaStreamSynchronize(stream));
      CK(cudaGetLastError());
      CK(cudaMemcpy(h_out.data(), d_out, h_out.size() * sizeof(T), cudaMemcpyDeviceToHost));
      CK(cudaMemcpy(h_oidx.data(), d_oidx, h_oidx.size() * sizeof(IdxT), cudaMemcpyDeviceToHost));
      long long bad = 0;
      for (int64_t b = 0; b < batch; ++b) {
        std::vector<T> got(h_out.begin() + b * k, h_out.begin() + (b + 1) * k);
        std::sort(got.begin(), got.end());
        for (int j = 0; j < k; ++j) {
          if (std::memcmp(&got[j], &ref[b * k + j], sizeof(T)) != 0) ++bad;
          const IdxT ix = h_oidx[b * k + j];
          if (ix < 0 || ix >= len || std::memcmp(&h_in[b * len + ix], &h_out[b * k + j], sizeof(T)) != 0) ++bad;
        }
      }
      bad_total += bad;
      if (bad != 0) std::printf("raft-1: iteration %d: %lld wrong entries\n", it, bad);
    }
    std::printf("raft-1: select_k done, %d iteration(s): %s (wrong entries: %lld)\n", iters,
                bad_total == 0 ? "OK" : "MISMATCH", bad_total);
    cudaFree(d_in);
    cudaFree(d_out);
    cudaFree(d_oidx);
  } catch (std::exception const& e) {
    std::fprintf(stderr, "exception: %s\n", e.what());
    return 2;
  }
  return 0;
}

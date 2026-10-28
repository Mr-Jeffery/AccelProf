// T21a lit-exllamav3-1 host main (identical for the buggy and the fixed variant).
// The verbatim exllamav3/exllamav3_ext/routing.cu of the revision (with its own routing.cuh, util.h, util.cuh, reduction.cuh,
// hgemm.cuh, graph.cuh copied from the same revision) is #included; the torch host functions of the file (routing_ds3_nogroup,
// routing_std, ...) are compiled but never called.  The three kernels that carry the shared-memory WAR of the record are
// launched with the configurations the host functions use (grid = bsz, block = CEIL_DIVIDE(E,32)*32, same dynamic shmem):
//   routing_ds3_nogroup_topk_kernel<ROUTING_ACT_SIGMOID>   (routing_ds3_nogroup, L714-L773)  -- primary target
//   routing_std_topk_kernel                                (routing_std,         L1192-L1251)
//   routing_std_kernel                                     (routing_std_logits,  L1254-L1321, use_topk = false)
// usage: driver [which = all|ds3|std_topk|std] [E = 256] [K = 8] [bsz = 4]
#include <exllamav3/exllamav3_ext/routing.cu>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

// reference: the K largest logits of a row, descending (all logits of a row are distinct)
static std::vector<int> ref_topk(const std::vector<float>& row, int K) {
  std::vector<int> ord(row.size());
  for (size_t i = 0; i < ord.size(); ++i) ord[i] = (int)i;
  std::sort(ord.begin(), ord.end(), [&](int a, int b) { return row[a] > row[b]; });
  ord.resize(K);
  return ord;
}

int main(int argc, char** argv) {
  const std::string which = argc > 1 ? argv[1] : "all";
  const int E = argc > 2 ? std::atoi(argv[2]) : 256;
  const int K = argc > 3 ? std::atoi(argv[3]) : 8;
  const int bsz = argc > 4 ? std::atoi(argv[4]) : 4;
  const int num_warps = CEIL_DIVIDE(E, 32);
  const int num_threads = num_warps * 32;

  // distinct, exactly representable half logits per row: ((idx*37 + row*11) mod 256) / 16 - 8  (37 is odd, so a permutation)
  std::vector<half> h_scores((size_t)bsz * E);
  std::vector<std::vector<float>> rows(bsz, std::vector<float>(E));
  for (int r = 0; r < bsz; ++r)
    for (int i = 0; i < E; ++i) {
      float v = (float)((i * 37 + r * 11) % 256) / 16.0f - 8.0f;
      rows[r][i] = v;
      h_scores[(size_t)r * E + i] = __float2half_rn(v);
    }

  half* d_scores = nullptr; int64_t* d_idx = nullptr; half* d_w = nullptr;
  CK(cudaMalloc(&d_scores, sizeof(half) * h_scores.size()));
  CK(cudaMalloc(&d_idx, sizeof(int64_t) * (size_t)bsz * K));
  CK(cudaMalloc(&d_w, sizeof(half) * (size_t)bsz * K));
  CK(cudaMemcpy(d_scores, h_scores.data(), sizeof(half) * h_scores.size(), cudaMemcpyHostToDevice));

  auto check = [&](const char* name) -> int {
    std::vector<int64_t> h_idx((size_t)bsz * K);
    CK(cudaMemcpy(h_idx.data(), d_idx, sizeof(int64_t) * h_idx.size(), cudaMemcpyDeviceToHost));
    int set_bad = 0, order_bad = 0;
    for (int r = 0; r < bsz; ++r) {
      std::vector<int> ref = ref_topk(rows[r], K);
      std::vector<int> got(K);
      for (int k = 0; k < K; ++k) got[k] = (int)h_idx[(size_t)r * K + k];
      order_bad += (got != ref);
      std::vector<int> a = ref, b = got;
      std::sort(a.begin(), a.end()); std::sort(b.begin(), b.end());
      set_bad += (a != b);
    }
    std::printf("%s E=%d K=%d bsz=%d grid=%d block=%d row0 top%d=[", name, E, K, bsz, bsz, num_threads, K);
    for (int k = 0; k < K; ++k) std::printf("%s%lld", k ? "," : "", (long long)h_idx[k]);
    std::printf("] rows_with_wrong_set=%d rows_with_other_order=%d/%d\n", set_bad, order_bad, bsz);
    return 0;
  };

  if (which == "all" || which == "ds3") {
    size_t shmem = (size_t)num_warps * K * (2 * sizeof(float) + sizeof(int));
    CK(cudaMemset(d_idx, 0xff, sizeof(int64_t) * (size_t)bsz * K));
    routing_ds3_nogroup_topk_kernel<ROUTING_ACT_SIGMOID><<<bsz, num_threads, shmem>>>(
        d_scores, /*bias=*/nullptr, d_idx, d_w, /*scaling_factor=*/1.0f, E, K, bsz);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());
    if (check("routing_ds3_nogroup_topk_kernel<SIGMOID>")) return 2;
  }
  if (which == "all" || which == "std_topk") {
    size_t shmem = (size_t)num_warps * K * (sizeof(float) + sizeof(int)) + (size_t)num_warps * sizeof(float);
    CK(cudaMemset(d_idx, 0xff, sizeof(int64_t) * (size_t)bsz * K));
    routing_std_topk_kernel<<<bsz, num_threads, shmem>>>(
        d_scores, d_idx, d_w, /*per_expert_scale=*/nullptr, /*bias=*/nullptr, E, K, bsz);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());
    if (check("routing_std_topk_kernel")) return 2;
  }
  if (which == "all" || which == "std") {
    int K_ = K + (K & 1);
    size_t shmem = (size_t)num_warps * K_ * (sizeof(float) + sizeof(int)) + (size_t)num_threads * sizeof(int) + (size_t)num_warps * sizeof(float);
    CK(cudaMemset(d_idx, 0xff, sizeof(int64_t) * (size_t)bsz * K));
    routing_std_kernel<<<bsz, num_threads, shmem>>>(
        d_scores, d_idx, d_w, /*per_expert_scale=*/nullptr, E, K, bsz);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());
    if (check("routing_std_kernel")) return 2;
  }
  return 0;
}

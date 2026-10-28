// T21c sglang-open-1 host main (R2).  The verbatim python/sglang/kernels/aot/csrc/moe/moe_align_kernel.cu of SGLang 08550acc28 is #included whole
// (CUDA, non-HIP path; with python/sglang/kernels/aot/include/utils.h, also verbatim).
// Launches exactly what the host dispatcher moe_align_block_size() (same file, last function) launches for int32 topk_ids in the general case
// (numel >= 1024 or num_experts > 64):
//     moe_align_block_size_kernel<int32_t><<<2, 1024, (E + (E+1) + scan_size + WARP_SIZE) * 4>>>(...)
//     count_and_sort_expert_tokens_kernel<int32_t><<<min(ceil(numel/256), 65535), 256>>>(...)
// The dispatcher itself takes torch::Tensor arguments (libtorch), so the tensors are replaced by cudaMalloc buffers of the sizes the Python wrapper allocates.
// Input: 4,096 tokens x top-8 routing = 32,768 ids, num_experts = 256, block_size = 16.
#include "python/sglang/kernels/aot/csrc/moe/moe_align_kernel.cu"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv)
{
    const int num_tokens = argc > 1 ? std::atoi(argv[1]) : 4096, topk = 8;
    const int32_t num_experts = argc > 2 ? std::atoi(argv[2]) : 256;
    const int32_t block_size = 16;
    const size_t numel = (size_t)num_tokens * topk;
    const bool pad_sorted_token_ids = true, ignore_invalid_expert = false;
    // sorted_token_ids length as the Python wrapper allocates it: numel + (num_experts) * (block_size - 1) (+ the invalid-expert slot)
    const int32_t max_num_tokens_padded = (int32_t)(numel + (size_t)(num_experts + 1) * (block_size - 1));
    const int32_t max_num_m_blocks = (max_num_tokens_padded + block_size - 1) / block_size;

    // topk_ids in [0, num_experts - 2] so that expert_id = topk_ids + 1 <= num_experts - 1 stays inside shared_counts[num_experts]
    std::vector<int32_t> h_ids(numel);
    unsigned s = 99u;
    for (auto& v : h_ids) { s = s * 1664525u + 1013904223u; v = (int32_t)((s >> 8) % (unsigned)(num_experts - 1)); }

    int32_t *d_ids, *d_sorted, *d_experts, *d_post_pad, *d_cumsum;
    CK(cudaMalloc(&d_ids, numel * 4)); CK(cudaMalloc(&d_sorted, (size_t)max_num_tokens_padded * 4 + 16));
    CK(cudaMalloc(&d_experts, (size_t)max_num_m_blocks * 4)); CK(cudaMalloc(&d_post_pad, 4)); CK(cudaMalloc(&d_cumsum, (size_t)(num_experts + 2) * 4));
    CK(cudaMemcpy(d_ids, h_ids.data(), numel * 4, cudaMemcpyHostToDevice));
    CK(cudaMemset(d_sorted, 0, (size_t)max_num_tokens_padded * 4)); CK(cudaMemset(d_experts, 0xff, (size_t)max_num_m_blocks * 4));
    CK(cudaMemset(d_post_pad, 0, 4)); CK(cudaMemset(d_cumsum, 0, (size_t)(num_experts + 2) * 4));

    int threads = 1024;
    const size_t scan_size = next_pow2(num_experts);
    const size_t shared_mem_size = (num_experts + (num_experts + 1) + scan_size + WARP_SIZE) * sizeof(int32_t);
    moe_align_block_size_kernel<int32_t><<<2, threads, shared_mem_size>>>(
        d_ids, d_sorted, d_experts, d_post_pad, num_experts, block_size, numel, d_cumsum,
        pad_sorted_token_ids, ignore_invalid_expert, (int32_t)scan_size, max_num_tokens_padded);
    CK(cudaGetLastError());

    const int block_threads = std::min(256, threads);
    const int num_blocks = (int)((numel + block_threads - 1) / block_threads);
    const int actual_blocks = std::min(num_blocks, 65535);
    count_and_sort_expert_tokens_kernel<int32_t><<<actual_blocks, block_threads>>>(d_ids, d_sorted, d_cumsum, numel, ignore_invalid_expert);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());

    // host reference of total_tokens_post_pad
    std::vector<int> cnt(num_experts, 0);
    for (auto v : h_ids) cnt[v + 1]++;
    long total = 0; for (int e = 0; e < num_experts; ++e) total += (long)(cnt[e] + block_size - 1) / block_size * block_size;
    int32_t got = 0; CK(cudaMemcpy(&got, d_post_pad, 4, cudaMemcpyDeviceToHost));
    std::vector<int32_t> h_exp(max_num_m_blocks);
    CK(cudaMemcpy(h_exp.data(), d_experts, (size_t)max_num_m_blocks * 4, cudaMemcpyDeviceToHost));
    std::printf("moe_align_block_size_kernel<int32_t> tokens=%d topk=%d numel=%zu experts=%d block_size=%d grid=2 block=%d smem=%zu "
                "total_tokens_post_pad=%d (host %ld) expert_ids[0..3]=%d,%d,%d,%d sort_grid=%d\n",
                num_tokens, topk, numel, num_experts, block_size, threads, shared_mem_size, got, total, h_exp[0], h_exp[1], h_exp[2], h_exp[3], actual_blocks);
    return 0;
}

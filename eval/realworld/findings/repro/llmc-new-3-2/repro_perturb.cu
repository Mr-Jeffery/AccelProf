// llmc-new-3-2 PERTURBED reproducer (repro.cu + __nanosleep in warp 0 between the barrier L707 and the read L708). Kernel copied from karpathy/llm.c f1e2ace651495b74ae22d45d1723443fd00ecd3a dev/cuda/attention_backward.cu
// L673-L717 (softmax_autoregressive_backward_kernel8), launched as launch_softmax_8 (L842-L851) with block_size 256.
// ONE deliberate change: the block.sync() of llm.c PR #847 (open) is added after the block_acc init (marked), so that the
// init WAW of finding llmc-new-3 is absent and only the loop-carried WAR (L708 read vs next iteration's L706 write) remains.
#include <cstdio>
#include <cmath>
#include <cooperative_groups.h>
#include <cooperative_groups/reduce.h>
template<int BlockSize>
__global__ void softmax_autoregressive_backward_kernel8(float* dpreatt, const float* datt, const float* att,
                                                        int B, int T, int C, float scale) {
    namespace cg = cooperative_groups;
    constexpr int T_per_block = 4;
    cg::thread_block block = cg::this_thread_block();
    cg::thread_block_tile<32> warp = cg::tiled_partition<32>(block);
    __shared__ float block_acc[32];
    int idx = blockIdx.y;
    int t0 = T - 1 - T_per_block*blockIdx.x;
    att += idx * T * T; datt += idx * T * T; dpreatt += idx * T * T;
    if (warp.meta_group_rank() == 0) {
        block_acc[warp.thread_rank()] = 0;                                              // L691
    }
    block.sync();                                                                       // PR #847 (not upstream at f1e2ace6)
    for(int to = 0; to < T_per_block; ++to) {                                           // L694
        int t = t0 - to; if(t < 0) return;
        const float* att_bth = att + t * T; const float* datt_bth = datt + t * T; float* dpreatt_bth = dpreatt + t * T;
        float local_sum = 0;
        for (int t2 = block.thread_rank(); t2 <= t; t2 += BlockSize) {
            local_sum += att_bth[t2] * datt_bth[t2];
        }
        block_acc[warp.meta_group_rank()] = cg::reduce(warp, local_sum, cg::plus<float>{});    // L706
        block.sync(); if (warp.meta_group_rank() == 0) __nanosleep(100000);              // L707 + PERTURB: warp 0 reads late
        local_sum = cg::reduce(warp, block_acc[warp.thread_rank()], cg::plus<float>{});        // L708
        for (int t3 = block.thread_rank(); t3 <= t; t3 += BlockSize) {
            float acc = __ldcs(att_bth + t3) * (__ldcs(datt_bth + t3) - local_sum);
            __stcs(dpreatt_bth + t3, scale * acc);
        }
    }
}
int main() {
    const int T = 256, HS = 64, n = T * T, reps = 20; const float scale = 1.0f / sqrtf((float)HS);
    float *ha = new float[n], *hd = new float[n], *ho = new float[n], *ref = new float[n], *da, *dd, *dp; unsigned s = 12345u;
    for (int i = 0; i < n; i++) { s = s * 1664525u + 1013904223u; ha[i] = (i % T) <= (i / T) ? 1.0f / (i / T + 1) : 0.f; hd[i] = ((s >> 8) & 0xffff) / 65536.0f - 0.5f; }
    for (int t = 0; t < T; t++) { double sum = 0; for (int j = 0; j <= t; j++) sum += (double)ha[t*T+j] * hd[t*T+j];
        for (int i = 0; i < T; i++) ref[t*T+i] = i <= t ? (float)(scale * ha[t*T+i] * (hd[t*T+i] - sum)) : 0.f; }
    cudaMalloc(&da, n * 4); cudaMalloc(&dd, n * 4); cudaMalloc(&dp, n * 4);
    cudaMemcpy(da, ha, n * 4, cudaMemcpyHostToDevice); cudaMemcpy(dd, hd, n * 4, cudaMemcpyHostToDevice); int bad_runs = 0, bad = 0;
    for (int r = 0; r < reps; r++) {
        cudaMemset(dp, 0, n * 4);
        softmax_autoregressive_backward_kernel8<256><<<dim3(T / 4, 1), 256>>>(dp, dd, da, 1, T, 768, scale);
        cudaMemcpy(ho, dp, n * 4, cudaMemcpyDeviceToHost);
        int b = 0; for (int i = 0; i < n; i++) b += fabsf(ho[i] - ref[i]) > 1e-4f + 1e-3f * fabsf(ref[i]);
        bad_runs += b != 0; bad += b;
    }
    cudaError_t e = cudaDeviceSynchronize(); printf("llmc-new-3-2 kernel8 T=%d grid=(%d,1) block=256 reps=%d runs_with_mismatches=%d total_mismatches=%d err=%s\n", T, T / 4, reps, bad_runs, bad, cudaGetErrorString(e));
    printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
    return 0;
}

// llmc-new-2 FIXED reproducer (repro.cu with final_sync=true at the attention.cuh L176 call). Copied from karpathy/llm.c f1e2ace651495b74ae22d45d1723443fd00ecd3a: llmc/cuda_common.h L31 (WARP_SIZE),
// llmc/cuda_utils.cuh L147-L152 (warpReduceSum) and L165-L184 (blockReduce), llmc/attention.cuh L152-L190
// (softmax_autoregressive_backward_inplace_kernel), launched as attention.cuh L266. Trimmed: floatX = float (upstream: bf16
// under ENABLE_BF16, conversions removed), comments. Same accesses, same barriers.
#include <cstdio>
#include <cmath>
#define WARP_SIZE 32U
__device__ inline float warpReduceSum(float val) {
    for (int offset = 16; offset > 0; offset /= 2) { val += __shfl_xor_sync(0xFFFFFFFF, val, offset); }
    return val;
}
using reduction_func_t = float (*) (float);
template<reduction_func_t warp_reduction>
__device__ inline float blockReduce(float val, bool final_sync=false, float out_of_bounds=0.0f) {
    __shared__ float shared_val[WARP_SIZE];
    const int lane_id = threadIdx.x % WARP_SIZE; const int warp_id = threadIdx.x / WARP_SIZE; const int num_warps = blockDim.x / WARP_SIZE;
    float warp_val = warp_reduction(val);
    if (lane_id == 0) { shared_val[warp_id] = warp_val; }                          // cuda_utils.cuh L175
    __syncthreads();                                                                // L176
    warp_val = (lane_id < num_warps) ? shared_val[lane_id] : out_of_bounds;         // L177
    float block_val = warp_reduction(warp_val);
    if (final_sync) { __syncthreads(); }                                            // L180-L182
    return block_val;
}
__global__ void softmax_autoregressive_backward_inplace_kernel(float* datt, const float* att, int B, int T, int C, float scale) {
    constexpr const int BlockSize = 256; constexpr int T_per_block = 4;
    int t0 = T - 1 - T_per_block*blockIdx.x; int idx = blockIdx.y;
    att += idx * T * T; datt += idx * T * T;
    for(int to = 0; to < T_per_block; ++to) {                                        // attention.cuh L164
        int t = t0 - to; if(t < 0) return;
        const float* att_bth = att + t * T; const float* datt_bth = datt + t * T; float* dpreatt_bth = datt + t * T;
        float local_sum = 0;
        for (int t2 = threadIdx.x; t2 <= t; t2 += BlockSize) { local_sum += (float)att_bth[t2] * (float)datt_bth[t2]; }
        local_sum = blockReduce<warpReduceSum>(local_sum, true);                    // L176 + FIX: final_sync=true
        for (int t3 = threadIdx.x; t3 < T; t3 += BlockSize) {
            if(t3 <= t) {
                float acc = (float) __ldcs(att_bth + t3) * ((float) __ldcs(datt_bth + t3) - local_sum);
                __stcs(dpreatt_bth + t3, (float) (scale * acc));
            } else { __stcs(dpreatt_bth + t3, (float)0.f); }
        }
    }
}
int main() {
    const int T = 256, HS = 64, n = T * T, reps = 20; const float scale = 1.0f / sqrtf((float)HS);  // B*NH = 1
    float *ha = new float[n], *hd = new float[n], *ho = new float[n], *ref = new float[n], *da, *dd; unsigned s = 12345u;
    for (int i = 0; i < n; i++) { s = s * 1664525u + 1013904223u; ha[i] = (i % T) <= (i / T) ? 1.0f / (i / T + 1) : 0.f; hd[i] = ((s >> 8) & 0xffff) / 65536.0f - 0.5f; }
    for (int t = 0; t < T; t++) { double sum = 0; for (int j = 0; j <= t; j++) sum += (double)ha[t*T+j] * hd[t*T+j];
        for (int i = 0; i < T; i++) ref[t*T+i] = i <= t ? (float)(scale * ha[t*T+i] * (hd[t*T+i] - sum)) : 0.f; }
    cudaMalloc(&da, n * 4); cudaMalloc(&dd, n * 4); cudaMemcpy(da, ha, n * 4, cudaMemcpyHostToDevice); int bad_runs = 0, bad = 0;
    for (int r = 0; r < reps; r++) {
        cudaMemcpy(dd, hd, n * 4, cudaMemcpyHostToDevice);
        softmax_autoregressive_backward_inplace_kernel<<<dim3(T / 4, 1), 256>>>(dd, da, 1, T, HS, scale);
        cudaMemcpy(ho, dd, n * 4, cudaMemcpyDeviceToHost);
        int b = 0; for (int i = 0; i < n; i++) b += fabsf(ho[i] - ref[i]) > 1e-4f + 1e-3f * fabsf(ref[i]);
        bad_runs += b != 0; bad += b;
    }
    cudaError_t e = cudaDeviceSynchronize(); printf("llmc-new-2 T=%d grid=(%d,1) block=256 reps=%d runs_with_mismatches=%d total_mismatches=%d err=%s\n", T, T / 4, reps, bad_runs, bad, cudaGetErrorString(e));
    printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
    return 0;
}

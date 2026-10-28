// llmc-new-1 reproducer. Kernel = the hand-off tail of layernorm_backward_kernel10, dev/cuda/layernorm_backward.cu
// L1183-L1223 at karpathy/llm.c f1e2ace651495b74ae22d45d1723443fd00ecd3a (same accesses, same barriers, same atomicInc).
// Trimmed: the row loop L1083-L1182 (it only fills dbias_shared/dweight_shared; here each block writes known values),
// the bf16 write-back L1226-L1248 (the last block writes its sums to `out` instead). f128/load128/store128 are common.h's
// Packed128<float> helpers (int4 reinterpret), reduced to a 4-float struct.
#include <cstdio>
#include <cstring>
struct f128 { float v[4]; };
__device__ f128 load128(const float* a) { int4 b = *reinterpret_cast<const int4*>(a); f128 r; memcpy(&r, &b, 16); return r; }
__device__ void store128(float* t, f128 x) { int4 b; memcpy(&b, &x, 16); *reinterpret_cast<int4*>(t) = b; }
__global__ void kernel10_tail(float* scratch, float* out, int C) {
    extern __shared__ float shared[];                       // 2*C + 1 floats
    const int BLOCK_SIZE = blockDim.x;
    float* dbias_shared = shared; float* dweight_shared = shared + C;
    for (int i = threadIdx.x; i < C; i += BLOCK_SIZE) { dbias_shared[i] = blockIdx.x + 1; dweight_shared[i] = 2.0f * (blockIdx.x + 1); }
    __syncthreads();                                                        // L1183
    unsigned int* scratchFlag = (unsigned int*)(scratch);                   // L1187
    scratch += 32;                                                          // L1189
    float* scratch_dbias = scratch; float* scratch_dweight = scratch + C;   // L1190-L1191
    for (int i = threadIdx.x * 4; i < C; i += BLOCK_SIZE * 4) {             // L1192
        store128(scratch_dbias + i + 2*C*blockIdx.x, load128(dbias_shared + i));     // L1194
        store128(scratch_dweight + i + 2*C*blockIdx.x, load128(dweight_shared + i)); // L1195
    }
    __syncthreads();                                                        // L1197
    unsigned int *tmp_flag = (unsigned int*)(shared + 2*C);                 // L1199
    if (threadIdx.x == 0) {
        *tmp_flag = atomicInc(scratchFlag, gridDim.x);                      // L1201
    }
    __syncthreads();                                                        // L1203
    if (*tmp_flag == gridDim.x-1) {                                         // L1204
        for (int i = threadIdx.x * 4; i < C; i += BLOCK_SIZE * 4) {         // L1208
            f128 dbias_accum = {}; f128 dweight_accum = {};
            for (int read_block_idx = 0; read_block_idx < gridDim.x; read_block_idx++) {
                int offset = i + 2*C*read_block_idx;                        // L1213
                f128 dbias128 = load128(scratch_dbias + offset);            // L1214
                f128 dweight128 = load128(scratch_dweight + offset);        // L1215
                for (int k = 0; k < 4; k++) { dbias_accum.v[k] += dbias128.v[k]; dweight_accum.v[k] += dweight128.v[k]; }
            }
            store128(out + i, dbias_accum); store128(out + C + i, dweight_accum);
        }
    }
}
int main() {
    const int C = 1600, block = 512, reps = 200;            // C as in main() L1438; block 512 = kernel10's __launch_bounds__
    int sms = 0; cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0);
    const int grid = 2 * sms;                               // (1024 / block_size) * numSMs, layernorm_backward10()
    float *scratch, *out; cudaMalloc(&scratch, (32 + 2 * C * grid) * sizeof(float)); cudaMalloc(&out, 2 * C * sizeof(float));
    float* h = new float[2 * C]; int bad_runs = 0;
    const float eb = grid * (grid + 1) / 2.0f, ew = 2.0f * eb; // exact in float (grid <= ~300)
    for (int r = 0; r < reps; r++) {
        cudaMemset(scratch, 0, sizeof(float));              // the flag, as layernorm_backward10() L1378
        kernel10_tail<<<grid, block, (2 * C + 1) * sizeof(float)>>>(scratch, out, C);
        cudaMemcpy(h, out, 2 * C * sizeof(float), cudaMemcpyDeviceToHost);
        int bad = 0; for (int i = 0; i < C; i++) bad += (h[i] != eb) + (h[C + i] != ew);
        bad_runs += bad != 0;
    }
    cudaError_t e = cudaDeviceSynchronize(); printf("llmc-new-1 kernel10 tail: grid=%d block=%d reps=%d runs_with_wrong_sums=%d err=%s\n", grid, block, reps, bad_runs, cudaGetErrorString(e));
    printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
    return 0;
}

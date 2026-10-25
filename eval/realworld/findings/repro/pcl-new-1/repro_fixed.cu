// pcl-new-1 reproducer, FIXED (__syncwarp in Warp::reduce, at L109 and after L141): NormalsEstimator::operator() (PCL 66e1d0ea8cc3fa54820eb38e18ad0adac6345b94 gpu/features/src/normal_3d.cu L73-L141) with
// Warp::reduce (gpu/utils/include/pcl/gpu/utils/device/warp.hpp L144-L175), launched as computeNormals(): CTA 256, one warp per point.  Kept:
// the centroid reductions L97-L106, __threadfence_block L109, L114-L141 (cov zeroing, accumulation, six reductions, lane<6 gather).  Trimmed:
// Warp/PtrStep plumbing (laneId asm kept), float3 operators written per component, the size<3 exit L86-L91 (all sizes are 40), and the
// Eigen33 solve L143-L171 (lane 0 writes the six cov values instead; the Eigen-vs-reduce report groups are not reproduced here).
#include <cstdio>
#include <cmath>
__device__ __forceinline__ unsigned int laneId() { unsigned int ret; asm("mov.u32 %0, %laneid;" : "=r"(ret)); return ret; }
struct plus { __forceinline__ __device__ float operator()(const float &lhs, const volatile float& rhs) const { return lhs + rhs; } };
// FIX (warp.hpp): __syncwarp() at entry and exit of both reduces, and between each step's load and store (lanes 0-15: mask 0xffff).
template<typename T, class BinOp> __device__ __forceinline__ void reduce(volatile T* buffer, BinOp op) {
    unsigned int lane = laneId(); __syncwarp(); T val = buffer[lane];
    if (lane < 16) for (int k = 16; k >= 1; k >>= 1) { val = op(val, buffer[lane + k]); __syncwarp(0xffff); buffer[lane] = val; __syncwarp(0xffff); }
    __syncwarp(); }
template<typename T, class BinOp> __device__ __forceinline__ T reduce(volatile T* buffer, T init, BinOp op) {
    unsigned int lane = laneId(); __syncwarp(); T val = buffer[lane] = init; __syncwarp();
    if (lane < 16) for (int k = 16; k >= 1; k >>= 1) { val = op(val, buffer[lane + k]); __syncwarp(0xffff); buffer[lane] = val; __syncwarp(0xffff); }
    __syncwarp(); return buffer[0]; }
__global__ void EstimateNormalsKernel(const int* indices, int pitch, const int* sizes, const float4* points, int n, float* out) {
    __shared__ float cov_buffer[6][256 + 1];
    int warp_idx = threadIdx.x >> 5; int idx = blockIdx.x * 8 + warp_idx;
    if (idx >= n) return;
    int size = sizes[idx]; int lane = laneId(); const int *ibeg = indices + idx * pitch; const int *iend = ibeg + size;
    float3 c = make_float3(0.f, 0.f, 0.f);
    for(const int *t = ibeg + lane; t < iend; t += 32) { float4 p = points[*t]; c.x += p.x; c.y += p.y; c.z += p.z; }
    volatile float *buffer = &cov_buffer[0][threadIdx.x - lane];
    c.x = reduce(buffer, c.x, plus()); c.y = reduce(buffer, c.y, plus()); c.z = reduce(buffer, c.z, plus());   // L103-L105
    c.x *= 1.f/size; c.y *= 1.f/size; c.z *= 1.f/size;
    __syncwarp();                                                                                        // FIX: replaces __threadfence_block() at L109
    int tid = threadIdx.x;
    for(int i = 0; i < 6; ++i) cov_buffer[i][tid] = 0.f;                                                 // L114-L115
    for(const int *t = ibeg + lane; t < iend; t += 32) {
        float4 p = points[*t]; float3 d = make_float3(p.x - c.x, p.y - c.y, p.z - c.z);
        cov_buffer[0][tid] += d.x * d.x; cov_buffer[1][tid] += d.x * d.y; cov_buffer[2][tid] += d.x * d.z;     // L124-L126
        cov_buffer[3][tid] += d.y * d.y; cov_buffer[4][tid] += d.y * d.z; cov_buffer[5][tid] += d.z * d.z; }   // L127-L129
    reduce(&cov_buffer[0][tid - lane], plus()); reduce(&cov_buffer[1][tid - lane], plus()); reduce(&cov_buffer[2][tid - lane], plus());   // L132-L134
    reduce(&cov_buffer[3][tid - lane], plus()); reduce(&cov_buffer[4][tid - lane], plus()); reduce(&cov_buffer[5][tid - lane], plus());   // L135-L137
    volatile float *cov = &cov_buffer[0][tid-lane];
    if (lane < 6) cov[lane] = cov_buffer[lane][tid-lane];                                                // L139-L141
    __syncwarp();                                                                                        // FIX: L141 stores before lane 0 reads cov[]
    if (lane == 0) for (int i = 0; i < 6; ++i) out[idx * 6 + i] = cov[i];                                // stands in for Eigen33 (L144-L171)
}
int main() {
    const int N = 2000, K = 40, PITCH = 64; static float4 pts[N]; static int idx[N * PITCH], sz[N]; static float out[N * 6]; int wrong = 0;
    for (int i = 0; i < N; ++i) { float x = 0.05f * (i % 40), y = 0.05f * (i / 40); pts[i] = make_float4(x, y, 0.1f * x + 0.01f * sinf((float)i), 0.f);
                                  sz[i] = K; for (int j = 0; j < K; ++j) idx[i * PITCH + j] = (i + j * 41) % N; }
    float4* dp; int *di, *ds; float* dout; cudaMalloc(&dp, sizeof pts); cudaMalloc(&di, sizeof idx); cudaMalloc(&ds, sizeof sz); cudaMalloc(&dout, sizeof out);
    cudaMemcpy(dp, pts, sizeof pts, cudaMemcpyHostToDevice); cudaMemcpy(di, idx, sizeof idx, cudaMemcpyHostToDevice); cudaMemcpy(ds, sz, sizeof sz, cudaMemcpyHostToDevice);
    EstimateNormalsKernel<<<(N + 7) / 8, 256>>>(di, PITCH, ds, dp, N, dout);
    if (cudaDeviceSynchronize() != cudaSuccess) { printf("CUDA error\n"); return 2; } cudaMemcpy(out, dout, sizeof out, cudaMemcpyDeviceToHost);
    for (int i = 0; i < N; ++i) {                                                                        // host reference in double
        double c[3] = {0, 0, 0}, v[6] = {0, 0, 0, 0, 0, 0}; bool bad = false;
        for (int j = 0; j < K; ++j) { float4 p = pts[idx[i * PITCH + j]]; c[0] += p.x / K; c[1] += p.y / K; c[2] += p.z / K; }
        for (int j = 0; j < K; ++j) { float4 p = pts[idx[i * PITCH + j]]; double d[3] = {p.x - c[0], p.y - c[1], p.z - c[2]};
            v[0] += d[0]*d[0]; v[1] += d[0]*d[1]; v[2] += d[0]*d[2]; v[3] += d[1]*d[1]; v[4] += d[1]*d[2]; v[5] += d[2]*d[2]; }
        for (int k = 0; k < 6; ++k) bad |= fabs(out[i * 6 + k] - v[k]) > 1e-4 * (1 + fabs(v[k]));
        if (bad && wrong++ < 3) printf("point %d: cov00 got %g expected %g\n", i, out[i * 6], v[0]);
    }
    printf("pcl-new-1 repro_fixed: points=%d wrong=%d -> %s\n", N, wrong, wrong ? "WRONG OUTPUT" : "output correct"); return 0;
}

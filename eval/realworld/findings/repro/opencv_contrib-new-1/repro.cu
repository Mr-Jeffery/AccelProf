// opencv_contrib-new-1 reproducer: compute_hists_kernel_many_blocks<4>, opencv_contrib eca97a4adb2fa32afc82478947d7f049fce57ee1 hog.cu L134-L208,
// launched as compute_hists() (L247-L271) launches it for the default HOG (64x128, cell 8, 2x2 cells, stride 8, 9 bins): grid (2,15), block (32,2,4).
// Kept verbatim: indexing, L167 zeroing, L191/L192 plain +=, the volatile reduction L196-L205, the barrier L208.  Trimmed: the gaussian/interp
// weight (L170-L189, registers only; votes are added unweighted so sums are exact), PtrStep (raw pointer + pitch), copy-out L210-L233.
#include <cstdio>
__constant__ int cnbins, cblock_stride_x, cblock_stride_y, cncells_block_x, cncells_block_y;
template <int nblocks> __global__ void compute_hists_kernel_many_blocks(const int img_block_width, const float* grad, const unsigned char* qangle,
    int step, float* out, int patch_size, int block_patch_size, int threads_cell, int half_cell_size) {
    const int block_x = threadIdx.z; const int cell_x = threadIdx.x / threads_cell; const int cell_y = threadIdx.y; const int cell_thread_x = threadIdx.x & (threads_cell - 1);
    if (blockIdx.x * blockDim.z + block_x >= img_block_width) return;
    extern __shared__ float smem[]; float* hists = smem; float* final_hist = smem + cnbins * block_patch_size * nblocks;
    if (cell_thread_x < patch_size) {
        const int offset_x = (blockIdx.x * blockDim.z + block_x) * cblock_stride_x + half_cell_size * cell_x + cell_thread_x;
        const int offset_y = blockIdx.y * cblock_stride_y + half_cell_size * cell_y;
        const float* grad_ptr = grad + offset_y * step * 2 + offset_x * 2; const unsigned char* qangle_ptr = qangle + offset_y * step * 2 + offset_x * 2;
        float* hist = hists + patch_size * (cell_y * blockDim.z * cncells_block_y + cell_x + block_x * cncells_block_x) + cell_thread_x;
        for (int bin_id = 0; bin_id < cnbins; ++bin_id) hist[bin_id * block_patch_size * nblocks] = 0.f;              // L167
        const int dist_y_begin = -half_cell_size - half_cell_size * (int)threadIdx.y;
        for (int dist_y = dist_y_begin; dist_y < dist_y_begin + patch_size; ++dist_y) {
            float2 vote = *(const float2*)grad_ptr; uchar2 bin = *(const uchar2*)qangle_ptr;
            grad_ptr += step * 2; qangle_ptr += step * 2;
            hist[bin.x * block_patch_size * nblocks] += vote.x;                                                   // L191
            hist[bin.y * block_patch_size * nblocks] += vote.y;                                                   // L192
        }
        volatile float* hist_ = hist;                                                                             // L196
        for (int bin_id = 0; bin_id < cnbins; ++bin_id, hist_ += block_patch_size * nblocks) {
            if (cell_thread_x < patch_size/2) hist_[0] += hist_[patch_size/2];                                    // L199
            if (cell_thread_x < patch_size/4 && (!((patch_size/4) < 3 && cell_thread_x == 0)))
                    hist_[0] += hist_[patch_size/4];                                                              // L201
            if (cell_thread_x == 0) final_hist[((cell_x + block_x * cncells_block_x) * cncells_block_y + cell_y) * cnbins + bin_id]
                    = hist_[0] + hist_[1] + hist_[2];                                                             // L202-L204
        }
    }
    __syncthreads();                                                                                              // L208
    const int t = (threadIdx.z * blockDim.y + threadIdx.y) * blockDim.x + threadIdx.x;
    if (t < cnbins * 4 * nblocks) out[(blockIdx.y * gridDim.x + blockIdx.x) * cnbins * 4 * nblocks + t] = final_hist[t];
}
int main() {
    const int W = 64, H = 128, nb = 9, s = 8, ncb = 2, ibw = (W - 16 + 8) / 8, ibh = (H - 16 + 8) / 8, gx = (ibw + 3) / 4, P = 12;
    static float g[W * H * 2], out[2 * 15 * 144], ref[2 * 15 * 144] = {}; static unsigned char q[W * H * 2];
    for (int i = 0; i < W * H; ++i) { g[2*i] = 1 + i % 3; g[2*i+1] = 1 + i % 2; q[2*i] = (i * 7) % nb; q[2*i+1] = (q[2*i] + 1) % nb; }
    cudaMemcpyToSymbol(cnbins, &nb, 4); cudaMemcpyToSymbol(cblock_stride_x, &s, 4); cudaMemcpyToSymbol(cblock_stride_y, &s, 4); cudaMemcpyToSymbol(cncells_block_x, &ncb, 4); cudaMemcpyToSymbol(cncells_block_y, &ncb, 4);
    float *dg, *dout; unsigned char* dq; cudaMalloc(&dg, sizeof g); cudaMalloc(&dq, sizeof q); cudaMalloc(&dout, sizeof out);
    cudaMemcpy(dg, g, sizeof g, cudaMemcpyHostToDevice); cudaMemcpy(dq, q, sizeof q, cudaMemcpyHostToDevice);
    compute_hists_kernel_many_blocks<4><<<dim3(gx, ibh), dim3(32, 2, 4), (nb * 4 * P * 4 + nb * 4 * 4) * 4>>>(ibw, dg, dq, W, dout, P, 4 * P, 16, 4);
    if (cudaDeviceSynchronize() != cudaSuccess) { printf("CUDA error\n"); return 2; } cudaMemcpy(out, dout, sizeof out, cudaMemcpyDeviceToHost);
    int wrong = 0, n = 0;   // host reference: per cell and bin, the sum of the votes of its 12x12 patch (exact integers)
    for (int by = 0; by < ibh; ++by) for (int bx = 0; bx < gx; ++bx) for (int bz = 0; bz < 4; ++bz) if (bx * 4 + bz < ibw)
      for (int cy = 0; cy < 2; ++cy) for (int cx = 0; cx < 2; ++cx) {
        float* r = ref + (by * gx + bx) * 144 + ((cx + bz * 2) * 2 + cy) * nb;
        for (int c = 0; c < P; ++c) for (int y = 0; y < P; ++y) { int p = (by * 8 + 4 * cy + y) * W + (bx * 4 + bz) * 8 + 4 * cx + c; r[q[2*p]] += g[2*p]; r[q[2*p+1]] += g[2*p+1]; }
        for (int b = 0; b < nb; ++b, ++n) if (out[r - ref + b] != r[b]) { if (wrong < 3) printf("hist %ld: got %g expected %g\n", (long)(r - ref + b), out[r - ref + b], r[b]); ++wrong; }
      }
    printf("opencv_contrib-new-1 repro: bins=%d wrong=%d -> %s\n", n, wrong, wrong ? "WRONG OUTPUT" : "output correct"); return 0;
}

// droidslam-new-1-2 reproducer, FIXED (one __syncthreads() before the swap): frame_distance_kernel (DROID-SLAM 2dfd39f0dcad44012ca7bbb8aa70b55edbfa9c99 src/droid_kernels.cu
// L527-L666), cross-warp race on the shared ix/jx.  Kept: thread 0 loads ix/jx (L554-L556), the barriers L563/L574/L588 (merged
// into one: nothing between them touches ix/jx), the "for (int n=0; n<1; n++)" loop, the pixel loop that reads disps[ix][i][j]
// (L595/L611), the swap by thread 0 without a barrier (L648-L652) and the trailing __syncthreads() (L654).  Trimmed: the pose and
// projection math (only registers) and the blockReduce tail (each thread's total[] is copied out instead; see droidslam-new-1).
#include <cstdio>
#define THREADS 256
#define GPU_1D_KERNEL_LOOP(k, n) for (size_t k = threadIdx.x; k<n; k += blockDim.x)

__global__ void frame_distance_kernel(const float *disps, int ht, int wd, const long *ii, const long *jj, float *out) {
  const int block_id = blockIdx.x, thread_id = threadIdx.x;
  __shared__ int ix;
  __shared__ int jx;
  if (thread_id == 0) { ix = static_cast<int>(ii[block_id]); jx = static_cast<int>(jj[block_id]); }
  __shared__ float total[THREADS]; total[thread_id] = 0;
  __syncthreads();
  for (int n=0; n<1; n++) {
    GPU_1D_KERNEL_LOOP(k, ht*wd) {
      const int i = k / wd;
      const int j = k % wd;
      total[threadIdx.x] += disps[((size_t)ix * ht + i) * wd + j];   // L611 Xi[3] = disps[ix][i][j]
    }
    __syncthreads();                                                 // FIX: readers of ix/jx finish before the swap
    if (threadIdx.x == 0) {
      int tmp = ix;
      ix = jx;
      jx = tmp;
    }
    __syncthreads();
  }
  out[block_id * THREADS + thread_id] = total[thread_id];
}

int main() {
  const int NF = 4, HT = 48, WD = 64;                     // as the target driver: 4 frames, 48x64, the 6 pairs i<j
  long h_ii[6], h_jj[6]; int num = 0;
  for (int i = 0; i < NF; ++i) for (int j = i + 1; j < NF; ++j) { h_ii[num] = i; h_jj[num] = j; ++num; }
  static float h_disps[NF * HT * WD], h_out[6 * THREADS];
  for (int f = 0; f < NF; ++f) for (int p = 0; p < HT * WD; ++p) h_disps[f * HT * WD + p] = (float)(f + 1);   // frame f = f+1
  float *d_disps, *d_out; long *d_ii, *d_jj;
  cudaMalloc(&d_disps, sizeof h_disps); cudaMalloc(&d_out, sizeof h_out); cudaMalloc(&d_ii, sizeof h_ii); cudaMalloc(&d_jj, sizeof h_jj);
  cudaMemcpy(d_disps, h_disps, sizeof h_disps, cudaMemcpyHostToDevice);
  cudaMemcpy(d_ii, h_ii, sizeof h_ii, cudaMemcpyHostToDevice); cudaMemcpy(d_jj, h_jj, sizeof h_jj, cudaMemcpyHostToDevice);
  frame_distance_kernel<<<num, THREADS>>>(d_disps, HT, WD, d_ii, d_jj, d_out);
  if (cudaDeviceSynchronize() != cudaSuccess) { printf("CUDA error\n"); return 2; }
  cudaMemcpy(h_out, d_out, sizeof h_out, cudaMemcpyDeviceToHost);
  int wrong_threads = 0, wrong_blocks = 0;
  for (int b = 0; b < num; ++b) {
    int wb = 0;
    for (int t = 0; t < THREADS; ++t) if (h_out[b * THREADS + t] != (float)(h_ii[b] + 1) * (HT * WD / THREADS)) ++wb;   // 12 px each
    if (wb) printf("block %d (ii=%ld jj=%ld): %d threads read the swapped frame index\n", b, h_ii[b], h_jj[b], wb);
    wrong_threads += wb; wrong_blocks += wb > 0;
  }
  printf("droidslam-new-1-2 repro_fixed: blocks=%d wrong_blocks=%d wrong_threads=%d -> %s\n", num, wrong_blocks, wrong_threads,
         wrong_threads ? "WRONG OUTPUT" : "output correct");
  return 0;
}

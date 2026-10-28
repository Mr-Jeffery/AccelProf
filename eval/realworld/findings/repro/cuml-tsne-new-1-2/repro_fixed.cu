// cuml-tsne-new-1-2 FIXED reproducer (repro.cu + __syncwarp after the stack init, after the stack reads and after the push). Kernel = the tree walk of ML::TSNE::BH::RepulsionKernel, rapidsai/cuml c7e7738bb6386186bc031d821e71ce1c1abfe3c8
// cpp/src/tsne/barnes_hut_kernels.cuh L589-L664 (per-warp stack pos[]/node[]: lane 0 writes, all lanes read, no __syncwarp). Trimmed: the dq
// prologue L565-L599 -> a host-built dq copied once per warp + __syncthreads (finding cuml-tsne-new-1 absent); the force terms L648-L651 and
// L666-L678 -> `normsum += massd[n]`, so a correct walk gives normsum == N for every body. Input: a full quadtree over a 32x32 grid of bodies.
#include <cstdio>
#include <vector>
#define THREADS5 1024
__global__ void walk(const int* childd, const float* massd, const float* posxd, const float* posyd, const int* sortd, const float* dqg,
                     int NNODES, int FOUR_NNODES, int N, int max_depth, float EPS_PLUS_1, float* out) {
  __shared__ int pos[THREADS5], node[THREADS5]; __shared__ float dq[THREADS5];                    // L567-L568
  const int sbase = (threadIdx.x / 32) * 32; const bool SBASE_EQ_THREAD = (sbase == threadIdx.x); const int diff = threadIdx.x - sbase;
  if (diff < max_depth) dq[diff + sbase] = dqg[diff];                // trimmed prologue (see header)
  __syncthreads();
  const auto MAX_SIZE = FOUR_NNODES + 4;
  for (auto k = threadIdx.x + blockIdx.x * blockDim.x; k < N; k += blockDim.x * gridDim.x) {
    const auto i = sortd[k]; if (i < 0 or i >= MAX_SIZE) continue;
    const float px = posxd[i]; const float py = posyd[i]; float normsum = 0.0f; int depth = sbase;
    if (SBASE_EQ_THREAD == true) { pos[sbase] = 0; node[sbase] = FOUR_NNODES; } __syncwarp(__activemask());   // L624-L627 + FIX
    do {
      auto pd = pos[depth];                                                                // L631
      auto nd = node[depth]; __syncwarp(__activemask());                                   // L632 + FIX
      while (pd < 4) {
        const auto index = nd + pd++; if (index < 0 or index >= MAX_SIZE) break;
        const auto n = childd[index]; if (n < 0 or n > NNODES) break;
        const float dx = px - posxd[n]; const float dy = py - posyd[n]; const float dxy1 = dx * dx + dy * dy + EPS_PLUS_1;
        if ((n < N) or __all_sync(__activemask(), dxy1 >= dq[depth])) {                    // L647
          normsum += massd[n];                                                             // trimmed force terms
        } else {
          if (SBASE_EQ_THREAD == true) { pos[depth] = pd; node[depth] = nd; } __syncwarp(__activemask());   // L654-L657 + FIX
          depth++; pd = 0; nd = n * 4;
        }
      }
    } while (--depth >= sbase);                                                            // L664
    out[i] = normsum;
  }
}
const int S = 32, N = S * S; int nextCell = N; std::vector<int> ch(8 * N, -1); std::vector<float> px(2 * N), py(2 * N), ms(2 * N);
int build(int x0, int y0, int s, int root) {           // returns the node id; bodies 0..N-1, cells N..NNODES, root = NNODES
  if (s == 1) { int b = y0 * S + x0; px[b] = x0 + 0.5f; py[b] = y0 + 0.5f; ms[b] = 1; return b; }
  int c = root >= 0 ? root : nextCell++, h = s / 2; float m = 0, cx = 0, cy = 0;
  for (int q = 0; q < 4; q++) { int k = build(x0 + (q & 1) * h, y0 + (q >> 1) * h, h, -1); ch[4 * c + q] = k; m += ms[k]; cx += px[k] * ms[k]; cy += py[k] * ms[k]; }
  ms[c] = m; px[c] = cx / m; py[c] = cy / m; return c;
}
template <class T> T* up(const std::vector<T>& v) { T* d; cudaMalloc(&d, v.size() * sizeof(T)); cudaMemcpy(d, v.data(), v.size() * sizeof(T), cudaMemcpyHostToDevice); return d; }
int main() {
  const int NNODES = N + 340, md = 6, reps = 20; build(0, 0, S, NNODES);           // 1 + 4 + 16 + 64 + 256 = 341 cells
  std::vector<float> dq(32); float r2 = (S / 2.0f) * (S / 2.0f), eps = 0.0025f; dq[0] = r2 / 0.25f;   // as L572-L582, theta = 0.5
  for (int i = 1; i < md; i++) { dq[i] = dq[i - 1] * 0.25f; dq[i - 1] += eps; } dq[md - 1] += eps; for (int i = 0; i < md; i++) dq[i] += 1.0f;
  std::vector<int> sortv(N); for (int i = 0; i < N; i++) sortv[i] = i;
  int *dch = up(ch), *dso = up(sortv); float *dms = up(ms), *dpx = up(px), *dpy = up(py), *ddq = up(dq), *dout; cudaMalloc(&dout, N * 4);
  std::vector<float> h(N); int bad_runs = 0, bad = 0;
  for (int r = 0; r < reps; r++) {
    walk<<<1, THREADS5>>>(dch, dms, dpx, dpy, dso, ddq, NNODES, 4 * NNODES, N, md, eps + 1.0f, dout);
    cudaMemcpy(h.data(), dout, N * 4, cudaMemcpyDeviceToHost);
    int b = 0; for (int i = 0; i < N; i++) b += h[i] != (float)N; bad_runs += b != 0; bad += b;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("cuml-tsne-new-1-2 N=%d cells=%d reps=%d out[0]=%g (expect %d) runs_with_mismatches=%d total_mismatches=%d err=%s\n", N, nextCell - N + 1, reps, h[0], N, bad_runs, bad, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

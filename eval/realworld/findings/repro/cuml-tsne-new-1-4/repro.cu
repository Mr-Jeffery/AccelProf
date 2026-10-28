// cuml-tsne-new-1-4 reproducer. Kernel = ML::TSNE::BH::SummarizationKernel, rapidsai/cuml c7e7738bb6386186bc031d821e71ce1c1abfe3c8
// cpp/src/tsne/barnes_hut_kernels.cuh L351-L482: producer writes countd[k], posxd[k], posyd[k] (plain), __threadfence, then the flag
// massd[k] (volatile); consumers poll massd[ch] (volatile) and then read countd[ch], posxd[ch], posyd[ch] (plain) with no fence in between.
// Trimmed: the five wait-free pre-passes L374-L418 (an optimisation; the main loop L420-L481, kept, summarises every remaining cell);
// statements are upstream's, several joined per line. Launch as barnes_hut_tsne.cuh: <<<SMs * FACTOR3, THREADS3>>>. Input: full quadtree, 32x32 bodies.
#include <cstdio>
#include <cmath>
#include <vector>
#define THREADS3 768
__global__ __launch_bounds__(THREADS3, 1) void SummarizationKernel(int* countd, const int* childd, volatile float* massd, float* posxd,
                                                                   float* posyd, const int NNODES, const int N, const int* bottomd) {
  bool flag = 0; float cm, px, py;
  __shared__ int child[THREADS3 * 4]; __shared__ float mass[THREADS3 * 4];
  const auto bottom = bottomd[0]; const auto inc = blockDim.x * gridDim.x;
  auto k = (bottom & -32) + threadIdx.x + blockIdx.x * blockDim.x; if (k < bottom) k += inc;
  int j = 0;                                                                                  // L420
  while (k <= NNODES) {
    if (massd[k] >= 0) { k += inc; goto SKIP_LOOP; }                                          // L423
    if (j == 0) { j = 4;
      for (int i = 0; i < 4; i++) { const auto ch = childd[k * 4 + i]; child[i * THREADS3 + threadIdx.x] = ch;
        if ((ch < N) or ((mass[i * THREADS3 + threadIdx.x] = massd[ch]) >= 0)) j--; }       // L434
    } else { j = 4;
      for (int i = 0; i < 4; i++) { const auto ch = child[i * THREADS3 + threadIdx.x];
        if ((ch < N) or (mass[i * THREADS3 + threadIdx.x] >= 0) or ((mass[i * THREADS3 + threadIdx.x] = massd[ch]) >= 0)) j--; }  // L442
    }
    if (j == 0) {
      cm = 0.0f; px = 0.0f; py = 0.0f; auto cnt = 0;
#pragma unroll
      for (int i = 0; i < 4; i++) { const auto ch = child[i * THREADS3 + threadIdx.x];
        if (ch >= 0) { const auto m = (ch >= N) ? (cnt += countd[ch], mass[i * THREADS3 + threadIdx.x]) : (cnt++, massd[ch]);  // L459
          cm += m; px += posxd[ch] * m; py += posyd[ch] * m; } }                              // L461-L463
      countd[k] = cnt; const float m = 1.0f / cm; posxd[k] = px * m; posyd[k] = py * m; flag = 1;   // L467-L471
    }
  SKIP_LOOP: __threadfence();                                                               // L475
    if (flag != 0) { massd[k] = cm; k += inc; flag = 0; }                                     // L476-L480
  }
}
const int S = 32, N = S * S; int nextCell = N; std::vector<int> ch(8 * N, -1), cnt(2 * N, 0); std::vector<float> px(2 * N), py(2 * N), ms(2 * N);
int build(int x0, int y0, int s, int root) {           // reference tree; bodies 0..N-1, cells N..NNODES, root = NNODES
  if (s == 1) { int b = y0 * S + x0; px[b] = x0 + 0.5f; py[b] = y0 + 0.5f; ms[b] = 1; return b; }
  int c = root >= 0 ? root : nextCell++, h = s / 2; float m = 0, cx = 0, cy = 0;
  for (int q = 0; q < 4; q++) { int k = build(x0 + (q & 1) * h, y0 + (q >> 1) * h, h, -1); ch[4 * c + q] = k; m += ms[k]; cx += px[k] * ms[k]; cy += py[k] * ms[k]; cnt[c] += k < N ? 1 : cnt[k]; }
  ms[c] = m; px[c] = cx / m; py[c] = cy / m; return c;
}
template <class T> T* up(const std::vector<T>& v) { T* d; cudaMalloc(&d, v.size() * sizeof(T)); cudaMemcpy(d, v.data(), v.size() * sizeof(T), cudaMemcpyHostToDevice); return d; }
int main() {
  const int NNODES = N + 340, reps = 20; build(0, 0, S, NNODES); int sms = 0; cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0);
  std::vector<float> m0(ms), x0(px), y0(py); for (int c = N; c <= NNODES; c++) { m0[c] = -1.0f; x0[c] = y0[c] = 0; }   // ClearKernel2: cells massd = -1
  int *dch = up(ch), *dbot = up(std::vector<int>{N}), *dcnt; cudaMalloc(&dcnt, cnt.size() * 4); float *dm, *dx, *dy; cudaMalloc(&dm, ms.size() * 4); cudaMalloc(&dx, px.size() * 4); cudaMalloc(&dy, py.size() * 4);
  std::vector<float> hm(ms.size()), hx(px.size()), hy(py.size()); std::vector<int> hc(cnt.size()); int bad_runs = 0, bad = 0;
  for (int r = 0; r < reps; r++) {
    cudaMemcpy(dm, m0.data(), m0.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(dx, x0.data(), x0.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(dy, y0.data(), y0.size() * 4, cudaMemcpyHostToDevice);
    SummarizationKernel<<<sms, THREADS3>>>(dcnt, dch, dm, dx, dy, NNODES, N, dbot);
    cudaMemcpy(hm.data(), dm, hm.size() * 4, cudaMemcpyDeviceToHost); cudaMemcpy(hx.data(), dx, hx.size() * 4, cudaMemcpyDeviceToHost); cudaMemcpy(hy.data(), dy, hy.size() * 4, cudaMemcpyDeviceToHost); cudaMemcpy(hc.data(), dcnt, hc.size() * 4, cudaMemcpyDeviceToHost);
    int b = 0; for (int c = N; c <= NNODES; c++) b += hm[c] != ms[c] || hc[c] != cnt[c] || fabsf(hx[c] - px[c]) > 1e-3f || fabsf(hy[c] - py[c]) > 1e-3f; bad_runs += b != 0; bad += b;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("cuml-tsne-new-1-4 cells=%d grid=%d block=%d reps=%d runs_with_wrong_cells=%d total_wrong_cells=%d err=%s\n", NNODES - N + 1, sms, THREADS3, reps, bad_runs, bad, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

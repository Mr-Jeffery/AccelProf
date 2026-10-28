// cuml-tsne-new-1-5 reproducer. Kernel = ML::TSNE::BH::TreeBuildingKernel, rapidsai/cuml c7e7738bb6386186bc031d821e71ce1c1abfe3c8
// cpp/src/tsne/barnes_hut_kernels.cuh L192-L324, statements upstream's (joined per line, comments dropped, value_idx = int, value_t = float):
// lock-free quadtree insertion; childd[] (plain, not volatile) is read with plain loads (L239, L299) while other threads CAS it (L259, L268),
// store it plainly (L283, L291, L303) and unlock it with a plain store after __threadfence (L313-L315). Launch as barnes_hut_tsne.cuh L225
// (<<<SMs * FACTOR2, THREADS2>>>) on the state ClearKernel1 / BoundingBoxKernel leave (childd = -1, bottom = NNODES, root cell = NNODES).
#include <cstdio>
#include <vector>
#define THREADS2 512
#define FACTOR2 3
__global__ __launch_bounds__(THREADS2) void TreeBuildingKernel(int* childd, const float* posxd, const float* posyd, const int NNODES,
                                                               const int N, int* maxdepthd, int* bottomd, const float* radiusd) {
  int j, depth; float x, y, r; float px, py; int ch, n, locked, patch;
  const float radius = radiusd[0]; const float rootx = posxd[NNODES]; const float rooty = posyd[NNODES];
  int localmaxdepth = 1; int skip = 1; const auto inc = blockDim.x * gridDim.x; int i = threadIdx.x + blockIdx.x * blockDim.x;
  while (i < N) {
    if (skip != 0) { skip = 0; n = NNODES; depth = 1; r = radius * 0.5f;
      x = rootx + ((rootx < (px = posxd[i])) ? (j = 1, r) : (j = 0, -r)); y = rooty + ((rooty < (py = posyd[i])) ? (j |= 2, r) : (-r)); }
    while ((ch = childd[n * 4 + j]) >= N) {                                                                     // L239
      n = ch; depth++; r *= 0.5f; x += ((x < px) ? (j = 1, r) : (j = 0, -r)); y += ((y < py) ? (j |= 2, r) : (-r)); }
    if (ch != -2) { locked = n * 4 + j;
      if (ch == -1) {
        if (atomicCAS(&childd[locked], (int)-1, i) == -1) { if (depth > localmaxdepth) localmaxdepth = depth; i += inc; skip = 1; }   // L259
      } else {
        if (ch == atomicCAS(&childd[locked], ch, (int)-2)) { patch = -1;                                         // L268
          while (ch >= 0) { depth++;
            const int cell = atomicAdd(bottomd, (int)-1) - 1;
            if (cell == N) { atomicExch(reinterpret_cast<unsigned long long int*>(bottomd), (unsigned long long int)NNODES); }
            else if (cell < N) { depth--; continue; }
            if (patch != -1) childd[n * 4 + j] = cell;                                                          // L283
            if (cell > patch) patch = cell;
            j = (x < posxd[ch]) ? 1 : 0; if (y < posyd[ch]) j |= 2;
            childd[cell * 4 + j] = ch; n = cell; r *= 0.5f;                                                     // L291
            x += ((x < px) ? (j = 1, r) : (j = 0, -r)); y += ((y < py) ? (j |= 2, r) : (-r));
            ch = childd[n * 4 + j]; if (r <= 1e-10) { break; } }                                                // L299
          childd[n * 4 + j] = i; if (depth > localmaxdepth) localmaxdepth = depth; i += inc; skip = 2; } } }    // L303
    __threadfence();                                                                                            // L313
    if (skip == 2) childd[locked] = patch;                                                                      // L315
  }
  if (localmaxdepth > 32) localmaxdepth = 32;
  atomicMax(maxdepthd, localmaxdepth);
}
int count(const std::vector<int>& c, int node, int N, std::vector<char>& seen) {   // bodies reachable from node; a lock or a repeat poisons it
  if (node < 0) return node == -1 ? 0 : -1000000; if (seen[node]++) return -1000000; if (node < N) return 1;
  int s = 0; for (int q = 0; q < 4; q++) s += count(c, c[4 * node + q], N, seen); return s;
}
int main() {
  const int N = 50000, NNODES = 2 * N + 31, reps = 20; int sms = 0, one = 1, bad_runs = 0, last = 0; cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, 0);
  std::vector<float> x(NNODES + 1), y(NNODES + 1); unsigned s = 3u; for (int i = 0; i < N; i++) { s = s * 1664525u + 1013904223u; x[i] = (s >> 8) / 16777216.0f; s = s * 1664525u + 1013904223u; y[i] = (s >> 8) / 16777216.0f; }
  x[NNODES] = y[NNODES] = 0.5f; float rad = 0.5f + 1e-5f; std::vector<int> c(4 * (NNODES + 1)); int *dc, *dmd, *db; float *dx, *dy, *dr;
  cudaMalloc(&dc, c.size() * 4); cudaMalloc(&dmd, 4); cudaMalloc(&db, 8); cudaMalloc(&dx, x.size() * 4); cudaMalloc(&dy, y.size() * 4); cudaMalloc(&dr, 4);
  cudaMemcpy(dx, x.data(), x.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(dy, y.data(), y.size() * 4, cudaMemcpyHostToDevice); cudaMemcpy(dr, &rad, 4, cudaMemcpyHostToDevice);
  for (int r = 0; r < reps; r++) {
    cudaMemset(dc, 0xff, c.size() * 4); cudaMemcpy(db, &NNODES, 4, cudaMemcpyHostToDevice); cudaMemcpy(dmd, &one, 4, cudaMemcpyHostToDevice);
    TreeBuildingKernel<<<sms * FACTOR2, THREADS2>>>(dc, dx, dy, NNODES, N, dmd, db, dr);
    cudaMemcpy(c.data(), dc, c.size() * 4, cudaMemcpyDeviceToHost); std::vector<char> seen(NNODES + 1, 0); last = count(c, NNODES, N, seen); bad_runs += last != N;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("cuml-tsne-new-1-5 N=%d grid=%d block=%d reps=%d bodies_in_tree(last)=%d runs_with_bad_tree=%d err=%s\n", N, sms * FACTOR2, THREADS2, reps, last, bad_runs, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

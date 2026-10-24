// R2 host driver for cuml-tsne-new-1 (T21c), written for this study (not upstream code).
// Calls ML::TSNE::Barnes_Hut<int, float> from the pinned commit's cpp/src/tsne/barnes_hut_tsne.cuh (copied verbatim) with a small
// attractive-force COO matrix built on the host, i.e. the same entry point tsne_runner.cuh calls after kNN + perplexity + symmetrisation.
// usage: driver [n=1000] [max_iter=2]
#include <cuml/manifold/tsne.h>

#include "barnes_hut_tsne.cuh"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <set>
#include <vector>

int main(int argc, char** argv)
{
  const int n        = argc > 1 ? std::atoi(argv[1]) : 1000;
  const int max_iter = argc > 2 ? std::atoi(argv[2]) : 2;
  const int k        = 8;  // neighbours per point

  // 2-D points: four Gaussian clusters (so the quadtree is non-trivial), scaled the way a PCA initialisation is (small).
  std::mt19937 gen(1);
  std::normal_distribution<float> nd(0.f, 1.f);
  const float cx[4] = {-5.f, 5.f, -5.f, 5.f}, cy[4] = {-5.f, -5.f, 5.f, 5.f};
  std::vector<float> hx(n), hy(n);
  for (int i = 0; i < n; i++) {
    hx[i] = (cx[i % 4] + nd(gen)) * 0.01f;
    hy[i] = (cy[i % 4] + nd(gen)) * 0.01f;
  }

  // brute-force kNN, symmetrised adjacency; COO sorted by (row, col), all values equal and summing to 1
  std::vector<std::set<int>> adj(n);
  std::vector<std::pair<float, int>> d(n);
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++)
      d[j] = {(hx[i] - hx[j]) * (hx[i] - hx[j]) + (hy[i] - hy[j]) * (hy[i] - hy[j]), j};
    d[i].first = 1e30f;
    std::partial_sort(d.begin(), d.begin() + k, d.end());
    for (int q = 0; q < k; q++) {
      adj[i].insert(d[q].second);
      adj[d[q].second].insert(i);
    }
  }
  std::vector<int> hrow, hcol;
  for (int i = 0; i < n; i++)
    for (int j : adj[i]) {
      hrow.push_back(i);
      hcol.push_back(j);
    }
  const int nnz = static_cast<int>(hrow.size());
  std::vector<float> hval(nnz, 1.0f / nnz);

  float *dval, *dY;
  int *dcol, *drow;
  RAFT_CUDA_TRY(cudaMalloc(&dval, nnz * sizeof(float)));
  RAFT_CUDA_TRY(cudaMalloc(&dcol, nnz * sizeof(int)));
  RAFT_CUDA_TRY(cudaMalloc(&drow, nnz * sizeof(int)));
  RAFT_CUDA_TRY(cudaMalloc(&dY, 2 * n * sizeof(float)));
  RAFT_CUDA_TRY(cudaMemcpy(dval, hval.data(), nnz * sizeof(float), cudaMemcpyHostToDevice));
  RAFT_CUDA_TRY(cudaMemcpy(dcol, hcol.data(), nnz * sizeof(int), cudaMemcpyHostToDevice));
  RAFT_CUDA_TRY(cudaMemcpy(drow, hrow.data(), nnz * sizeof(int), cudaMemcpyHostToDevice));
  RAFT_CUDA_TRY(cudaMemcpy(dY, hx.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  RAFT_CUDA_TRY(cudaMemcpy(dY + n, hy.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  ML::TSNEParams params;
  params.dim               = 2;
  params.theta             = 0.5f;
  params.epssq             = 0.0025f;
  params.init              = ML::TSNE_INIT::PCA;  // take Y as given (random_vector is not used)
  params.max_iter          = max_iter;
  params.exaggeration_iter = 1;  // iteration 0 exaggerated, the rest after the switch
  params.algorithm         = ML::TSNE_ALGORITHM::BARNES_HUT;

  raft::handle_t handle(0);
  auto res = ML::TSNE::Barnes_Hut<int, float>(dval, dcol, drow, nnz, handle, dY, n, params);
  RAFT_CUDA_TRY(cudaDeviceSynchronize());

  std::vector<float> out(2 * n);
  RAFT_CUDA_TRY(cudaMemcpy(out.data(), dY, 2 * n * sizeof(float), cudaMemcpyDeviceToHost));
  int finite = 0;
  double sum = 0;
  for (float v : out) {
    finite += std::isfinite(v) ? 1 : 0;
    sum += std::isfinite(v) ? v : 0;
  }
  std::printf("n=%d nnz=%d max_iter=%d iters_run=%d kl=%g finite=%d/%d checksum=%.6f\n",
              n, nnz, max_iter, res.second, res.first, finite, 2 * n, sum);
  return finite == 2 * n ? 0 : 1;
}

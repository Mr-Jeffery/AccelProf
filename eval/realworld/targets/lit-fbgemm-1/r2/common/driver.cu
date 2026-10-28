// T21a lit-fbgemm-1 host main (identical for the buggy and the fixed variant).
// The verbatim fast_gemv.cu of the revision (with its own fast_gemv.cuh and utility.cuh, copied from the same revision)
// is #included; header-only CUTLASS is the only other dependency.  The kernel is launched like
// bf16_fast_gemv.cu does: gemv_bf16<<<dim3(1, n / block.y), block>>>(mat, vec, res, k, m, n, k / block.x), block = (256, 1).
#include <fbgemm_gpu/experimental/gen_ai/src/quantize/fast_gemv/include/fast_gemv.cu>

#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // m = number of vector rows (the col loop trip count; the race needs m >= 2 and blockDim.x > 32),
  // n = matrix rows (output length), k = reduction length.  Defaults: m=2, n=64, k=2048, block (256,1).
  const unsigned m = argc > 1 ? (unsigned)std::atoi(argv[1]) : 2;
  const unsigned n = argc > 2 ? (unsigned)std::atoi(argv[2]) : 64;
  const unsigned k = argc > 3 ? (unsigned)std::atoi(argv[3]) : 2048;
  dim3 block(256, 1);
  dim3 grid(1, n / block.y);
  const unsigned num_per_thread = k / block.x;

  std::vector<__nv_bfloat16> h_mat((size_t)n * k), h_vec((size_t)m * k), h_res((size_t)m * n);
  // small integers: all partial sums are exact in float, so the bf16 result is reproducible bit for bit
  for (unsigned r = 0; r < n; ++r)
    for (unsigned c = 0; c < k; ++c) h_mat[(size_t)r * k + c] = __float2bfloat16((float)((int)((r * 7 + c * 3) % 5) - 2));
  for (unsigned r = 0; r < m; ++r)
    for (unsigned c = 0; c < k; ++c) h_vec[(size_t)r * k + c] = __float2bfloat16((float)((int)((r * 11 + c * 5) % 7) - 3));

  __nv_bfloat16 *d_mat = nullptr, *d_vec = nullptr, *d_res = nullptr;
  CK(cudaMalloc(&d_mat, sizeof(__nv_bfloat16) * h_mat.size()));
  CK(cudaMalloc(&d_vec, sizeof(__nv_bfloat16) * h_vec.size()));
  CK(cudaMalloc(&d_res, sizeof(__nv_bfloat16) * h_res.size()));
  CK(cudaMemcpy(d_mat, h_mat.data(), sizeof(__nv_bfloat16) * h_mat.size(), cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_vec, h_vec.data(), sizeof(__nv_bfloat16) * h_vec.size(), cudaMemcpyHostToDevice));
  CK(cudaMemset(d_res, 0, sizeof(__nv_bfloat16) * h_res.size()));

  gemv_bf16<<<grid, block>>>(d_mat, d_vec, d_res, k, m, n, num_per_thread);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  CK(cudaMemcpy(h_res.data(), d_res, sizeof(__nv_bfloat16) * h_res.size(), cudaMemcpyDeviceToHost));
  long bad = 0;
  for (unsigned c = 0; c < m; ++c)
    for (unsigned r = 0; r < n; ++r) {
      float acc = 0.0f;
      for (unsigned i = 0; i < k; ++i) acc += __bfloat162float(h_mat[(size_t)r * k + i]) * __bfloat162float(h_vec[(size_t)c * k + i]);
      bad += (__bfloat162float(h_res[(size_t)r + (size_t)c * n]) != __bfloat162float(__float2bfloat16(acc)));
    }
  std::printf("gemv_bf16 m=%u n=%u k=%u grid=(%u,%u) block=(%u,%u) num_per_thread=%u mismatches=%ld/%zu\n",
              m, n, k, grid.x, grid.y, block.x, block.y, num_per_thread, bad, h_res.size());
  return 0;
}

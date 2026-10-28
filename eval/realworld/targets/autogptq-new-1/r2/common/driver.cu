// T21c autogptq-new-1 host main (R2).  The verbatim autogptq_extension/marlin/marlin_repack.cu (with its own marlin_repack.cuh,
// both copied from the pinned commit 9f7d3707) is #included; gptq_repack() (host, needs libtorch) is compiled but never called.
// The kernel is launched exactly as gptq_repack() launches it: gptq_repack_kernel<<<dim3(m/2, n/64), 32>>>(in, out, m, n).
#include <autogptq_extension/marlin/marlin_repack.cu>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // W is the GPTQ int32 tensor [m, n] (m even, n a multiple of 64); default 2 x 64 -> grid (1,1), one 32-lane warp.
  const int m = argc > 1 ? std::atoi(argv[1]) : 2;
  const int n = argc > 2 ? std::atoi(argv[2]) : 64;
  if (m % 2 || n % 64) { std::fprintf(stderr, "m must be even, n a multiple of 64\n"); return 1; }
  const size_t in_words = (size_t)m * n, out_words = (size_t)(m / 2) * n * 2;

  std::vector<uint32_t> h_in(in_words), h_out(out_words, 0xdeadbeefu);
  uint32_t s = 12345u;                                  // deterministic LCG fill: every word packs eight 4-bit values
  for (auto& w : h_in) { s = s * 1664525u + 1013904223u; w = s; }

  uint32_t *d_in = nullptr, *d_out = nullptr;
  CK(cudaMalloc(&d_in, in_words * 4));
  CK(cudaMalloc(&d_out, out_words * 4));
  CK(cudaMemcpy(d_in, h_in.data(), in_words * 4, cudaMemcpyHostToDevice));
  CK(cudaMemset(d_out, 0xef, out_words * 4));

  const dim3 blocks(m / 2, n / 64);
  gptq_repack_kernel<<<blocks, 32>>>(d_in, d_out, m, n);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());
  CK(cudaMemcpy(h_out.data(), d_out, out_words * 4, cudaMemcpyDeviceToHost));

  // Host reference: the kernel's two phases executed lane by lane in program order (unpack for all 32 lanes, then repack).
  std::vector<uint32_t> ref(out_words, 0xefefefefu);
  for (int bx = 0; bx < m / 2; ++bx) for (int by = 0; by < n / 64; ++by) {
    uint8_t block[4][16][18]; std::memset(block, 0, sizeof(block));
    const uint32_t row = bx * 2, col = by * 64;
    for (int t = 0; t < 32; ++t) {
      const int bi = t / 8, bo = t % 8;
      for (int off = bo; off < 16; off += 8) {
        uint32_t v1 = h_in[row * n + col + bi * 16 + off], v2 = h_in[(row + 1) * n + col + bi * 16 + off];
        for (int i = 0; i < 8; ++i) { block[bi][i][off] = v1 & 0xf; v1 >>= 4; block[bi][i + 8][off] = v2 & 0xf; v2 >>= 4; }
      }
    }
    for (int t = 0; t < 32; ++t) {
      const uint32_t srow = (t % 4) * 2, scol = t / 4;
      const uint32_t idx[8][2] = {{srow, scol}, {srow + 8, scol}, {srow, scol + 8}, {srow + 8, scol + 8},
                                  {srow + 1, scol}, {srow + 9, scol}, {srow + 1, scol + 8}, {srow + 9, scol + 8}};
      for (int i = 0; i < 4; ++i) {
        uint32_t v[8]; for (int j = 0; j < 8; ++j) v[j] = block[i][idx[j][0]][idx[j][1]];
        ref[(size_t)bx * n * 2 + by * 128 + t * 4 + i] = (v[7] << 28) | (v[6] << 24) | (v[5] << 20) | (v[4] << 16) | (v[3] << 12) | (v[2] << 8) | (v[1] << 4) | v[0];
      }
    }
  }
  int bad = 0;
  for (size_t i = 0; i < out_words; ++i) bad += (h_out[i] != ref[i]);
  std::printf("gptq_repack_kernel m=%d n=%d grid=(%d,%d) block=32 out[0..3]=%08x,%08x,%08x,%08x mismatches=%d/%zu\n",
              m, n, blocks.x, blocks.y, h_out[0], h_out[1], h_out[2], h_out[3], bad, out_words);
  return 0;
}

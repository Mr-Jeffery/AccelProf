// autogptq-new-1 reproducer. Kernel copied verbatim from AutoGPTQ/AutoGPTQ 9f7d37072917ab3a7545835f23e808294a542153
// autogptq_extension/marlin/marlin_repack.cu L8-L66 (gptq_repack_kernel), launched as gptq_repack() L82-L91:
// <<<dim3(m/2, n/64), 32>>>. Trimmed: the torch includes and the host wrapper gptq_repack() (libtorch); comments.
#include <cstdio>
#include <cstdint>
#include <cstring>
__global__ void gptq_repack_kernel(uint32_t* in, uint32_t* out, int m, int n) {
  uint32_t row = blockIdx.x * 2; uint32_t col = blockIdx.y * 64; uint32_t t = threadIdx.x;
  const int pad_len = 18;
  __shared__ uint8_t block[4][16][pad_len];
  int block_idx = t / 8; int block_offset = t % 8;                         // unpack
  for (int offset = block_offset; offset < 16; offset += 8) {              // L25
    uint32_t v1 = in[row * n + col + block_idx * 16 + offset];
    uint32_t v2 = in[(row + 1) * n + col + block_idx * 16 + offset];
#pragma unroll
    for (int i = 0; i < 8; i += 1) {
      block[block_idx][i][offset] = v1 & 0xf;                              // L30
      v1 >>= 4;
      block[block_idx][i + 8][offset] = v2 & 0xf;                          // L32
      v2 >>= 4;
    }
  }
  uint32_t srow = (t % 4) * 2; uint32_t scol = t / 4;                      // repack (L37-L40)
  uint32_t idx[8][2];
  idx[0][0] = srow;     idx[0][1] = scol;     idx[1][0] = srow + 8; idx[1][1] = scol;
  idx[2][0] = srow;     idx[2][1] = scol + 8; idx[3][0] = srow + 8; idx[3][1] = scol + 8;
  idx[4][0] = srow + 1; idx[4][1] = scol;     idx[5][0] = srow + 9; idx[5][1] = scol;
  idx[6][0] = srow + 1; idx[6][1] = scol + 8; idx[7][0] = srow + 9; idx[7][1] = scol + 8;
#pragma unroll
  for (int i = 0; i < 4; i += 1) {
    uint32_t v[8];
#pragma unroll
    for (int j = 0; j < 8; ++j) { v[j] = block[i][idx[j][0]][idx[j][1]]; }            // L58
    uint32_t pack = (v[7] << 28) | (v[6] << 24) | (v[5] << 20) | (v[4] << 16) | (v[3] << 12) | (v[2] << 8) | (v[1] << 4) | v[0];
    out[blockIdx.x * n * 2 + blockIdx.y * 128 + t * 4 + i] = pack;          // L64
  }
}
int main() {
  const int m = 64, n = 256, reps = 50, iw = m * n, ow = (m / 2) * n * 2;   // m even, n % 64 == 0 (gptq_repack asserts)
  uint32_t *hi = new uint32_t[iw], *ho = new uint32_t[ow], *ref = new uint32_t[ow], *di, *dout; uint32_t s = 12345u;
  for (int i = 0; i < iw; i++) { s = s * 1664525u + 1013904223u; hi[i] = s; }
  for (int bx = 0; bx < m / 2; bx++) for (int by = 0; by < n / 64; by++) {  // host reference: unpack all lanes, then repack
    uint8_t b[4][16][18]; memset(b, 0, sizeof(b));
    for (int t = 0; t < 32; t++) for (int off = t % 8; off < 16; off += 8) { uint32_t v1 = hi[bx*2*n + by*64 + (t/8)*16 + off], v2 = hi[(bx*2+1)*n + by*64 + (t/8)*16 + off];
      for (int i = 0; i < 8; i++) { b[t/8][i][off] = v1 & 0xf; v1 >>= 4; b[t/8][i+8][off] = v2 & 0xf; v2 >>= 4; } }
    for (int t = 0; t < 32; t++) { uint32_t r = (t % 4) * 2, c = t / 4, rr[8] = {r, r+8, r, r+8, r+1, r+9, r+1, r+9}, cc[8] = {c, c, c+8, c+8, c, c, c+8, c+8};
      for (int i = 0; i < 4; i++) { uint32_t p = 0; for (int j = 0; j < 8; j++) p |= (uint32_t)b[i][rr[j]][cc[j]] << (4 * j); ref[bx*n*2 + by*128 + t*4 + i] = p; } }
  }
  cudaMalloc(&di, iw * 4); cudaMalloc(&dout, ow * 4); cudaMemcpy(di, hi, iw * 4, cudaMemcpyHostToDevice); int bad_runs = 0, bad = 0;
  for (int r = 0; r < reps; r++) {
    cudaMemset(dout, 0xef, ow * 4); gptq_repack_kernel<<<dim3(m / 2, n / 64), 32>>>(di, dout, m, n);
    cudaMemcpy(ho, dout, ow * 4, cudaMemcpyDeviceToHost);
    int b = 0; for (int i = 0; i < ow; i++) b += ho[i] != ref[i]; bad_runs += b != 0; bad += b;
  }
  cudaError_t e = cudaDeviceSynchronize(); printf("autogptq-new-1 m=%d n=%d grid=(%d,%d) block=32 reps=%d runs_with_mismatches=%d total_mismatches=%d err=%s\n", m, n, m / 2, n / 64, reps, bad_runs, bad, cudaGetErrorString(e));
  printf("RESULT: %s\n", e != cudaSuccess ? "ERROR" : bad_runs ? "WRONG" : "OK");
  return 0;
}

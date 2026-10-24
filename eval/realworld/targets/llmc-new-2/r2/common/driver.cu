// T21c llmc-new-2 host main (R2).  The verbatim llmc/attention.cuh (+ llmc/cuda_utils.cuh and the headers they include,
// llmc/cuda_common.h, llmc/utils.h, llmc/cublas_common.h, all copied byte-for-byte from f1e2ace651) is #included.
// Stubs: `deviceProp` (defined by train_gpt2.cu upstream) and `matmul_cublaslt` (llmc/matmul.cuh; called only by the host
// launchers attention_forward/attention_backward, which this driver never calls).
// The kernel is launched exactly as attention_backward() launches it (attention.cuh L266):
//     softmax_autoregressive_backward_inplace_kernel<<<dim3(T / 4, B * NH), 256>>>(datt, att, B, T, C, scale)
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <cuda_runtime.h>

cudaDeviceProp deviceProp;   // upstream: defined in the main program file (train_gpt2.cu)

template <class... Args>
inline void matmul_cublaslt(Args&&...) {   // stub of llmc/matmul.cuh; never called
    std::fprintf(stderr, "matmul_cublaslt stub called\n");
    std::abort();
}

// CUDA 13 compatibility overload: the toolkit's cudaMemAdvise takes a cudaMemLocation, cuda_utils.cuh L220 (host code) passes an int device id.
static inline cudaError_t cudaMemAdvise(const void* ptr, size_t count, enum cudaMemoryAdvise advice, int device) {
    cudaMemLocation loc; loc.type = device < 0 ? cudaMemLocationTypeHost : cudaMemLocationTypeDevice; loc.id = device < 0 ? 0 : device;
    return cudaMemAdvise(ptr, count, advice, loc);
}

#include "llmc/attention.cuh"

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // T = 64, B*NH = 1 (B = 1, NH = 1, HS = 64 -> C = 64).  Grid dim3(T/4, B*NH) = (16, 1), 256 threads (8 warps).
  const int B = 1, NH = 1, T = argc > 1 ? std::atoi(argv[1]) : 64, HS = 64, C = NH * HS;
  const float scale = 1.0f / std::sqrt((float)HS);
  const size_t n = (size_t)B * NH * T * T;

  // att: causal softmax rows (uniform 1/(t+1) over t2 <= t, zero above the diagonal); datt: pseudo-random.
  std::vector<floatX> h_att(n), h_datt(n);
  unsigned s = 12345u;
  for (int t = 0; t < T; ++t)
    for (int i = 0; i < T; ++i) {
      s = s * 1664525u + 1013904223u;
      h_att[(size_t)t * T + i]  = (floatX)(i <= t ? 1.0f / (float)(t + 1) : 0.0f);
      h_datt[(size_t)t * T + i] = (floatX)(((s >> 8) & 0xffff) / 65536.0f - 0.5f);
    }

  floatX *d_att = nullptr, *d_datt = nullptr;
  CK(cudaMalloc(&d_att, n * sizeof(floatX)));
  CK(cudaMalloc(&d_datt, n * sizeof(floatX)));
  CK(cudaMemcpy(d_att, h_att.data(), n * sizeof(floatX), cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_datt, h_datt.data(), n * sizeof(floatX), cudaMemcpyHostToDevice));

  softmax_autoregressive_backward_inplace_kernel<<<dim3(T / 4, B * NH), 256>>>(d_datt, d_att, B, T, C, scale);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<floatX> h_out(n);
  CK(cudaMemcpy(h_out.data(), d_datt, n * sizeof(floatX), cudaMemcpyDeviceToHost));

  // host reference of the in-place softmax backward: dpreatt[t][i] = scale * att[t][i] * (datt[t][i] - sum_j att[t][j]*datt[t][j])
  int bad = 0;
  for (int t = 0; t < T; ++t) {
    float sum = 0;
    for (int j = 0; j <= t; ++j) sum += (float)h_att[(size_t)t * T + j] * (float)h_datt[(size_t)t * T + j];
    for (int i = 0; i < T; ++i) {
      float ref = i <= t ? scale * (float)h_att[(size_t)t * T + i] * ((float)h_datt[(size_t)t * T + i] - sum) : 0.0f;
      float got = (float)h_out[(size_t)t * T + i];
      if (std::fabs(ref - got) > 1e-2f * (std::fabs(ref) + 1e-3f)) ++bad;
    }
  }
  std::printf("softmax_autoregressive_backward_inplace_kernel B=%d NH=%d T=%d C=%d grid=(%d,%d) block=256 mismatches=%d/%zu\n",
              B, NH, T, C, T / 4, B * NH, bad, n);
  return 0;
}

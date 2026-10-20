// T21a pytorch-3 host main (identical for the buggy and the fixed variant).
// The verbatim MultiMarginLoss.cu of the revision is #included so that the kernel in the anonymous namespace
// at::native::{anon} is reachable; the ATen host code of that file is compiled (against the installed PyTorch headers)
// but never called.  The kernel is launched exactly as multi_margin_loss_cuda_backward_out does for a 1-D input
// (input.dim() <= 1): blocks = 1, threads = MULTIMARGIN_THREADS = 128, p = 1, reduction = Mean, no weights,
// i.e. what torch.nn.MultiMarginLoss()(x, y).backward() launches for x = randn(128), y = tensor(64).
#include <aten/src/ATen/native/cuda/MultiMarginLoss.cu>

#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv) {
  // dim = input length (one frame), tgt = target class.  The race needs tgt % 128 != 0; tgt = 64 puts the
  // thread that owns the slot (threadIdx.x == 64, warp 2) in a different warp from thread 0 (warp 0).
  const int dim = argc > 1 ? std::atoi(argv[1]) : 128;
  const long long tgt = argc > 2 ? std::atoll(argv[2]) : 64;
  const int nframe = 1;
  const float margin = 1.0f;
  const float gout = 2.0f;   // scalar grad_output (reduction = Mean), 2.0 so that a lost scaling is visible

  std::vector<float> h_in(dim);
  unsigned s = 4242u;
  for (int i = 0; i < dim; ++i) {
    s = s * 1664525u + 1013904223u;
    h_in[i] = (float)((int)((s >> 10) % 33) - 16) * 0.125f;   // multiples of 1/8 in [-2, 2]
  }

  float *d_in = nullptr, *d_gin = nullptr, *d_gout = nullptr; int64_t* d_tgt = nullptr;
  CK(cudaMalloc(&d_in, sizeof(float) * dim));
  CK(cudaMalloc(&d_gin, sizeof(float) * dim));
  CK(cudaMalloc(&d_gout, sizeof(float)));
  CK(cudaMalloc(&d_tgt, sizeof(int64_t)));
  CK(cudaMemcpy(d_in, h_in.data(), sizeof(float) * dim, cudaMemcpyHostToDevice));
  CK(cudaMemcpy(d_gout, &gout, sizeof(float), cudaMemcpyHostToDevice));
  int64_t t64 = (int64_t)tgt;
  CK(cudaMemcpy(d_tgt, &t64, sizeof(int64_t), cudaMemcpyHostToDevice));
  CK(cudaMemset(d_gin, 0, sizeof(float) * dim));

  dim3 blocks(1);
  dim3 threads(at::native::MULTIMARGIN_THREADS);
  at::native::MultiMarginLoss_backward_kernel<1, float><<<blocks, threads>>>(
      d_gin, d_gout, d_in, d_tgt, /*weights=*/nullptr, nframe, dim, /*sizeAverage=*/true, margin, /*reduce=*/true);
  CK(cudaGetLastError());
  CK(cudaDeviceSynchronize());

  std::vector<float> h_gin(dim), ref(dim, 0.0f);
  CK(cudaMemcpy(h_gin.data(), d_gin, sizeof(float) * dim, cudaMemcpyDeviceToHost));
  // reference (all values are multiples of 1/128, so float sums are exact)
  const float g = 1.0f / (float)(nframe * dim);
  float sum = 0.0f;
  for (int i = 0; i < dim; ++i) {
    if (i == tgt) continue;
    float z = margin - h_in[tgt] + h_in[i];
    if (z > 0) { ref[i] = g; sum -= g; }
  }
  ref[tgt] = sum;
  for (int i = 0; i < dim; ++i) ref[i] *= gout;
  int bad = 0;
  for (int i = 0; i < dim; ++i) bad += (h_gin[i] != ref[i]);
  std::printf("MultiMarginLoss_backward_kernel<1,float> dim=%d target=%lld blocks=1 threads=128 gradInput[target]=%g expected=%g mismatches=%d/%d\n",
              dim, (long long)tgt, h_gin[tgt], ref[tgt], bad, dim);
  return 0;
}

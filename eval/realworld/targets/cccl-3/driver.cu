// cccl-3 driver (T21a): cub::DeviceTopK::MaxKeys over 1e5 keys (more than one tile, so gridDim.x > 1 and the
// finalize_pass last-block hand-off is exercised).  Our own code; headers are the checkout's (R1h).
#include <cub/device/device_topk.cuh>
#include <cuda/__execution/determinism.h>
#include <cuda/__execution/output_ordering.h>
#include <cuda/__execution/require.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <vector>

int main(int argc, char** argv)
{
  const int n = argc > 1 ? atoi(argv[1]) : 100000;
  const int k = argc > 2 ? atoi(argv[2]) : 16;
  std::vector<unsigned> h(n);
  unsigned s = 12345u;
  for (int i = 0; i < n; ++i) { s = s * 1664525u + 1013904223u; h[i] = s; }
  unsigned *d_in, *d_out;
  cudaMalloc(&d_in, n * sizeof(unsigned));
  cudaMalloc(&d_out, k * sizeof(unsigned));
  cudaMemcpy(d_in, h.data(), n * sizeof(unsigned), cudaMemcpyHostToDevice);
  auto env = cuda::execution::require(cuda::execution::determinism::not_guaranteed, cuda::execution::output_ordering::unsorted);
  void* d_temp   = nullptr;
  size_t t_bytes = 0;
  cub::DeviceTopK::MaxKeys(d_temp, t_bytes, d_in, d_out, (long) n, (long) k, env);
  cudaMalloc(&d_temp, t_bytes);
  cudaError_t e1 = cub::DeviceTopK::MaxKeys(d_temp, t_bytes, d_in, d_out, (long) n, (long) k, env);
  cudaError_t e2 = cudaDeviceSynchronize();
  std::vector<unsigned> out(k), ref(h);
  cudaMemcpy(out.data(), d_out, k * sizeof(unsigned), cudaMemcpyDeviceToHost);
  std::sort(ref.begin(), ref.end(), std::greater<unsigned>());
  ref.resize(k);
  std::sort(out.begin(), out.end(), std::greater<unsigned>());
  printf("cccl-3 DeviceTopK::MaxKeys n=%d k=%d call=%s run=%s %s\n", n, k, cudaGetErrorString(e1), cudaGetErrorString(e2),
         out == ref ? "result==reference" : "RESULT DIFFERS from reference");
  return (e1 == cudaSuccess && e2 == cudaSuccess) ? 0 : 1;
}

// cccl-1 driver (T21a): the shape of cub/test/catch2_test_block_reduce.cu's kernel for T=uint8_t, 65 threads,
// BLOCK_REDUCE_RAKING, one block.  Our own code; the CCCL headers it includes are the checkout's (R1h).
#include <cub/block/block_reduce.cuh>
#include <cstdint>
#include <cstdio>

constexpr int kThreads = 65;

__global__ void block_reduce_kernel(const uint8_t* in, uint8_t* out)
{
  using BlockReduceT = cub::BlockReduce<uint8_t, kThreads, cub::BLOCK_REDUCE_RAKING>;
  __shared__ typename BlockReduceT::TempStorage temp_storage;
  uint8_t thread_data = in[threadIdx.x];
  uint8_t aggregate   = BlockReduceT(temp_storage).Sum(thread_data);
  if (threadIdx.x == 0) { out[0] = aggregate; }
}

int main()
{
  uint8_t h_in[kThreads], h_out = 0;
  unsigned expect = 0;
  for (int i = 0; i < kThreads; ++i) { h_in[i] = (uint8_t) (i % 4 + 1); expect += h_in[i]; }
  uint8_t *d_in, *d_out;
  cudaMalloc(&d_in, kThreads);
  cudaMalloc(&d_out, 1);
  cudaMemcpy(d_in, h_in, kThreads, cudaMemcpyHostToDevice);
  block_reduce_kernel<<<1, kThreads>>>(d_in, d_out);
  cudaError_t e = cudaDeviceSynchronize();
  cudaMemcpy(&h_out, d_out, 1, cudaMemcpyDeviceToHost);
  printf("cccl-1 block_reduce_kernel<<<1,%d>>> cuda=%s sum=%u expect(mod 256)=%u\n", kThreads, cudaGetErrorString(e),
         (unsigned) h_out, expect & 0xffu);
  return e == cudaSuccess ? 0 : 1;
}

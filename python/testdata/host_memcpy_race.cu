// host_memcpy_race.cu (T2): a host cudaMemcpyAsync and a kernel on two non-blocking
// streams touching one device buffer, with nothing ordering the two operations.
//   default         H2D copy on stream a, then a kernel on stream b READS the buffer
//   -DKERNEL_FIRST  a kernel on stream a WRITES the buffer, then a D2H copy on stream b reads it
//   -DFIXED         stream b waits on an event recorded on stream a after the first operation
// 256 ints, so a YOSEMITE_HB_TRACE dump stays tiny. Expected: racy -> RACE, fixed -> CLEAN.
#include <cstdio>
#include <cuda_runtime.h>

__global__ void touch(int* buf, int* out, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
#ifdef KERNEL_FIRST
  buf[i] = 2 * i;          // the D2H copy on stream b reads buf
#else
  out[i] = buf[i] + 1;     // the H2D copy on stream a writes buf
#endif
}

int main() {
  const int n = 256;
  int *h, *d_buf, *d_out;
  cudaMallocHost(&h, n * sizeof(int));
  for (int i = 0; i < n; ++i) h[i] = i;
  cudaMalloc(&d_buf, n * sizeof(int));
  cudaMalloc(&d_out, n * sizeof(int));
  cudaMemset(d_buf, 0, n * sizeof(int));
  cudaDeviceSynchronize();
  cudaStream_t a, b;
  cudaStreamCreateWithFlags(&a, cudaStreamNonBlocking);
  cudaStreamCreateWithFlags(&b, cudaStreamNonBlocking);
  cudaEvent_t done;
  cudaEventCreateWithFlags(&done, cudaEventDisableTiming);
#ifdef KERNEL_FIRST
  touch<<<(n + 127) / 128, 128, 0, a>>>(d_buf, d_out, n);
#else
  cudaMemcpyAsync(d_buf, h, n * sizeof(int), cudaMemcpyHostToDevice, a);
#endif
#ifdef FIXED
  cudaEventRecord(done, a);
  cudaStreamWaitEvent(b, done, 0);
#endif
#ifdef KERNEL_FIRST
  cudaMemcpyAsync(h, d_buf, n * sizeof(int), cudaMemcpyDeviceToHost, b);
#else
  touch<<<(n + 127) / 128, 128, 0, b>>>(d_buf, d_out, n);
#endif
  cudaError_t err = cudaDeviceSynchronize();
  printf("host_memcpy_race: %s\n", cudaGetErrorString(err));
  return err != cudaSuccess;
}

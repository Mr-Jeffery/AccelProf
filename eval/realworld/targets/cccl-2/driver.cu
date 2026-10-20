// cccl-2 driver (T21a): DeviceRunLengthEncode::NonTrivialRuns on one tile.  Our own code; headers are the checkout's (R1h).
// Policy for sm_89 at this commit: 96 threads x 15 items = 1,440 items per tile, so n = 1440 is exactly one tile
// (tile_idx == 0, the path without a barrier between WarpScanAllocations and the scatter).  Every key pair is a run of
// length 2 (key = i / 2), so warp 0's 480 items start 240 non-trivial runs (the record needs >= 97 in warp 0's range).
#include <cub/device/device_run_length_encode.cuh>
#include <cstdio>
#include <cstdlib>
#include <vector>

int main(int argc, char** argv)
{
  const int n = argc > 1 ? atoi(argv[1]) : 1440;
  std::vector<int> h(n);
  for (int i = 0; i < n; ++i) { h[i] = i / 2; }
  int *d_in, *d_off, *d_len, *d_num;
  cudaMalloc(&d_in, n * sizeof(int));
  cudaMalloc(&d_off, n * sizeof(int));
  cudaMalloc(&d_len, n * sizeof(int));
  cudaMalloc(&d_num, sizeof(int));
  cudaMemcpy(d_in, h.data(), n * sizeof(int), cudaMemcpyHostToDevice);
  void* d_temp   = nullptr;
  size_t t_bytes = 0;
  cub::DeviceRunLengthEncode::NonTrivialRuns(d_temp, t_bytes, d_in, d_off, d_len, d_num, n);
  cudaMalloc(&d_temp, t_bytes);
  cudaError_t e1 = cub::DeviceRunLengthEncode::NonTrivialRuns(d_temp, t_bytes, d_in, d_off, d_len, d_num, n);
  cudaError_t e2 = cudaDeviceSynchronize();
  int num = -1;
  cudaMemcpy(&num, d_num, sizeof(int), cudaMemcpyDeviceToHost);
  std::vector<int> off(n), len(n);
  cudaMemcpy(off.data(), d_off, n * sizeof(int), cudaMemcpyDeviceToHost);
  cudaMemcpy(len.data(), d_len, n * sizeof(int), cudaMemcpyDeviceToHost);
  int bad = 0;
  for (int r = 0; r < n / 2 && r < num; ++r) { bad += (off[r] != 2 * r) || (len[r] != 2); }
  printf("cccl-2 NonTrivialRuns n=%d (one tile) call=%s run=%s num_runs=%d expect=%d mismatches=%d\n", n,
         cudaGetErrorString(e1), cudaGetErrorString(e2), num, n / 2, bad);
  return (e1 == cudaSuccess && e2 == cudaSuccess) ? 0 : 1;
}

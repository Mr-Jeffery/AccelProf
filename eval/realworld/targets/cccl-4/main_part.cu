
// ---- end of the verbatim excerpt; everything below is the T21a driver (host main in the shape of the test's body) ----
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

int main(int argc, char** argv)
{
  using message_t         = std::uint32_t;
  using scan_tile_state_t = cub::ScanTileState<message_t>;
  const int num_tiles     = argc > 1 ? atoi(argv[1]) : 64; // 64 tiles x 256 threads

  std::vector<message_t> h(num_tiles);
  for (int i = 0; i < num_tiles; ++i) { h[i] = (message_t) (i % 7 + 1); }
  message_t* d_tile_data = nullptr;
  cudaMalloc(&d_tile_data, num_tiles * sizeof(message_t));
  cudaMemcpy(d_tile_data, h.data(), num_tiles * sizeof(message_t), cudaMemcpyHostToDevice);

  std::size_t temp_storage_bytes{};
  scan_tile_state_t::AllocationSize(num_tiles, temp_storage_bytes);
  void* d_temp_storage = nullptr;
  cudaMalloc(&d_temp_storage, temp_storage_bytes);
  scan_tile_state_t tile_status;
  cudaError_t status = tile_status.Init(num_tiles, d_temp_storage, temp_storage_bytes);
  if (status != cudaSuccess) { printf("Init failed: %s\n", cudaGetErrorString(status)); return 2; }

  constexpr unsigned int threads_in_init_block = 256;
  const unsigned int blocks_in_init_grid       = (num_tiles + threads_in_init_block - 1) / threads_in_init_block;
  init_kernel<<<blocks_in_init_grid, threads_in_init_block>>>(tile_status, num_tiles);
  cudaError_t e1 = cudaDeviceSynchronize();

  constexpr unsigned int threads_in_block = 256;
  decoupled_look_back_kernel<<<num_tiles, threads_in_block>>>(tile_status, d_tile_data);
  cudaError_t e2 = cudaDeviceSynchronize();

  std::vector<message_t> out(num_tiles);
  cudaMemcpy(out.data(), d_tile_data, num_tiles * sizeof(message_t), cudaMemcpyDeviceToHost);
  message_t ref = 0;
  int bad       = 0;
  for (int i = 0; i < num_tiles; ++i) { ref += h[i]; bad += (out[i] != ref); }
  printf("cccl-4 decoupled_look_back_kernel<<<%d,256>>> init=%s run=%s mismatches=%d last=%u\n", num_tiles,
         cudaGetErrorString(e1), cudaGetErrorString(e2), bad, (unsigned) out[num_tiles - 1]);
  return (e1 == cudaSuccess && e2 == cudaSuccess && bad == 0) ? 0 : 1;
}

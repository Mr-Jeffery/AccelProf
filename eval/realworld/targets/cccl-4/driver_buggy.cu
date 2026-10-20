/******************************************************************************
 * Copyright (c) 2011-2023, NVIDIA CORPORATION.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of the NVIDIA CORPORATION nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL NVIDIA CORPORATION BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 ******************************************************************************/

// T21a driver for cccl-4 (buggy): the two kernels below (lines 38-97 of cub/test/catch2_test_device_decoupled_look_back.cu at 45f868f38fdf7a5e9746aa4074bf7da0c730a330) are verbatim.
#undef NDEBUG
#include <cub/device/device_scan.cuh>

#include <cassert>

template <class ScanTileStateT>
__global__ void init_kernel(ScanTileStateT tile_state, int blocks_in_grid)
{
  tile_state.InitializeStatus(blocks_in_grid);
}

template <class MessageT>
__global__ void decoupled_look_back_kernel(cub::ScanTileState<MessageT> tile_state, MessageT* tile_data)
{
  using scan_op_t         = ::cuda::std::plus<>;
  using scan_tile_state_t = cub::ScanTileState<MessageT>;
  using tile_prefix_op    = cub::TilePrefixCallbackOp<MessageT, scan_op_t, scan_tile_state_t>;
  using temp_storage_t    = typename tile_prefix_op::TempStorage;

  // Allocate temp storage in shared memory
  __shared__ temp_storage_t temp_storage;

  scan_op_t scan_op{};
  constexpr unsigned int threads_in_warp = 32;
  const unsigned int tid                 = threadIdx.x;

  // Construct prefix op
  tile_prefix_op prefix(tile_state, temp_storage, scan_op);
  const unsigned int tile_idx = prefix.GetTileIdx();

  // "Compute" tile aggregate
  MessageT tile_aggregate = tile_data[tile_idx];

  if (tile_idx == 0)
  {
    // There are no blocks to look back to, immediately set the inclusive state
    if (tid == 0)
    {
      tile_state.SetInclusive(tile_idx, tile_aggregate);
      tile_data[tile_idx] = tile_aggregate;
    }
  }
  else
  {
    // Only the first warp in the block can perform the look back
    const unsigned int warp_id = tid / threads_in_warp;

    if (warp_id == 0)
    {
      // Perform the decoupled look-back
      // Invocation of the prefix will block until the look-back is complete.
      MessageT exclusive_prefix = prefix(tile_aggregate);

      if (tid == 0)
      {
        MessageT inclusive_prefix = scan_op(exclusive_prefix, tile_aggregate);
        tile_data[tile_idx]       = inclusive_prefix;
      }
    }
    __syncthreads();

    assert(tile_data[tile_idx] == prefix.GetInclusivePrefix());
    assert(tile_aggregate == prefix.GetBlockAggregate());
  }
}

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

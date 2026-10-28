// cuRace R2 shim for src/backend/cuda/debug_cuda.hpp: CUDA_LAUNCH / CUDA_LAUNCH_SMEM / POST_LAUNCH_CHECK as in a35a2d08
// (the NDEBUG = Release branch of POST_LAUNCH_CHECK), with the per-device ArrayFire stream replaced by the default stream.
#pragma once
#include <err_cuda.hpp>

namespace cuda
{
    static inline cudaStream_t getStream(int) { return 0; }
    static inline int getActiveDeviceId() { return 0; }
    static inline bool synchronize_calls() { return false; }
}

#define CUDA_LAUNCH_SMEM(fn, blks, thrds, smem_size, ...) \
	fn<<<blks, thrds, smem_size, cuda::getStream(cuda::getActiveDeviceId())>>>(__VA_ARGS__)

#define CUDA_LAUNCH(fn, blks, thrds, ...) \
	CUDA_LAUNCH_SMEM(fn, blks, thrds, 0, __VA_ARGS__)

#define POST_LAUNCH_CHECK() do {                                        \
    if(cuda::synchronize_calls()) {                                     \
        CUDA_CHECK(cudaStreamSynchronize(cuda::getStream(cuda::getActiveDeviceId()))); \
    } else {                                                            \
        CUDA_CHECK(cudaPeekAtLastError());                              \
    }                                                                   \
  } while(0)

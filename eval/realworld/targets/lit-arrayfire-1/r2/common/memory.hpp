// cuRace R2 shim for src/backend/cuda/memory.hpp: memAlloc / memFree on top of cudaMalloc / cudaFree (ArrayFire's caching
// allocator is not part of the kernel files).
#pragma once
#include <cstdlib>
#include <err_cuda.hpp>

namespace cuda
{
    template<typename T> inline T* memAlloc(const size_t &elements)
    {
        void *p = NULL;
        CUDA_CHECK(cudaMalloc(&p, elements * sizeof(T)));
        return (T*)p;
    }

    template<typename T> inline void memFree(T* ptr)
    {
        CUDA_CHECK(cudaFree((void*)ptr));
    }
}

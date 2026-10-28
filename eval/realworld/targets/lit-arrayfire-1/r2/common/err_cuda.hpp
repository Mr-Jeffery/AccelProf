// cuRace R2 shim for src/backend/cuda/err_cuda.hpp: CUDA_CHECK without the ArrayFire exception machinery (prints and aborts).
#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <backend.hpp>

#define CUDA_CHECK(fn) do {                                         \
        cudaError_t _cuda_error = fn;                               \
        if (_cuda_error != cudaSuccess) {                           \
            fprintf(stderr, "CUDA Error (%d): %s at %s:%d\n",       \
                    (int)(_cuda_error),                             \
                    cudaGetErrorString(_cuda_error),                \
                    __FILE__, __LINE__);                            \
            exit(1);                                                \
        }                                                           \
    } while(0)

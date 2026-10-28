// cuRace R2 shim for src/backend/cuda/kernel/config.hpp (blob c879e4fe, identical in a35a2d08 and a7a297ba): same constants.
#pragma once
#include <backend.hpp>

namespace cuda
{
namespace kernel
{

    static const uint THREADS_PER_BLOCK = 256;
    static const uint THREADS_X = 32;
    static const uint THREADS_Y = THREADS_PER_BLOCK / THREADS_X;
    static const uint REPEAT    = 32;
}
}

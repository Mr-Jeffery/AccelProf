// cuRace R2 shim for src/backend/cuda/math.hpp: only what Binary/Transform of the add operator use.
#pragma once
#include <backend.hpp>

namespace cuda
{
    template<typename T> static inline __DH__ T scalar(double val) { return (T)(val); }
}

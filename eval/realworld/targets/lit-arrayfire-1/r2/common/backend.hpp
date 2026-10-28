// cuRace R2 shim for src/backend/cuda/backend.hpp (+ the pieces of types.hpp, af/defines.h, defines.hpp it pulls in).
// The ArrayFire tree at a35a2d08 / a7a297ba cannot be built as a library with CUDA 13; the two kernel files are compiled
// verbatim and these shims provide only the names they use.  Same shim for the buggy and the fixed variant.
#pragma once
#ifdef __DH__
#undef __DH__
#endif

#include <cuda_runtime.h>
#define __DH__ __device__ __host__

#include <cuComplex.h>
#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <cstdlib>

// af/defines.h at a35a2d08 (LP64 branch)
typedef long long dim_t;

namespace cuda
{
    // types.hpp
    typedef cuFloatComplex   cfloat;
    typedef cuDoubleComplex cdouble;
    typedef unsigned int   uint;
    typedef unsigned char  uchar;
    typedef unsigned short ushort;
    // defines.hpp
    typedef long long          intl;
    typedef unsigned long long uintl;
}

namespace detail = cuda;

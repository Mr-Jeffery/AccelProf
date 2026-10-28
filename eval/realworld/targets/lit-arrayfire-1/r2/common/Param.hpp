// cuRace R2 shim for src/backend/cuda/Param.hpp (identical in a35a2d08 and a7a297ba; re-typed here, same layout and members).
#pragma once
#include <backend.hpp>

namespace cuda
{

template<typename T>
struct Param
{
    T *ptr;
    dim_t dims[4];
    dim_t strides[4];
};

template<typename T>
class CParam
{
public:
    const T *ptr;
    dim_t dims[4];
    dim_t strides[4];

    __DH__ CParam(const T *iptr, const dim_t *idims, const dim_t *istrides) :
        ptr(iptr)
    {
        for (int i = 0; i < 4; i++) {
            dims[i] = idims[i];
            strides[i] = istrides[i];
        }
    }

    __DH__ CParam(Param<T> &in) : ptr(in.ptr)
    {
        for (int i = 0; i < 4; i++) {
            dims[i] = in.dims[i];
            strides[i] = in.strides[i];
        }
    }

    __DH__ ~CParam() {}
};

}

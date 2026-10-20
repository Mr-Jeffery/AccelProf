// cuRace R2 shim for modules/gpu/include/opencv2/gpu/device/common.hpp (ce42593f and 7fd21d21 have the same file).
// The original cannot be compiled with CUDA 13 (textureReference / cudaBindTexture2D were removed in CUDA 12), so this shim keeps what the
// verbatim canny.cu needs: cudaSafeCall, divUp, the device typedefs, and stand-ins for the removed texture reference API
// (texture<>, tex2D, bindTexture, cudaThreadSynchronize).  The texture stand-ins are only used by calcMagnitudeKernel / calcMapKernel,
// which the driver never launches; the kernel under test (edgesHysteresisLocalKernel) does not use textures.
// PtrStep / PtrStepSz come from the VERBATIM modules/core/include/opencv2/core/cuda_devptrs.hpp (r2_extract.sh).
#ifndef __OPENCV_GPU_COMMON_HPP__
#define __OPENCV_GPU_COMMON_HPP__

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>
#include "opencv2/core/cuda_devptrs.hpp"

#define cudaSafeCall(expr)  ___cudaSafeCall(expr, __FILE__, __LINE__, __func__)

// removed from the CUDA runtime in CUDA 12
#define cudaThreadSynchronize cudaDeviceSynchronize

namespace cv { namespace gpu
{
    inline void error(const char *error_string, const char *file, const int line, const char *func)
    {
        fprintf(stderr, "OpenCV GPU error: %s (%s:%d, %s)\n", error_string, file, line, func);
        exit(1);
    }
}}

static inline void ___cudaSafeCall(cudaError_t err, const char *file, const int line, const char *func = "")
{
    if (cudaSuccess != err)
        cv::gpu::error(cudaGetErrorString(err), file, line, func);
}

namespace cv { namespace gpu
{
    __host__ __device__ __forceinline__ int divUp(int total, int grain)
    {
        return (total + grain - 1) / grain;
    }

    namespace device
    {
        using cv::gpu::divUp;

        typedef unsigned char uchar;
        typedef unsigned short ushort;
        typedef signed char schar;

        // stand-in for the CUDA texture reference API (removed in CUDA 12); never executed by the driver
        template <class T, int dim = 1, enum cudaTextureReadMode mode = cudaReadModeElementType> struct texture
        {
            typedef T elem_type;
            texture(int = 0, enum cudaTextureFilterMode = cudaFilterModePoint, enum cudaTextureAddressMode = cudaAddressModeClamp) {}
        };

        template <class Tex> __device__ __forceinline__ typename Tex::elem_type tex2D_standin(float, float)
        {
            return typename Tex::elem_type();
        }

        template<class T> inline void bindTexture(const void*, const PtrStepSz<T>&) {}
    }
}}

// tex2D(tex, x, y): the texture object itself must not be referenced in device code, only its type
#define tex2D(tex, x, y) cv::gpu::device::tex2D_standin<decltype(tex)>((float)(x), (float)(y))

#endif // __OPENCV_GPU_COMMON_HPP__

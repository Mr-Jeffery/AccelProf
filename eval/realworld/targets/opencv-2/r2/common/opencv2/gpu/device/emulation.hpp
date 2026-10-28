// cuRace R2 shim for modules/gpu/include/opencv2/gpu/device/emulation.hpp: only Emulation::smem::atomicAdd (the sm >= 1.2 path of
// the original, i.e. ::atomicAdd), used by edgesHysteresisGlobalKernel which the driver does not launch.
#ifndef __OPENCV_GPU_EMULATION_HPP_
#define __OPENCV_GPU_EMULATION_HPP_

#include "opencv2/gpu/device/common.hpp"

namespace cv { namespace gpu { namespace device
{
    struct Emulation
    {
        struct smem
        {
            template<typename T>
            static __device__ __forceinline__ T atomicAdd(T* address, T val)
            {
                return ::atomicAdd(address, val);
            }
        };
    };
}}}

#endif /* __OPENCV_GPU_EMULATION_HPP_ */

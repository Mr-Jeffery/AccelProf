// cuRace R2 shim for modules/gpu/include/opencv2/gpu/device/functional.hpp: only unary_function / binary_function (same definitions as
// the original), used as base classes of canny::L1, L2 and GetEdges.
#ifndef __OPENCV_GPU_FUNCTIONAL_HPP__
#define __OPENCV_GPU_FUNCTIONAL_HPP__

#include "opencv2/gpu/device/common.hpp"

namespace cv { namespace gpu { namespace device
{
    template <typename T, typename D> struct unary_function
    {
        typedef T argument_type;
        typedef D result_type;
    };

    template <typename T1, typename T2, typename D> struct binary_function
    {
        typedef T1 first_argument_type;
        typedef T2 second_argument_type;
        typedef D result_type;
    };
}}}

#endif // __OPENCV_GPU_FUNCTIONAL_HPP__

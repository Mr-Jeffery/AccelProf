// cuRace R2 shim for modules/gpu/include/opencv2/gpu/device/transform.hpp: the names canny.cu uses (WithOutMask, TransformFunctorTraits,
// DefaultTransformFunctorTraits, transform(...)).  The transform() stand-ins do nothing: they are only called by canny::calcMagnitude(dx,dy,mag)
// and canny::getEdges, which the driver never calls; the kernel under test does not use them.
#ifndef __OPENCV_GPU_TRANSFORM_HPP__
#define __OPENCV_GPU_TRANSFORM_HPP__

#include "opencv2/gpu/device/common.hpp"

namespace cv { namespace gpu { namespace device
{
    struct WithOutMask {};

    template <typename T> struct DefaultTransformFunctorTraits
    {
        enum { simple_block_dim_x = 16, simple_block_dim_y = 16 };
        enum { smart_block_dim_x = 16, smart_block_dim_y = 16 };
        enum { smart_shift = 1 };
    };

    template <typename T> struct TransformFunctorTraits : DefaultTransformFunctorTraits<T> {};

    template <class SrcPtr, class DstPtr, class UnOp, class Mask>
    void transform(const SrcPtr&, const DstPtr&, const UnOp&, const Mask&, cudaStream_t) {}

    template <class Src1Ptr, class Src2Ptr, class DstPtr, class BinOp, class Mask>
    void transform(const Src1Ptr&, const Src2Ptr&, const DstPtr&, const BinOp&, const Mask&, cudaStream_t) {}
}}}

#endif // __OPENCV_GPU_TRANSFORM_HPP__

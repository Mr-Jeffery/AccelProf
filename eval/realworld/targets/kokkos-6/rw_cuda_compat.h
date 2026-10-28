// rw_cuda_compat.h -- T21a toolkit-compatibility pre-include (nvcc -include), NOT part of Kokkos and not a kernel change.
// Kokkos 3.6/3.7 (2022) core/src/Cuda/Kokkos_Cuda_Half_Conversion.hpp does not compile with CUDA >= 12.2:
//   (a) __half2double is not declared by cuda_fp16.h any more   -> "identifier __half2double is undefined"
//   (b) __half2float(half_t) etc. rely on an implicit half_t -> __half conversion that half_t does not have (its operator
//       __half is explicit)                                      -> "no suitable user-defined conversion from half_t to __half"
// The half conversion header is unrelated to the reductions under test.  This header only declares the missing functions
// as forwarding overloads, so that header compiles unchanged.  It is pre-included into every Kokkos translation unit of
// BOTH variants with identical flags.
#pragma once
#include <cuda_fp16.h>
#include <type_traits>
#include <utility>

__host__ __device__ inline double __half2double(const __half h) { return static_cast<double>(__half2float(h)); }

#define RW_HALF_FWD(NAME, RET)                                                                                 \
  template <class W, class = std::enable_if_t<std::is_class<W>::value && !std::is_same<W, __half>::value,      \
                                              decltype(static_cast<__half>(std::declval<const W&>()))>>        \
  __host__ __device__ inline RET NAME(const W& w) {                                                            \
    return NAME(static_cast<__half>(w));                                                                       \
  }
RW_HALF_FWD(__half2float, float)
RW_HALF_FWD(__half2double, double)
RW_HALF_FWD(__half2short_rz, short)
RW_HALF_FWD(__half2ushort_rz, unsigned short)
RW_HALF_FWD(__half2int_rz, int)
RW_HALF_FWD(__half2uint_rz, unsigned int)
RW_HALF_FWD(__half2ll_rz, long long)
RW_HALF_FWD(__half2ull_rz, unsigned long long)
#undef RW_HALF_FWD

// (c) CUDA 13 changed cudaMemPrefetchAsync/cudaMemAdvise to take a cudaMemLocation instead of an int device
//     (Kokkos_CudaSpace.cpp: cudaMemPrefetchAsync(ptr, bytes, device, stream), cudaMemAdvise(ptr, size, advice, device)).
//     Forward the old int-device overloads to the new API (cudaCpuDeviceId -> host location); managed-memory hints only.
#include <cuda_runtime_api.h>
#if defined(CUDART_VERSION) && CUDART_VERSION >= 13000
static inline cudaMemLocation rw_mem_location(int dev) {
  cudaMemLocation loc;
  loc.type = (dev == cudaCpuDeviceId) ? cudaMemLocationTypeHost : cudaMemLocationTypeDevice;
  loc.id   = dev;
  return loc;
}
static inline cudaError_t cudaMemPrefetchAsync(const void* p, size_t n, int dev, cudaStream_t s = 0) {
  return cudaMemPrefetchAsync(p, n, rw_mem_location(dev), 0u, s);
}
static inline cudaError_t cudaMemAdvise(const void* p, size_t n, enum cudaMemoryAdvise advice, int dev) {
  return cudaMemAdvise(p, n, advice, rw_mem_location(dev));
}
#endif

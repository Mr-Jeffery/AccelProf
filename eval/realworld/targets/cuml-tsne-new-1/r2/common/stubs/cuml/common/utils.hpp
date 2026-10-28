// R2 stub (T21c): the only thing the BH kernels take from the real cuml/common/utils.hpp is this macro, copied from the pinned commit
// (cpp/include/cuml/common/utils.hpp at c7e7738bb6: "#define CUML_KERNEL __global__ static" under __CUDACC__).
#pragma once
#include <raft/core/error.hpp>
#include <raft/util/cudart_utils.hpp>
#ifdef __CUDACC__
#define CUML_KERNEL __global__ static
#else
#define CUML_KERNEL static
#endif

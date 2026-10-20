// rw_cuda13_compat.h -- T21a toolkit-compatibility pre-include (g++ -include), NOT part of Ginkgo and not a kernel change.
// cuda/base/exception.cpp of the Jan-2025 Ginkgo names three cuFFT status enumerators that cuFFT 12 (CUDA 13) removed:
//   CUFFT_INCOMPLETE_PARAMETER_LIST, CUFFT_PARSE_ERROR, CUFFT_LICENSE_ERROR  ("was not declared in this scope").
// They are only used to print an error name; this header supplies their historical values (cuFFT 11/12) so that file compiles
// unchanged.  Pre-included into every compiled C++ translation unit of BOTH variants, with identical flags.
#pragma once
#if defined(__has_include)
#if __has_include(<cufft.h>)
#include <cufft.h>
#ifndef CUFFT_INCOMPLETE_PARAMETER_LIST
#define CUFFT_INCOMPLETE_PARAMETER_LIST 0xA
#define CUFFT_PARSE_ERROR 0xC
#define CUFFT_LICENSE_ERROR 0x0F
#endif
#endif
#endif

// T21c include shim (not an upstream file) standing in for colmap/util/endian.h, which pulls in colmap/util/types.h (Eigen, Boost).
// gpu_mat.h only names ReadBinaryLittleEndian / WriteBinaryLittleEndian inside GpuMat::Read / ::Write, which this harness never calls;
// the declarations are never defined.
#pragma once

#include <iostream>
#include <vector>

namespace colmap {
template <typename T, typename Stream, typename Vec>
void ReadBinaryLittleEndian(Stream* stream, Vec* data);
template <typename T, typename Stream, typename Vec>
void WriteBinaryLittleEndian(Stream* stream, const Vec& data);
}  // namespace colmap

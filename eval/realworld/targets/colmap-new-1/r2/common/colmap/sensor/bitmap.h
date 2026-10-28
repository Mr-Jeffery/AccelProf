// T21c include shim (not an upstream file) standing in for colmap/sensor/bitmap.h (FreeImage-backed, Eigen).  The copied mvs headers (image.h,
// depth_map.h, normal_map.h) only name the Bitmap type, and patch_match_cuda.cu's host class calls Bitmap::RowMajorData(); none of this runs here.
#pragma once

#include <cstdint>
#include <vector>

namespace colmap {
class Bitmap {
 public:
  const std::vector<uint8_t>& RowMajorData() const { return data_; }

 private:
  std::vector<uint8_t> data_;
};
}  // namespace colmap

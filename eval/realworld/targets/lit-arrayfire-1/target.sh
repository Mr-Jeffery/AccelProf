# lit-arrayfire-1: ArrayFire CUDA scan-by-key, missing __syncthreads after the 'Identify segment boundary' block (R2).
# Fix a7a297ba (2016-06-16), parent a35a2d08.  The 2016 ArrayFire library cannot be built on CUDA 13 (CMake + boost + old CUDA APIs),
# so the two kernel files (src/backend/cuda/kernel/scan_{first,dim}_by_key_impl.hpp) are compiled VERBATIM (r2_extract.sh) and the
# headers they include (ops/backend/Param/dispatch/math/err_cuda/debug_cuda/memory/config.hpp) are stubbed in r2/common/.
# One driver (r2/common/driver.cu) runs the files' own host entry points scan_dim_by_key (32x300) and scan_first_by_key (8193).
T_ROUTE=R2; T_KERNEL=nonfinal_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build()  {
  # Project flags (ArrayFire a35a2d08, CMAKE_BUILD_TYPE Release): nvcc default -O3 device code, host -O3 -DNDEBUG.  C++17: CUDA 13 minimum.
  nvcc -std=c++17 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO -I"$SRC" -I"$SRC/common" -o driver "$SRC/common/driver.cu"
}
t_cmd()    { echo "$ART/driver"; }

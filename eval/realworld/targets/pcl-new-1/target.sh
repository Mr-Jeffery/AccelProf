# pcl-new-1: gpu/features/src/normal_3d.cu NormalsEstimator (EstimateNormalsKernel) + gpu/utils/.../warp.hpp Warp::reduce: volatile warp-synchronous reductions (T21c, R2).
# Candidate, pinned 66e1d0ea8c (no fix commit).  normal_3d.cu and warp.hpp (the record's files) plus the PCL headers they include (internal.hpp, safe_call.hpp,
# funcattrib.hpp, eigen.hpp, the gpu/containers headers, octree/device_format.hpp, algorithm.hpp, vector_math.hpp, pcl_exports.h) are copied BYTE-FOR-BYTE from the
# pinned commit (r2_extract.sh; r2/blob.check).  principal_curvatures.cu / fpfh.cu (same pattern, in the record's files list) are not built.
# Stub: r2/common/pcl/pcl_config.h (CMake-generated header).  Linking: nothing from PCL's .cpp files; -ffunction-sections/--gc-sections drops the unused host functions.
# Flags: PCL's own for CUDA (cmake/pcl_targets.cmake: --expt-relaxed-constexpr, gencode from $RW_NVCC_FLAGS), Release -O3 -DNDEBUG, -std=c++17.
T_ROUTE=R2; T_KERNEL=EstimateNormalsKernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build() {
  nvcc -std=c++17 -O3 -DNDEBUG --expt-relaxed-constexpr $RW_NVCC_FLAGS $RW_LINEINFO \
    -I"$SRC/common" -I"$SRC" -I"$SRC/common/include" -I"$SRC/gpu/features/src" -I"$SRC/gpu/features/include" \
    -I"$SRC/gpu/utils/include" -I"$SRC/gpu/containers/include" -I"$SRC/gpu/octree/include" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

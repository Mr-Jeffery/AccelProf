# colmap-new-1 (T21c candidate, unfixed, pinned 6db3867f60): patch_match_cuda.cu LocalRefImage::Read (shared row shift L364-365 / new bottom row L377-378,
# each lane writes its own 3 columns) vs PhotoConsistencyCostComputer::Compute (L502, reads the 2R neighbouring lanes' columns), no warp barrier at the
# row-loop back-edge (intra-warp, formal) in ComputeInitialCost and SweepFromTopToBottom.  R2.
# src/colmap/mvs/patch_match_cuda.cu and the project's own headers/sources it needs (mvs/{patch_match_cuda.h,cuda_texture.h,depth_map.h,gpu_mat.h,
# gpu_mat_prng.{h,cu},gpu_mat_ref_image.{h,cu},image.h,mat.h,normal_map.h,patch_match.h,patch_match_options.h,cuda_flip.h,cuda_rotate.h,cuda_transpose.h},
# util/{cuda.h,cudacc.h,cuda_to_hip.h,string.h}) byte-for-byte from the pinned commit (r2_extract.sh, blob.check).  Include shims in common/colmap/:
# util/logging.h (glog replacement), util/endian.h (types.h/Eigen replacement), sensor/bitmap.h (FreeImage/Eigen replacement); no Eigen/Boost/glog needed.
# common/driver.cu #includes the .cu files and launches the two real kernels.  Flags: the project's (CMake Release: -O3 -DNDEBUG, CMAKE_CUDA_STANDARD 17,
# --expt-relaxed-constexpr, -Wno-deprecated-gpu-targets, --compiler-options -fPIC; CMAKE_CUDA_ARCHITECTURES=89 via $RW_NVCC_FLAGS) + -lineinfo, never -G.
# NB the .cu's host dispatcher PatchMatchCuda::Run instantiates the kernels for every window radius 1..20 x step 1,2 (as the project build does), so the
# build takes long; only <7,1> is launched.
T_ROUTE=R2; T_KERNEL=ComputeInitialCost; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_build() {
  nvcc -std=c++17 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    --expt-relaxed-constexpr -Wno-deprecated-gpu-targets \
    -I"$SRC/common" -I"$SRC/src" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

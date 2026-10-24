# mmcv-fps-new-1 (T21c candidate, unfixed, pinned d2111bda57): furthest_point_sample_cuda_kernel.cuh furthest_point_sampling_forward_cuda_kernel<1024> and
# furthest_point_sampling_with_dist_forward_cuda_kernel<1024>: dists_i[tid] write (iteration j+1, thread 0) vs dists_i[0] read (iteration j, all threads). R2.
# mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh byte-for-byte from the pinned commit (r2_extract.sh, blob.check); common/driver.cu
# #includes it; common/pytorch_cuda_helper.hpp is the include shim (CUDA runtime only, no torch).  Flags: mmcv's (setup.py: nvcc -std=c++14, the
# -D__CUDA_NO_HALF_*__ set, -DMMCV_WITH_CUDA, no -O flag) with -std=c++17 instead of c++14 (CUDA 13 no longer accepts c++14) and -arch from $RW_NVCC_FLAGS.
T_ROUTE=R2; T_KERNEL=furthest_point_sampling; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_build() {
  nvcc -std=c++17 $RW_NVCC_FLAGS $RW_LINEINFO \
    -DMMCV_WITH_CUDA -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ \
    -I"$SRC/common" -I"$SRC" \
    -Xcompiler -fPIC \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

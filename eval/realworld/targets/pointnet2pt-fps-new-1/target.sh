# pointnet2pt-fps-new-1 (T21c candidate, unfixed, pinned b5ceb6d9ca): sampling_gpu.cu furthest_point_sampling_kernel<512>, dists_i[0] written at
# L112 (iteration j+1, thread 0) vs read at L170 (iteration j, every thread); no barrier after the read (cross-warp).  R2.
# pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu + .../include/cuda_utils.h byte-for-byte from the pinned commit (r2_extract.sh,
# blob.check); common/driver.cu #includes the .cu.  ATen/c10 headers (cuda_utils.h includes ATen/ATen.h and ATen/cuda/CUDAContext.h) are the INSTALLED
# PyTorch 2.14.0 headers (include shim); nothing is linked from libtorch / libpython.  Flags: the project's (setup.py: nvcc -O3; its -Xfatbin
# -compress-all (packaging only) and TORCH_CUDA_ARCH_LIST are replaced by -arch from $RW_NVCC_FLAGS=sm_89) plus what torch.utils.cpp_extension adds.
T_ROUTE=R2; T_KERNEL=furthest_point_sampling_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=_ext -D_GLIBCXX_USE_CXX11_ABI=1 \
    -I"$SRC/common" -I"$SRC" -I"$SRC/pointnet2_ops_lib/pointnet2_ops/_ext-src/include" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

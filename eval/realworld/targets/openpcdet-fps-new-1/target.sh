# openpcdet-fps-new-1 (T21c candidate, unfixed, pinned 233f849829): pointnet2_batch/src/sampling_gpu.cu farthest_point_sampling_kernel<1024> and
# pointnet2_stack/src/sampling_gpu.cu farthest_point_sampling_kernel<1024> + stack_farthest_point_sampling_kernel<1024>: dists_i[tid] write (iteration
# j+1, thread 0) vs dists_i[0] read (iteration j, all threads), cross-warp.  R2.
# Both sampling_gpu.cu plus their own cuda_utils.h and sampling_gpu.h byte-for-byte from the pinned commit (r2_extract.sh, blob.check); common/driver.cu
# #includes each inside its own namespace (see its header comment) and calls the upstream launchers.  torch/serialize/tensor.h and
# ATen/cuda/CUDAContext.h are the INSTALLED PyTorch 2.14.0 headers (include shim), nothing is linked from libtorch / libpython.  Flags: the project's
# (setup.py make_cuda_ext: CUDAExtension with no extra nvcc args = torch.utils.cpp_extension defaults) with -arch from $RW_NVCC_FLAGS (sm_89).
T_ROUTE=R2; T_KERNEL=farthest_point_sampling_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=pointnet2_batch_cuda -D_GLIBCXX_USE_CXX11_ABI=1 \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

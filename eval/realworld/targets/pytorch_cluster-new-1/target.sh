# pytorch_cluster-new-1 (T21c candidate, unfixed, pinned e9a855c284): fps_cuda.cu fps_kernel, in-place stride-doubling shared-memory
# argmax reduction (best_dist / best_dist_idx), cross-warp strides i = 32, 64, 128.  R2, same approach as pytorch_cluster-1.
# csrc/cuda/{fps_cuda.cu,fps_cuda.h,utils.cuh} + csrc/{extensions.h,macros.h} byte-for-byte from the pinned commit (r2_extract.sh, blob.check);
# common/driver.cu #includes the .cu.  torch/torch.h etc. are the INSTALLED PyTorch 2.14.0 headers (include shim), nothing is linked from libtorch /
# libpython.  Flags: the project's (setup.py at the commit: -DWITH_CUDA, nvcc -O2 -DTORCH_INDUCTOR_CPP_WRAPPER --expt-relaxed-constexpr, arch from
# $RW_NVCC_FLAGS) plus what torch.utils.cpp_extension adds for a CUDAExtension (-std=c++20 required by torch 2.14, -D__CUDA_NO_HALF_*__, ...).
T_ROUTE=R2; T_KERNEL=fps_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -O2 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -DWITH_CUDA -DTORCH_INDUCTOR_CPP_WRAPPER --expt-relaxed-constexpr \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=torch_cluster_fps -D_GLIBCXX_USE_CXX11_ABI=1 -DCUB_WRAPPED_NAMESPACE=at_cuda_detail \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

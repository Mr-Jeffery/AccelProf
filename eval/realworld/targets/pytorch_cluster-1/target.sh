# pytorch_cluster-1: nearest_cuda.cu nearest_kernel, in-place stride-doubling shared-memory reduction (WAR). R2.
# Fix a5abfee856 (2020-12-07), parent 817b767e55.  csrc/cuda/{nearest_cuda.cu,nearest_cuda.h,utils.cuh} byte-for-byte from both commits
# (r2_extract.sh); common/driver.cu #includes the .cu.  torch/extension.h etc. are the INSTALLED PyTorch 2.14.0 headers (include shim), nothing
# is linked from libtorch / libpython.  Flags: the project's own (setup.py/CMakeLists: -DWITH_CUDA --expt-relaxed-constexpr, arch from $RW_NVCC_FLAGS)
# plus what torch.utils.cpp_extension adds for a CUDAExtension.
T_ROUTE=R2; T_KERNEL=nearest_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -DWITH_CUDA --expt-relaxed-constexpr \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=torch_cluster_nearest -D_GLIBCXX_USE_CXX11_ABI=1 -DCUB_WRAPPED_NAMESPACE=at_cuda_detail \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

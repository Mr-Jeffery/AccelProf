# lit-exllamav3-1: routing.cu top-K routing kernels, shared-memory WAR between stage reads and the next write slice. R2.
# Fix 3daf2d5dff (2026-09-03), parent 0c4804c4e3.  exllamav3/exllamav3_ext/{routing.cu,routing.cuh,util.h,util.cuh,reduction.cuh,hgemm.cuh,graph.cuh}
# byte-for-byte from both commits (r2_extract.sh); common/driver.cu #includes routing.cu.  ATen/c10/pybind11 headers come from the INSTALLED
# PyTorch 2.14.0 include dir (shim), nothing is linked from libtorch/libpython.  Flags: the project's own (setup.py extra_cuda_cflags:
# -lineinfo -O3 --use_fast_math -Xcudafe --diag_suppress=177/20012) plus what torch.utils.cpp_extension adds for a CUDAExtension.
T_ROUTE=R2; T_KERNEL=routing_ds3_nogroup_topk_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -O3 --use_fast_math -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -Xcudafe --diag_suppress=177 -Xcudafe --diag_suppress=20012 \
    --expt-relaxed-constexpr \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=exllamav3_ext -D_GLIBCXX_USE_CXX11_ABI=1 -DCUB_WRAPPED_NAMESPACE=at_cuda_detail \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

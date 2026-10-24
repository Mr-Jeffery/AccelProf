# sglang-open-1: python/sglang/kernels/aot/csrc/moe/moe_align_kernel.cu moe_align_block_size_kernel, prefix[tid] write vs prefix[mid] binary search, no barrier (T21c, R2).
# Open candidate, pinned 08550acc28 (no fix commit).  The AOT copy's file and python/sglang/kernels/aot/include/utils.h (WARP_SIZE, next_pow2, DISPATCH_INTEGRAL_TYPES)
# are copied BYTE-FOR-BYTE (r2_extract.sh; r2/blob.check); the CUDA (non-HIP) path is built.  The JIT copy (kernels/jit/csrc/moe/moe_align_kernel.cu, same race) needs
# tvm-ffi/dlpack headers and a JIT toolchain and is NOT built (optional per the brief).
# Shim: r2/common/THC/THCAtomics.cuh (empty; header removed from modern PyTorch).  torch/ATen/c10 headers = the INSTALLED PyTorch 2.14.0 headers + conda Python 3.14
# headers (as pytorch_cluster-1); nothing is linked from libtorch: the never-called torch::Tensor host dispatcher still references libtorch/c10 symbols
# (ld keeps it under --gc-sections), so the link uses --unresolved-symbols=ignore-all (they resolve to 0 and are never executed).
# Flags: the project's own (python/sglang/kernels/aot/CMakeLists.txt SGL_KERNEL_CUDA_FLAGS): -DNDEBUG -O3 -std=c++20 -DFLASHINFER_ENABLE_F16/_BF16/_FP8(_E4M3,_E5M2)
# --expt-relaxed-constexpr --expt-extended-lambda -DOPERATOR_NAMESPACE=sgl-kernel; arch from $RW_NVCC_FLAGS (the project's gencode list holds sm_89 as well).
T_ROUTE=R2; T_KERNEL=moe_align_block_size_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_export() { :; }
t_build() {
  nvcc -std=c++20 -O3 -DNDEBUG -DOPERATOR_NAMESPACE=sgl-kernel -DFLASHINFER_ENABLE_F16 -DFLASHINFER_ENABLE_BF16 \
    -DFLASHINFER_ENABLE_FP8 -DFLASHINFER_ENABLE_FP8_E4M3 -DFLASHINFER_ENABLE_FP8_E5M2 \
    --expt-relaxed-constexpr --expt-extended-lambda $RW_NVCC_FLAGS $RW_LINEINFO \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -D_GLIBCXX_USE_CXX11_ABI=1 \
    -I"$SRC/common" -I"$SRC" -I"$SRC/python/sglang/kernels/aot/include" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections -Xlinker --unresolved-symbols=ignore-all \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

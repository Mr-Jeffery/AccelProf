# pytorch-3: MultiMarginLoss.cu MultiMarginLoss_backward_kernel, missing barrier before the final scaling loop (global-memory WAW/RAW). R2.
# Fix 8573a2beda (2025-07-24), parent 13398dab79.  Kernel file byte-for-byte from both commits (r2_extract.sh); common/driver.cu #includes it.
# The ATen/c10 headers the file needs are the installed PyTorch 2.14.0 headers (include shim); nothing is linked from libtorch.
T_ROUTE=R2; T_KERNEL=MultiMarginLoss_backward_kernel; T_SPACE=global; T_RACECHECK=na; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
t_build() {
  # flags follow PyTorch's own CUDA flags (Release): -O3 -DNDEBUG, relaxed constexpr, extended lambda, no implicit half operators
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    --expt-relaxed-constexpr --expt-extended-lambda \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -D_GLIBCXX_USE_CXX11_ABI=1 -DCUB_WRAPPED_NAMESPACE=at_cuda_detail \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" \
    -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

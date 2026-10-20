# pytorch-4: Sorting.cu gatherKthValue, unsynchronised global WAW of kthValue[0]/indices[0] by every matching thread. R2.
# Fix 79a4a9c02e (2025-10-25), parent 9d0b77f4cd.  Kernel file byte-for-byte from both commits (r2_extract.sh); common/driver.cu #includes it.
# The ATen/c10 headers the file needs are the installed PyTorch 2.14.0 headers (include shim); nothing is linked from libtorch. SortingRadixSelect.cuh, SortingCommon.cuh and TensorInfo.cuh are copied from the revision (r2/{buggy,fixed}/..., put first on the include path via -I$SRC/aten/src): the installed 2.14 radixSelect is a different implementation.
T_ROUTE=R2; T_KERNEL=gatherKthValue; T_SPACE=global; T_RACECHECK=na; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
t_build() {
  # flags follow PyTorch's own CUDA flags (Release): -O3 -DNDEBUG, relaxed constexpr, extended lambda, no implicit half operators
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    --expt-relaxed-constexpr --expt-extended-lambda \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -D_GLIBCXX_USE_CXX11_ABI=1 -DCUB_WRAPPED_NAMESPACE=at_cuda_detail \
    -I"$SRC/common" -I"$SRC" -I"$SRC/aten/src" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" \
    -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

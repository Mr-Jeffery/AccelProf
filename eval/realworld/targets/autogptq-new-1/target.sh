# autogptq-new-1 (T21c candidate, unfixed, pinned 9f7d37072917): marlin_repack.cu gptq_repack_kernel, unpack-phase STS vs repack-phase LDS on
# the uint8 block[4][16][18] with no warp barrier between them (intra-warp, formal). R2.
# autogptq_extension/marlin/{marlin_repack.cu,marlin_repack.cuh} byte-for-byte from the pinned commit (r2_extract.sh, blob.check);
# common/driver.cu #includes the .cu.  ATen/c10/torch headers are the INSTALLED PyTorch 2.14.0 (include shim, as pytorch_cluster-1), nothing is
# linked from libtorch/libpython.  Flags: the project's (setup.py: CUDAExtension with no extra nvcc args, so torch.utils.cpp_extension defaults)
# with -arch from $RW_NVCC_FLAGS (sm_89) + -lineinfo, never -G.
T_ROUTE=R2; T_KERNEL=gptq_repack_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
t_build() {
  nvcc -std=c++20 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=autogptq_marlin_cuda -D_GLIBCXX_USE_CXX11_ABI=1 \
    -I"$SRC/common" -I"$SRC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

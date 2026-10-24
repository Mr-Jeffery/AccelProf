# droidslam-new-1: src/droid_kernels.cu frame_distance_kernel -> blockReduce/warpReduce on a volatile float* (T21c, R2).
# Candidate, pinned 2dfd39f0dc (no fix commit).  src/droid_kernels.cu is copied BYTE-FOR-BYTE (r2_extract.sh; r2/blob.check) and #included whole by common/driver.cu.
# Includes provided by dependencies, not stubs of kernel code: torch/ATen/pybind/Python headers = the INSTALLED PyTorch 2.14.0 headers + conda Python 3.14 headers
# (as pytorch_cluster-1); Eigen = the eigen submodule that lietorch pins (DROID-SLAM thirdparty/lietorch@7f687644 -> eigen@824272cd, which setup.py puts on
# include_dirs as thirdparty/lietorch/eigen), exported to ~/incoming/realworld/deps/eigen-824272c (setup, login node):
#   git -C ~/incoming/realworld/deps/eigen.git fetch --depth 1 https://gitlab.com/libeigen/eigen.git 824272cde8ca2541e8b67b0887f5ded92b128d1f ; git archive ... Eigen unsupported | tar -x
# Nothing is linked from libtorch/libpython (-ffunction-sections --gc-sections discard the file's torch::Tensor host functions).
# Flags: setup.py nvcc extra args ['-O3'] plus what torch.utils.cpp_extension adds for a CUDAExtension (as pytorch_cluster-1), arch from $RW_NVCC_FLAGS.
T_ROUTE=R2; T_KERNEL=frame_distance_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
PT_INC=/home/fzheng4/miniconda3/envs/accel/lib/python3.14/site-packages/torch/include
PY_INC=/home/fzheng4/miniconda3/envs/accel/include/python3.14
EIGEN_INC=/home/fzheng4/incoming/realworld/deps/eigen-824272c
t_export() { :; }
t_build() {
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -D__CUDA_NO_HALF_OPERATORS__ -D__CUDA_NO_HALF_CONVERSIONS__ -D__CUDA_NO_HALF2_OPERATORS__ -D__CUDA_NO_BFLOAT16_CONVERSIONS__ \
    -DTORCH_API_INCLUDE_EXTENSION_H -DTORCH_EXTENSION_NAME=droid_backends -D_GLIBCXX_USE_CXX11_ABI=1 \
    --expt-relaxed-constexpr \
    -I"$SRC/common" -I"$SRC" -I"$EIGEN_INC" -I"$PT_INC" -I"$PT_INC/torch/csrc/api/include" -I"$PY_INC" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

# bitsandbytes-1: kEstimateQuantiles, missing __syncthreads between the smem_qidx clear loop and the quantile scatter (R2).
# Fix 5b28fd3f (2024-02-14), parent 344e8516.
# R1 (the project's own CMake build of csrc/) FAILS on CUDA 13.4 at configure, for both commits (same CMakeLists.txt blob 1b9f1854):
#   CMake Error at CMakeLists.txt:82 (message):  CUDA Version > 12 is not supported      (cmake -DCOMPUTE_BACKEND=cuda -DCOMPUTE_CAPABILITY=89)
# so the ONE alternative route R2 is used: csrc/kernels.cu (+ the unchanged csrc/kernels.cuh and csrc/ops.cuh) verbatim from both commits
# (r2_extract.sh), host main r2/common/driver.cu #includes kernels.cu; the only stub is cub::Max / cub::Sum (removed in CCCL 3), in driver.cu.
T_ROUTE=R2; T_KERNEL=kEstimateQuantiles; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build()  {
  # Project flags (CMakeLists.txt): CMAKE_CUDA_FLAGS " --use_fast_math" + "-gencode arch=compute_XX,code=sm_XX" (here $RW_NVCC_FLAGS),
  # CUDA_SEPARABLE_COMPILATION ON (-rdc=true), no CMAKE_BUILD_TYPE (no -O flag); cxx_std_14 is below nvcc 13's minimum -> -std=c++17.
  nvcc -std=c++17 --use_fast_math -rdc=true $RW_NVCC_FLAGS $RW_LINEINFO -I"$SRC" -I"$SRC/csrc" -o driver "$SRC/common/driver.cu"
}
t_cmd()    { echo "$ART/driver"; }

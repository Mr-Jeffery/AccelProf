# lit-shoc-1: SHOC level1 Scan, bottom_scan<T,vecT,256>: missing __syncthreads before the s_seed update in the window loop (R2).
# Fix 700ab826 (2014-04-13), parent 785d9ee6.
# R1 (SHOC's own autotools build: ./configure --with-cuda --without-opencl --without-mpi CUDA_CPPFLAGS="-arch=sm_89 -lineinfo";
# make -C src/common; make -C src/cuda/level1/scan Scan) FAILS on CUDA 13.4 for both commits, in the project's own host main
# (src/common/main.cpp:104:61: error: 'struct cudaDeviceProp' has no member named 'clockRate'; see r1_attempt.txt),
# so the ONE alternative route R2 is used: src/cuda/level1/scan/scan_kernel.h (the record's file) verbatim from both commits
# (r2_extract.sh), host main r2/common/driver.cu = RunTest<T,vecT> of Scan.cu for size class 1 (no stubs needed).
T_ROUTE=R2; T_KERNEL=bottom_scan; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build()  {
  # SHOC configure.ac default NVCXXFLAGS = "-g -O2" (CXX probed as g++); CUDA_CPPFLAGS (the -gencode list) replaced by $RW_NVCC_FLAGS $RW_LINEINFO;
  # nvcc 13 needs C++17 or later.
  nvcc -std=c++17 -g -O2 $RW_NVCC_FLAGS $RW_LINEINFO -I"$SRC" -o driver "$SRC/common/driver.cu"
}
t_cmd()    { echo "$ART/driver"; }

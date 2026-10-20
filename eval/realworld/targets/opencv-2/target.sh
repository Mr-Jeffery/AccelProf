# opencv-2: OpenCV 2.4 gpu module canny.cu edgesHysteresisLocalKernel, missing __syncthreads in the 16-step flood fill on volatile smem (R2).
# Fix 7fd21d21 (2014-02-20), parent ce42593f.  The 2014 tree is not built (texture references were removed in CUDA 12, cudaThreadSynchronize
# too); modules/gpu/src/cuda/canny.cu (the record's file) and modules/core/include/opencv2/core/cuda_devptrs.hpp (PtrStep/PtrStepSz,
# unchanged by the fix) are copied BYTE-FOR-BYTE from both commits (r2_extract.sh).  Stubs (r2/common/opencv2/gpu/device/): common.hpp,
# emulation.hpp, functional.hpp, transform.hpp, utility.hpp.  r2/common/driver.cu #includes canny.cu and calls canny::edgesHysteresisLocal.
T_ROUTE=R2; T_KERNEL=edgesHysteresisLocalKernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build()  {
  # OpenCV 2.4 Release: nvcc default -O3 device code, host -O3 -DNDEBUG; C++17 = CUDA 13 minimum.
  nvcc -std=c++17 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO -I"$SRC/common" -I"$SRC" -I"$SRC/modules/core/include" -o driver "$SRC/common/driver.cu"
}
t_cmd()    { echo "$ART/driver"; }

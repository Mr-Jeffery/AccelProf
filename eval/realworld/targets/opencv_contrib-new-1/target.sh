# opencv_contrib-new-1: modules/cudaobjdetect/src/cuda/hog.cu compute_hists_kernel_many_blocks<4>, volatile warp-synchronous histogram reduction (T21c, R2).
# Candidate, pinned eca97a4adb (no fix commit).  hog.cu is copied BYTE-FOR-BYTE (r2_extract.sh; r2/blob.check) and #included whole by common/driver.cu.
# hog.cu includes opencv2/core/cuda/*.hpp (from the opencv/opencv repository) and opencv2/cudev/ptr2d/texture.hpp (opencv_contrib modules/cudev, the pinned commit):
# DEPENDENCY HEADERS, not copied into the worktree, read from ~/incoming/realworld/deps/opencv-0316027 (setup, login node):
#   git -C ~/incoming/realworld/opencv.git archive 03160275da3abb939b3db7cf7d276649cef26db9 modules/core/include | tar -x -C $OCV     # opencv master of 2026-10-10 (day after the pin)
#   git -C ~/incoming/realworld/cand/opencv_contrib.git archive eca97a4adb2fa32afc82478947d7f049fce57ee1 modules/cudev/include | tar -x -C $OCV
# Generated OpenCV headers (cvconfig.h, opencv_modules.hpp) are stubbed in r2/common/.  Nothing is linked from OpenCV (cv::cuda::device::error is stubbed in driver.cu).
# Flags: OpenCV Release for CUDA: nvcc -O3 -DNDEBUG (no --use_fast_math: CUDA_FAST_MATH is OFF by default), -std=c++17 (CUDA 13 minimum), arch from $RW_NVCC_FLAGS.
T_ROUTE=R2; T_KERNEL=compute_hists_kernel_many_blocks; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
OCV=/home/fzheng4/incoming/realworld/deps/opencv-0316027
t_export() { :; }
t_build() {
  nvcc -std=c++17 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    -I"$SRC/common" -I"$SRC" -I"$OCV/modules/core/include" -I"$OCV/modules/cudev/include" \
    -Xcompiler -fPIC -Xcompiler -ffunction-sections -Xlinker --gc-sections \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

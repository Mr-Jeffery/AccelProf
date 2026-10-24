# llmc-new-2: karpathy/llm.c softmax_autoregressive_backward_inplace_kernel -> blockReduce<warpReduceSum> called in a loop with final_sync=false (T21c, R2).
# Candidate, pinned f1e2ace651 (no fix commit): the pinned commit is the only build.  llmc/attention.cuh and llmc/cuda_utils.cuh (the record's files) plus the
# headers they include (llmc/cuda_common.h, llmc/utils.h, llmc/cublas_common.h) are copied BYTE-FOR-BYTE from the pinned commit (r2_extract.sh; r2/blob.check).
# Stubs in common/driver.cu: `deviceProp` and a `matmul_cublaslt` stub (llmc/matmul.cuh is not copied; only the unused host launchers call it).
# Flags: the project's own (Makefile at the commit): NVCC_FLAGS = --use_fast_math -std=c++17 -O3, PFLAGS = -DENABLE_BF16 (default PRECISION=BF16), arch from $RW_NVCC_FLAGS.
T_ROUTE=R2; T_KERNEL=softmax_autoregressive_backward_inplace_kernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build() {
  nvcc --use_fast_math -std=c++17 -O3 -DENABLE_BF16 $RW_NVCC_FLAGS $RW_LINEINFO \
    -I"$SRC/common" -I"$SRC" -I"$SRC/llmc" -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

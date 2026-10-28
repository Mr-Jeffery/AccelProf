# lit-fbgemm-1: fast_gemv.cu gemv_bf16, shared-memory WAR on warpLevelSums across the col loop. R2.
# Fix 2c32f22baf (2026-10-11), parent 8b87d01bfe.  include/{fast_gemv.cu,fast_gemv.cuh,utility.cuh} byte-for-byte from both commits (r2_extract.sh);
# common/driver.cu #includes the .cu.  Only other dependency: header-only CUTLASS, the exact commit FBGEMM pins as external/cutlass at the buggy
# commit (571edeb2d0ac872a8392fc49285b156b07884b4e, CUTLASS_VERSION 4.3.0), fetched on the login node into ~/incoming/realworld/deps/cutlass (git) and
# packed as ~/incoming/realworld/deps/cutlass-include-571edeb.tar.gz (git archive of include/); unpacked node-locally at build time.
T_ROUTE=R2; T_KERNEL=gemv_bf16; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
CUTLASS_TGZ=/home/fzheng4/incoming/realworld/deps/cutlass-include-571edeb.tar.gz
t_build() {
  mkdir -p "$OUT/cutlass" && tar -xzf "$CUTLASS_TGZ" -C "$OUT/cutlass" || return 1
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO \
    --expt-relaxed-constexpr --expt-extended-lambda \
    -DCUTLASS_ENABLE_TENSOR_CORE_MMA=1 -DCUTLASS_DEBUG_TRACE_LEVEL=0 \
    -I"$SRC/common" -I"$SRC" -I"$OUT/cutlass/include" \
    -o driver "$SRC/common/driver.cu"
}
t_cmd() { echo "$ART/driver"; }

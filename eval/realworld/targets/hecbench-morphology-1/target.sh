# hecbench-morphology-1: twoWayScan (vhgw_horiz/vhgw_vert) in-place Hillis-Steele scan on shared opArray, one barrier per iteration (R1).
# Fix 7be8747ef1 (parent e245737e75).  Route R1: the app's own Makefile (nvcc -O3 -std=c++17 -arch=sm_89 -lineinfo), identical flags
# for both variants.  Driver: `./main 64 64 192 192 1` (reporter: 512x512; selSize 64 > 32: cross-warp).  No manifest overlap.
T_ROUTE=R1; T_KERNEL=vhgw; T_SPACE=shared; T_EXE=main; T_ARTIFACTS="libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 main"
t_export() { "$HARNESS/export_rev.sh" HeCBench "$2" "$3" src/morphology-cuda; }
t_build() {    # cwd = $OUT (node-local); sources unpacked at $SRC/src/...
  local sm; sm=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*(sm_[0-9]+).*/\1/')
  ( cd "$SRC/src/morphology-cuda" && make clean && make ARCH="$sm" LDFLAGS="-Xlinker '-rpath=\$\$ORIGIN'" EXTRA_CFLAGS="$RW_LINEINFO" -j"$NJOBS" ) > make.txt 2>&1 || { tail -30 make.txt; return 1; }
  cp "$SRC/src/morphology-cuda/main" main
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done
}
# 192x192 instead of the reporter's 512x512 (same kernels, same selSize 64 -> cross-warp): 5.8e6 instead of 4.3e7 thread-level memory instructions (ncu, sm_75 build).
# (128x128 prints FAIL for both variants: the app's self-check depends on the border; 130..256 PASS.)
t_cmd() { echo "$ART/main 64 64 192 192 1"; }

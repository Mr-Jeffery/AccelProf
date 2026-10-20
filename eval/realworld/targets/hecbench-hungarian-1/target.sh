# hecbench-hungarian-1: min-reduction warp steps through `volatile data*` shared pointer, no __syncwarp (R1).
# Fix 44ed88e1ae (2026-06-18), parent 5be7a451e0.  Route R1: the app's own Makefile (nvcc -O3 -std=c++17 -arch=sm_89 -lineinfo),
# identical flags for both variants; the record's driver recipe adds -D_n_=64 -D_range_=64 (the Makefile-supported `#ifdef _n_` branch:
# n=64, n_tests=100, all six reduction steps active).  T_KERNEL=min_ matches the four kernels that contain the racy warp reductions
# (calc_min_in_rows, calc_min_in_cols, min_reduce_kernel1, min_reduce_kernel2).  No overlap with eval/baselines/manifest.csv (no hungarian row).
T_ROUTE=R1; T_KERNEL=min_; T_SPACE=shared; T_EXE=main; T_ARTIFACTS="libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 main"
t_export() { "$HARNESS/export_rev.sh" HeCBench "$2" "$3" src/hungarian-cuda; }
t_build() {    # cwd = $OUT (node-local); sources unpacked at $SRC/src/...
  local sm; sm=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*(sm_[0-9]+).*/\1/')
  ( cd "$SRC/src/hungarian-cuda" && make clean && make ARCH="$sm" LDFLAGS="-Xlinker '-rpath=\$\$ORIGIN'" EXTRA_CFLAGS="$RW_LINEINFO -D_n_=64 -D_range_=64" -j"$NJOBS" ) > make.txt 2>&1 || { tail -30 make.txt; return 1; }
  cp "$SRC/src/hungarian-cuda/main" main
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done
}
# main freopen()s stdout to the file named by argv[1]
t_cmd() { echo "$ART/main output.txt"; }

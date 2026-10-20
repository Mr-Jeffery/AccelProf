# hecbench-surfel-1: surfel_render_tile<float,256> smem tile WAR (no barrier at the end of the tile loop body) (R1).
# Fix 66eba4016f (parent 7b177e4302).  Route R1: the app's own Makefile (nvcc -O3 -std=c++17 -arch=sm_89 -lineinfo -fopenmp host flag),
# identical flags for both variants.  Driver: the reporter's repro `./main 1024 64 64 1`.  No manifest overlap.
T_ROUTE=R1; T_KERNEL=surfel_render_tile; T_SPACE=shared; T_EXE=main; T_ARTIFACTS="libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 main"
t_export() { "$HARNESS/export_rev.sh" HeCBench "$2" "$3" src/surfel-cuda; }
t_build() {    # cwd = $OUT (node-local); sources unpacked at $SRC/src/...
  local sm; sm=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*(sm_[0-9]+).*/\1/')
  ( cd "$SRC/src/surfel-cuda" && make clean && make ARCH="$sm" LDFLAGS="-Xlinker '-rpath=\$\$ORIGIN'" EXTRA_CFLAGS="$RW_LINEINFO" -j"$NJOBS" ) > make.txt 2>&1 || { tail -30 make.txt; return 1; }
  cp "$SRC/src/surfel-cuda/main" main
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done
}
# 300 surfels, 16x16 image (one 16x16 block, two tiles since 300 > TILE=256): 2.5e6 thread-level memory instructions; the reporter's `1024 64 64 1` is 5e7 shared loads alone
t_cmd() { echo "$ART/main 300 16 16 1"; }

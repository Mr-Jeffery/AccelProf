# hecbench-dxtc2-1: DXT1 compressor, intra-warp shared-memory RAW/WAR in colorSums/bestFitLine/sortColors/loadColorBlock (R1).
# Fix 6e11c2bb2d (2025-09-18), parent fe80f0f747.  Route R1: the app's own Makefile (nvcc -O3 -arch=sm_89 -lineinfo), identical
# flags for both variants.  The program reads a PPM and a reference DDS; the driver input is the repo's lena_std.ppm /
# lena_ref.dds cropped to the top-left 32x32 pixels by crop.py (input preparation, no code edited).
# The Makefile's CFLAGS (EXTRA_CFLAGS -std=c++14 -Xcompiler -Wall -arch=$(ARCH) -I$(SPATH) -O3) are reproduced on the make command line
# with ONE change: -std=c++17.  CUDA 13.4's libcu++ (pulled in by cooperative_groups.h in main.cu) aborts under -std=c++14 with
# "#error libcu++ requires at least C++ 17" (and -DCCCL_IGNORE_DEPRECATED_CPP_DIALECT only moves the failure into libcu++: 97 errors).
# Link only: LDFLAGS adds an $ORIGIN rpath and the gcc-12.4 runtime libs (libstdc++, libgcc_s, libgomp) are copied next to main (system libstdc++ is gcc 8, no libstdc++.a exists).
# P9 overlap: eval/baselines/manifest.csv has P9-dxtc2-cuda (program dxtc2-cuda, label RACE) = this app's source (a different, older
# build of the same HeCBench app, input lena_std.ppm full size, 100 iterations).
T_ROUTE=R1; T_KERNEL=compress; T_SPACE=shared; T_EXE=main; T_ARTIFACTS="libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 main lena32.ppm lena32_ref.dds"
t_export() {   # login node
  "$HARNESS/export_rev.sh" HeCBench "$2" "$3" src/dxtc2-cuda src/boxfilter-sycl/shrUtils.h src/boxfilter-sycl/shrUtils.cpp \
      src/dxtc2-sycl/data/lena_std.ppm src/dxtc2-sycl/data/lena_ref.dds
}
t_build() {    # cwd = $OUT (node-local); sources unpacked at $SRC/src/...
  local sm; sm=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*(sm_[0-9]+).*/\1/')
  ( cd "$SRC/src/dxtc2-cuda" && make clean && \
    make ARCH="$sm" LDFLAGS="-Xlinker '-rpath=\$\$ORIGIN'" CFLAGS="$RW_LINEINFO -std=c++17 -Xcompiler -Wall -arch=$sm -I../boxfilter-sycl -O3" -j"$NJOBS" ) > make.txt 2>&1 || { tail -30 make.txt; return 1; }
  cp "$SRC/src/dxtc2-cuda/main" main || return 1
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done
  python3 "$TDIR/crop.py" "$SRC/src/dxtc2-sycl/data/lena_std.ppm" "$SRC/src/dxtc2-sycl/data/lena_ref.dds" lena32.ppm lena32_ref.dds 32
}
# the program writes its result next to the input path (lena32.dds), so the inputs are copied into the run directory first
t_cmd() { echo "$ART/main $ART/lena32.ppm $ART/lena32_ref.dds 1"; }  # absolute input paths: no staging into the cwd; the program writes lena32.dds into its cwd

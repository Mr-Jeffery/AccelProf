# llamacpp-2: mm_ids_helper shared-memory RAW between lanes of one warp, separated only by full-mask shfl.sync (R1).
# Fix 73a43d1f69 (2026-09-06), parent 9e0e220594.  Route R1: llama.cpp's own CMake build of the test-backend-ops target at the
# exact commit, same flags for both variants.  Static ggml/llama libraries (BUILD_SHARED_LIBS=OFF) so test-backend-ops carries all
# device code itself; the gcc-12.4 runtime libs (libstdc++, libgcc_s, libgomp: the system ones are gcc 8, no static libstdc++.a exists) are copied next to
# the binary and found through an $ORIGIN rpath (-DCMAKE_BUILD_RPATH); CUDA runtime/cuBLAS stay dynamic (/usr/local/cuda-13.4, RPATH set).  GGML_NATIVE=OFF: portable CPU reference.
T_ROUTE=R1; T_KERNEL=mm_ids_helper; T_SPACE=shared; T_EXE=test-backend-ops; T_ARTIFACTS="test-backend-ops libstdc++.so.6 libgcc_s.so.1 libgomp.so.1"
T_PARAMS='type_a=q4_0,type_b=f32,n_mats=8,n_used=4,b=0,m=512,n=32,k=256'
t_export() {   # login node: everything cmake needs to configure with tests ON (tools/ui is not needed: LLAMA_BUILD_SERVER=OFF)
  local sha=$2 out=$3 repo=$INCOMING/llama.cpp.git tools
  tools=$(git -C "$repo" ls-tree --name-only "$sha" tools/ | grep -v '^tools/ui$' | tr '\n' ' ')
  "$HARNESS/export_rev.sh" llama.cpp "$sha" "$out" CMakeLists.txt CMakePresets.json cmake common ggml include licenses src tests vendor examples pocs app $tools
}
t_build() {    # cwd = $OUT (node-local)
  local arch; arch=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  cmake -S "$SRC" -B "$OUT/cmake-build" -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="$arch" \
        -DCMAKE_CUDA_FLAGS="$RW_LINEINFO" -DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_SERVER=OFF \
        -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DCMAKE_BUILD_RPATH='$ORIGIN' > cmake-configure.txt 2>&1 || { tail -30 cmake-configure.txt; return 1; }
  cmake --build "$OUT/cmake-build" --target test-backend-ops -j"$NJOBS" > build-all.txt 2>&1 || { tail -40 build-all.txt; return 1; }
  cp "$OUT/cmake-build/bin/test-backend-ops" test-backend-ops || return 1
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done   # $ORIGIN rpath, see header
  { grep -E "CMAKE_CUDA_ARCHITECTURES|CMAKE_CUDA_FLAGS:|CMAKE_BUILD_TYPE|BUILD_SHARED_LIBS|GGML_NATIVE" "$OUT/cmake-build/CMakeCache.txt"
    grep -m3 -E "nvcc|-gencode" "$OUT/cmake-build/ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/flags.make" 2>/dev/null | cut -c1-600
    ldd test-backend-ops | sed 's/(0x.*//'; } > build-info.txt 2>&1
}
t_cmd() { echo "$ART/test-backend-ops test -b CUDA0 -o MUL_MAT_ID -p '$T_PARAMS'"; }

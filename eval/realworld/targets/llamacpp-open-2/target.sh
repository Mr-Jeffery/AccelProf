# llamacpp-open-2: flash_attn_ext_vec (fattn-vec.cuh) KQ shared-memory WAR between loop iterations (R1, T21c candidate).
# Pinned (buggy) 1b70350c92563449576bcbbf552994b1d1ed847d; FIX below = 99db719bdf07f7d537431ca556a0512bf3d995b6 (llama.cpp master, 2026-10-19,
# the revision the coordinator names as the fixed build; record fix_commit is null, so rw.sh would build `buggy` only: FIX is set here and
# target.sh is sourced after rw.sh reads the record).  Route R1: llama.cpp's own CMake build of test-backend-ops, identical flags for both
# variants, copied from llamacpp-4 (static ggml/llama libs, gcc-12.4 runtime libs next to the binary with an $ORIGIN rpath, GGML_NATIVE=OFF,
# -DLLAMA_SUBPROCESS=OFF: kept identical to llamacpp-4 so the three llama.cpp targets share one set of flags; the option only drops subprocess
# support from llama-common and touches no test-backend-ops or CUDA code).
FIX=99db719bdf07f7d537431ca556a0512bf3d995b6
T_ROUTE=R1; T_KERNEL=flash_attn_ext_vec; T_SPACE=shared; T_EXE=test-backend-ops; T_ARTIFACTS="test-backend-ops libstdc++.so.6 libgcc_s.so.1 libgomp.so.1"
T_PARAMS='hsk=128,hsv=128,nh=4,nr23=\[1,1\],kv=512,nb=1,.*type_K=f16'
t_export() {   # login node: everything cmake needs to configure with tests ON (tools/ui is not needed: LLAMA_BUILD_SERVER=OFF)
  local sha=$2 out=$3 repo=$INCOMING/llama.cpp.git tools
  tools=$(git -C "$repo" ls-tree --name-only "$sha" tools/ | grep -v '^tools/ui$' | tr '\n' ' ')
  "$HARNESS/export_rev.sh" llama.cpp "$sha" "$out" CMakeLists.txt CMakePresets.json cmake common ggml include licenses src tests vendor examples pocs app $tools
}
t_build() {    # cwd = $OUT (node-local)
  local arch; arch=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  cmake -S "$SRC" -B "$OUT/cmake-build" -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="$arch" \
        -DCMAKE_CUDA_FLAGS="$RW_LINEINFO" -DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_SERVER=OFF \
        -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DLLAMA_SUBPROCESS=OFF -DCMAKE_BUILD_RPATH='$ORIGIN' > cmake-configure.txt 2>&1 || { tail -30 cmake-configure.txt; return 1; }
  cmake --build "$OUT/cmake-build" --target test-backend-ops -j"$NJOBS" > build-all.txt 2>&1 || { tail -40 build-all.txt; return 1; }
  cp "$OUT/cmake-build/bin/test-backend-ops" test-backend-ops || return 1
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done   # $ORIGIN rpath, see header
  { grep -E "CMAKE_CUDA_ARCHITECTURES|CMAKE_CUDA_FLAGS:|CMAKE_BUILD_TYPE|BUILD_SHARED_LIBS|GGML_NATIVE" "$OUT/cmake-build/CMakeCache.txt"
    grep -m3 -E "nvcc|-gencode" "$OUT/cmake-build/ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/flags.make" 2>/dev/null | cut -c1-600
    ldd test-backend-ops | sed 's/(0x.*//'; } > build-info.txt 2>&1
}
t_cmd() { echo "$ART/test-backend-ops test -b CUDA0 -o FLASH_ATTN_EXT -p '$T_PARAMS'"; }

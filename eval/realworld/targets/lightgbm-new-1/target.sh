# lightgbm-new-1: FixHistogramKernel -> ShuffleReduceSum<double> shared_mem_buffer reuse (cuda_histogram_constructor.cu L762/L763) (R1, T21c candidate).
# Pinned (buggy) c8be3579413199a6e0f769e74c15ee119735471c (microsoft/LightGBM master, 2026-10-09); no fix commit, only the buggy variant is built.
# Route R1: LightGBM's own CMake build of the `lightgbm` CLI with -DUSE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release (CMake turns the plain
# 89 into --generate-code arch=compute_89,code=[compute_89,sm_89], SASS + PTX).  The project's own CUDA flags are kept: CMakeLists.txt appends "-O3 -lineinfo" to
# CMAKE_CUDA_FLAGS itself (USE_DEBUG=OFF), so -lineinfo is always on; for the `lineinfo` phase (RW_LINEINFO empty) the generated flags.make files in the
# node-local build tree are sed-ed to drop it (generated build files only, no source change).  No -G.
# Dependencies at the revision's own submodule pins, fetched with git on the login node into ~/incoming/realworld/deps/lgbm-<name>.git and placed into
# external_libs/{eigen,fast_double_parser,fmt,nanoarrow} of the exported tree (the partial clone has only the gitlinks): eigen 3147391d, fast_double_parser 252029dd,
# fmt 8303d140, nanoarrow a579fbf5.  NCCL (find_package(NCCL REQUIRED) when USE_CUDA; this revision initialises NCCL even for one GPU) is built from the NVIDIA/nccl tag v2.29.3-1 (fetched with git on the login node, built for sm_89 by deps/build_nccl.sh, static libnccl_static.a) because the HPC SDK 23.7 NCCL 2.18.3 on the cluster fails to link against CUDA 13 (undefined cudaGetDeviceProperties_v2);
# installed in $RW/src/lightgbm-new-1/nccl-2.29.3 and passed as NCCL_ROOT.  gcc-12.4 runtime libs copied next to the binary ($ORIGIN rpath), like llamacpp-4.
# CMake: CMakeLists.txt at this revision says cmake_minimum_required(VERSION 3.28) and the cluster has 3.26.5, so CMake 3.31.6 (Kitware tag v3.31.6, fetched with git on the login node into
# ~/incoming/realworld/deps/cmake-kitware.git, bootstrapped on a compute node by deps/build_cmake.sh with gcc 12.4) is installed to $RW/src/lightgbm-new-1/cmake-3.31.6 and put first in PATH.
# Driver: the `lightgbm` CLI with a generated 1,000 x 6 dataset (gen_data.py in this directory; three features are 70% exactly 5.0 so their most frequent bin is not 0),
# max_bin=255, 3 gbdt iterations, 15 leaves, device_type=cuda.
T_ROUTE=R1; T_KERNEL=FixHistogramKernel; T_SPACE=shared; T_EXE=lightgbm; T_ARTIFACTS="lightgbm libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 train.tsv train.conf"
t_export() {   # login node: main tree (only what CMake needs) + the four submodule trees at the revision's gitlink pins
  local sha=$2 out=$3 repo=$INCOMING/cand/LightGBM.git dep=$INCOMING/deps tmp n s
  tmp=$(mktemp -d /tmp/lgbm-export.XXXXXX) || return 1
  "$HARNESS/export_rev.sh" cand/LightGBM "$sha" "$tmp/main.tar.gz" CMakeLists.txt VERSION.txt cmake include src || return 1
  mkdir -p "$tmp/x"; tar -xzf "$tmp/main.tar.gz" -C "$tmp/x"
  for n in eigen fast_double_parser fmt nanoarrow; do
    s=$(git -C "$repo" ls-tree "$sha" external_libs/$n | awk '{print $3}')
    mkdir -p "$tmp/x/external_libs/$n"; git -C "$dep/lgbm-$n.git" archive "$s" | tar -x -C "$tmp/x/external_libs/$n" || return 1
    echo "submodule $n @ $s"
  done
  tar -czf "$out" -C "$tmp/x" .; rm -rf "$tmp"
  echo "t_export: $out ($(du -sh "$out" | cut -f1))"
}
t_build() {    # cwd = $OUT (node-local)
  export PATH=/mnt/beegfs/fzheng4/realworld/src/lightgbm-new-1/cmake-3.31.6/bin:$PATH   # CMake 3.31.6, see header: the revision needs >= 3.28
  local arch; arch=$(echo "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/')
  cmake -S "$SRC" -B "$OUT/cmake-build" ${RW_CMAKE_EXTRA:-} -DCMAKE_BUILD_TYPE=Release -DUSE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="$arch" -DBUILD_CLI=ON \
        -DNCCL_ROOT=/mnt/beegfs/fzheng4/realworld/src/lightgbm-new-1/nccl-2.29.3 -DCMAKE_BUILD_RPATH='$ORIGIN' > cmake-configure.txt 2>&1 || { tail -30 cmake-configure.txt; return 1; }
  if [ -z "$RW_LINEINFO" ]; then   # lineinfo phase: generated build files only
    grep -rl -- '-lineinfo' "$OUT/cmake-build" --include=flags.make --include=build.make --include=link.txt 2>/dev/null | xargs -r sed -i 's/ -lineinfo//g'
    echo "lineinfo removed from generated flags: $(grep -rl -- '-lineinfo' "$OUT/cmake-build" --include=flags.make | wc -l) flags.make still mention it"
  fi
  cmake --build "$OUT/cmake-build" --target lightgbm -j"$NJOBS" > build-all.txt 2>&1 || { tail -40 build-all.txt; return 1; }
  cp "$SRC/lightgbm" lightgbm 2>/dev/null || cp "$OUT/cmake-build/lightgbm" lightgbm || return 1   # LightGBM sets EXECUTABLE_OUTPUT_PATH to the source dir
  for l in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -L /opt/ohpc/pub/compiler/gcc/12.4.0/lib64/$l . || return 1; done
  python3 "$TDIR/gen_data.py" train.tsv || return 1
  cat > train.conf <<CONF
task = train
boosting = gbdt
objective = regression
device_type = cuda
data = $ART/train.tsv
max_bin = 255
num_leaves = 15
num_iterations = 3
learning_rate = 0.1
min_data_in_leaf = 20
num_threads = 4
verbosity = 1
seed = 1
CONF
  { grep -E "CMAKE_CUDA_ARCHITECTURES|CMAKE_CUDA_FLAGS:|CMAKE_BUILD_TYPE|USE_CUDA|NCCL_" "$OUT/cmake-build/CMakeCache.txt"
    grep -h -m2 -E "CUDA_FLAGS|CUDA_DEFINES" "$OUT/cmake-build/CMakeFiles/lightgbm_objs.dir/flags.make" 2>/dev/null | cut -c1-500
    ldd lightgbm | sed 's/(0x.*//'; } > build-info.txt 2>&1
}
t_cmd() { echo "$ART/lightgbm config=$ART/train.conf output_model=model.txt"; }

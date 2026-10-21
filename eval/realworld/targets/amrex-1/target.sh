# amrex-1: AMReX MLNodeABecLaplacian::Fsmooth GPU path (ParallelFor lambda: mlndlap_adotx_aa reads sol neighbours, mlndabeclap_jacobi_aa
# updates sol(i,j,k) in place, one launch) -- global-memory read/write race.  Fix 930e7c223f (2026-10-04), parent bfc7fcfe6f.
# Route R1: AMReX's own CMake build (CUDA backend, 3D, no MPI) and its own test target Test_LinearSolvers_ABecLaplacian_C_3d
# (Tests/LinearSolvers/ABecLaplacian_C), run with the shipped inputs-node and command-line overrides.
T_ROUTE=R1; T_KERNEL=MLNodeABecLaplacian7Fsmooth; T_KERNEL_NSYS="MLNodeABecLaplacian::Fsmooth"; T_SPACE=global; T_RACECHECK=na
T_EXE=Test_LinearSolvers_ABecLaplacian_C_3d; T_ARTIFACTS="Test_LinearSolvers_ABecLaplacian_C_3d inputs-node"
t_export() { "$HARNESS/export_rev.sh" amrex "$2" "$3" CMakeLists.txt CHANGES.md CTestConfig.cmake Tools Src Tests; }
t_build() {
  local cc arch
  cc=$(printf '%s' "$RW_NVCC_FLAGS" | sed -E 's/.*sm_([0-9]+).*/\1/'); arch="${cc:0:1}.${cc:1}"
  local args=(-DCMAKE_BUILD_TYPE=Release -DAMReX_GPU_BACKEND=CUDA -DAMReX_CUDA_ARCH=$arch -DAMReX_SPACEDIM=3 -DAMReX_MPI=OFF -DAMReX_OMP=OFF
              -DAMReX_LINEAR_SOLVERS=ON -DAMReX_ENABLE_TESTS=ON "-DCMAKE_CUDA_FLAGS=$RW_LINEINFO" ${RW_CMAKE_EXTRA:-})   # T21b: RW_CMAKE_EXTRA="-DCMAKE_CUDA_RUNTIME_LIBRARY=Shared ..." (relink_job.sh); empty = T21a as built
  echo "cmake args: ${args[*]}  (AMReX_CUDA_ARCH from RW_NVCC_FLAGS=$RW_NVCC_FLAGS)" | tee cmake_args.txt
  cmake -S "$SRC" -B bld "${args[@]}" > cmake.log 2>&1 || { tail -30 cmake.log; return 1; }
  make -C bld -j"${NJOBS:-8}" Test_LinearSolvers_ABecLaplacian_C_3d > make.log 2>&1 || { grep -n -E "error|Error" make.log | head -30; tail -15 make.log; return 1; }
  local exe; exe=$(find bld -name Test_LinearSolvers_ABecLaplacian_C_3d -type f | head -1)
  [ -n "$exe" ] || { echo "no test executable built"; return 1; }
  cp "$exe" Test_LinearSolvers_ABecLaplacian_C_3d
  cp "$SRC/Tests/LinearSolvers/ABecLaplacian_C/inputs-node" inputs-node
  { echo "# compile and link commands (CUDA) of the test target"; find bld/Tests -path '*ABecLaplacian_C_3d.dir*' -name flags.make -exec cat {} \; ; find bld/Tests -path '*ABecLaplacian_C_3d.dir*' -name link.txt -exec cat {} \; ; } > build_flags.txt 2>/dev/null
  return 0
}
t_cmd() { echo "$ART/Test_LinearSolvers_ABecLaplacian_C_3d $ART/inputs-node n_cell=16 max_grid_size=8"; }

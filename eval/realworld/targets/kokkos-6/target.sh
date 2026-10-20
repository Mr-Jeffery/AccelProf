# kokkos-6: Kokkos cuda_inter_warp_reduction missing trailing __syncthreads (sh_result reuse WAR, Kokkos_Cuda_ReduceScan.hpp L105 vs L116-118
# at the parent).  Fix 71761882dc (2022-10-13), parent af65233184.  Driver = the fix's TestRepeatedTeamReduce pasted in and shrunk.
# Route R1: Kokkos' own CMake build (CUDA), driver linked in-tree; same flags for both variants (see kokkos_build.sh).
T_ROUTE=R1; T_KERNEL=TestRepeatedTeamReduce; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
source "$TDIR/kokkos_build.sh"
t_export() { "$HARNESS/export_rev.sh" kokkos "$2" "$3" CMakeLists.txt cmake bin core/CMakeLists.txt core/cmake core/src containers/CMakeLists.txt containers/cmake containers/src algorithms/CMakeLists.txt algorithms/cmake algorithms/src example/CMakeLists.txt simd tpls; }
t_build()  { kokkos_build "$TDIR/driver.cpp"; }
t_cmd()    { echo "$ART/driver"; }

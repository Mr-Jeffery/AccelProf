# kokkos-5: Kokkos CudaReductionsFunctor<F,Tag,false,false>::scalar_intra_warp_reduction broadcast '*value = *(value - lane_id)'
# (intra-warp WAR on shared memory, Kokkos_Cuda_ReduceScan.hpp L551 at the parent).  Fix db1a77ddc4 (2022-03-08), parent 87415792f5.
# Route R1: Kokkos' own CMake build (CUDA), driver linked in-tree; same flags for both variants (see kokkos_build.sh).
T_ROUTE=R1; T_KERNEL=RwSumFunctor; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
source "$TDIR/kokkos_build.sh"
t_export() { "$HARNESS/export_rev.sh" kokkos "$2" "$3" CMakeLists.txt cmake bin core/CMakeLists.txt core/cmake core/src containers/CMakeLists.txt containers/cmake containers/src algorithms/CMakeLists.txt algorithms/cmake algorithms/src example/CMakeLists.txt; }
t_build()  { kokkos_build "$TDIR/driver.cpp"; }
t_cmd()    { echo "$ART/driver"; }

# ginkgo-5: Ginkgo range_minimum_query compute_lookup_small / compute_lookup_large: plain RMW on bit-packed words (global-memory lost-update race,
# common/unified/components/range_minimum_query_kernels.cpp -> core/components/bit_packed_storage.hpp set()).
# Fix 64f194612d (2025-01-10), parent 09d861f107.  Route R1, direct-launch variant (see ginkgo5_build.sh): the revision's own kernel TU,
# compiled with the project's CMake-generated command, called from driver.cpp through a real CudaExecutor.
T_ROUTE=R1; T_KERNEL=compute_lookup_; T_SPACE=global; T_RACECHECK=na; T_EXE=driver; T_ARTIFACTS="driver"
source "$TDIR/ginkgo5_build.sh"
t_export() { "$HARNESS/export_rev.sh" ginkgo "$2" "$3"; }
t_build()  { ginkgo5_build "$TDIR/driver.cpp"; }
t_cmd()    { echo "$ART/driver"; }

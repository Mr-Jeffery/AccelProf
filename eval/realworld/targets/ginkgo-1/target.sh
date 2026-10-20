# ginkgo-1: Ginkgo generic_kernel_col_reduction_2d_blocked missing barrier at the end of the column-block loop (block_partial reuse WAR,
# common/cuda_hip/base/kernel_launch_reduction.hpp).  Fix 4d8ec443d3 (2026-09-08), parent e0d4d6e071.
# Route R1, DIRECT LAUNCH (the record's cheaper variant): cmake configure only + driver compiled with the CUDA backend's own flags.
T_ROUTE=R1; T_KERNEL=generic_kernel_col_reduction_2d_blocked; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
source "$TDIR/ginkgo_build.sh"
t_export() { "$HARNESS/export_rev.sh" ginkgo "$2" "$3"; }
t_build()  { ginkgo_build "$TDIR/driver.cu"; }
t_cmd()    { echo "$ART/driver"; }

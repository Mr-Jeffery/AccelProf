# cccl-1: cub BlockReduceRaking smem-reuse WAR (R1h).  Fix cb8707cbba (2024-11-05), parent 5e0f9222c4.
T_ROUTE=R1h; T_KERNEL=block_reduce_kernel; T_SPACE=shared; T_EXE=driver
t_export() { r1h_cccl_export "$@"; }
t_build()  { r1h_cccl_build "$TDIR/driver.cu"; }
t_cmd()    { echo "$ART/driver"; }

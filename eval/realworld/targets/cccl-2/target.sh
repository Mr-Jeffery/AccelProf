# cccl-2: cub agent_rle WarpScanAllocations smem-reuse WAR (R1h).  Fix ee14babeaa (2023-09), parent eea703e553.
T_ROUTE=R1h; T_KERNEL=DeviceRleSweepKernel; T_SPACE=shared; T_EXE=driver
t_export() { r1h_cccl_export "$@"; }
t_build()  { r1h_cccl_build "$TDIR/driver.cu"; }
t_cmd()    { echo "$ART/driver 1440"; }

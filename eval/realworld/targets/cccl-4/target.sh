# cccl-4: cub test decoupled_look_back_kernel, missing barrier on global tile_data (R1h).  Fix 5dad0bff89 (2025-04-28), parent 45f868f38f.
# The kernel is in the cub TEST file, so each variant compiles its own verbatim excerpt (driver_<variant>.cu, made by gen_driver.sh).
T_ROUTE=R1h; T_KERNEL=decoupled_look_back_kernel; T_SPACE=global; T_RACECHECK=na; T_EXE=driver
t_export() { r1h_cccl_export "$@"; }
t_build()  { r1h_cccl_build "$TDIR/driver_$1.cu"; }
t_cmd()    { echo "$ART/driver 64"; }

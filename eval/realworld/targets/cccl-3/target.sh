# cccl-3: cub DeviceTopK finalize_pass, global hand-off without acquire (R1h).  Fix 879ab26a11 (2026-08), parent 8b99dbeba0.
T_ROUTE=R1h; T_KERNEL=TopK; T_SPACE=global; T_RACECHECK=na; T_EXE=driver
t_export() { r1h_cccl_export "$@"; }
t_build()  { r1h_cccl_build "$TDIR/driver.cu"; }
t_cmd()    { echo "$ART/driver 100000 16"; }

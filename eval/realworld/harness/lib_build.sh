# eval/realworld/harness/lib_build.sh -- sourced by rw.sh; helpers for target.sh files.

# --- R1h: header-only library, driver compiled against the checkout's headers placed BEFORE the toolkit's bundled CCCL ---
# CCCL layout since 2023: cub/cub, thrust/thrust, libcudacxx/include (the monorepo dirs cub/, thrust/, libcudacxx/ hold the -I roots).
r1h_cccl_export() {   # t_export for the CCCL targets: $1 variant, $2 sha, $3 out.tar.gz
  "$HARNESS/export_rev.sh" cccl "$2" "$3" cub/cub thrust/thrust libcudacxx/include
}
r1h_cccl_build() {    # r1h_cccl_build <driver.cu> [extra nvcc flags]; cwd = $OUT; leaves driver, hdr.log, h_proof.txt
  local drv=$1; shift
  local inc="-I$SRC/cub -I$SRC/thrust -I$SRC/libcudacxx/include"
  nvcc -std=${RW_STD:-c++17} $RW_NVCC_FLAGS $RW_LINEINFO $inc "$@" -o driver "$drv" || return 1
  nvcc -Xcompiler -H -std=${RW_STD:-c++17} $RW_NVCC_FLAGS $RW_LINEINFO $inc "$@" -c -o /dev/null "$drv" > hdr.log 2>&1
  "$HARNESS/h_proof.sh" hdr.log "$SRC" | tee h_proof.txt
}

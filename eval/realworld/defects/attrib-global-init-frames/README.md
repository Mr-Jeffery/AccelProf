# Defect (harness): `rw_attribute.cubin_frames` gives the last kernel of a cubin the frames of a data section

Found by the T21b Opus triage of `lit-fbgemm-1` (buggy build MISSED in both modes). Class (c) of T21c step 3, harness side
(`eval/realworld/harness/rw_attribute.py`), not the detector. Runs below: the **WSL triage build** box (CUDA 13.3 nvdisasm); no detector run
is needed.

## Mechanism

`cubin_frames` (rw_attribute.py:39-68) runs `nvdisasm --print-line-info-inline <cubin>` without `-c` (:46), so the listing also holds the
data sections, whose bytes are printed as `/*OFFSET*/ .byte ...` lines. `SECTION_RE` (:31) matches only `.section .text.<fn>`; a
non-text `.section` line does not reset `fn` (:49-54), and `OFF_RE` (:30) matches the data lines, so (:62-64) every data offset that is
also a code offset of the last `.text` function before it overwrites that pc's frames with the last `//##` group seen (the function's
final line-info group). A cubin with an initialised `__device__` array has `.nv.global.init` after the last `.text` section.

## Input and command

`global_init_lineinfo.cu`: a kernel `k` (STS at line 12, LDS at line 14) and a 16 KiB initialised `__device__` array.
`check_frames.py`: the parser of rw_attribute.py:29-31 and :47-66 copied verbatim, run on the full listing (as the harness does) and on the
`-c` listing.

    source ~/curace-wsl/env.sh
    nvcc -arch=native -lineinfo --cudart shared -o gil global_init_lineinfo.cu
    cuobjdump -xelf all gil
    python3 -I check_frames.py global_init_lineinfo.sm_89.cubin

## Expected and actual

| pc | SASS | expected frame | harness parser (actual) |
|---|---|---|---|
| 0x0040 | `STS [R6.X4], R6` | global_init_lineinfo.cu:12 | global_init_lineinfo.cu:15 |
| 0x00a0 | `LDS R0, [R0.X4]` | global_init_lineinfo.cu:14 | global_init_lineinfo.cu:15 |

On the T21b `lit-fbgemm-1` buggy driver (`gemv_bf16` is the last `.text` section; `.nv.global.init` holds curand's mrg32k3a tables, 13,628
offset lines) every pc of `gemv_bf16` gets `sm_30_intrinsics.hpp:439 <- fast_gemv.cuh:65 <- fast_gemv.cu:149`; the `-c` listing gives
0x27d0 -> fast_gemv.cu:145 and 0x2b00 -> fast_gemv.cu:141 (`wsl_run.txt`).

Fix (harness only, for the T21b helper): reset `fn = None` on every `.section` line that is not `.text.*`, or call nvdisasm with `-c`;
then re-run the attribution of every target and diff the reports' frames.

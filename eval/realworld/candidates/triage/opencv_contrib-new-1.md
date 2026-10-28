# T21c triage: opencv_contrib-new-1 (opencv_contrib eca97a4adb2fa32afc82478947d7f049fce57ee1, `compute_hists_kernel_many_blocks<4>`)

Inputs: `eval/results/realworld_t21c/attrib/opencv_contrib-new-1-buggy.json` (scalar-clock, 1 kernel JSON, 64 reports, 0 SC, 5
ordered, 244 skipped, all 132 skipped site pairs intra-thread-only), `other_reports.csv` (9 rows), `recall.csv` (DR component
DETECTED, SC component DETECTED-AS-DR), racecheck `eval/realworld/racecheck/opencv_contrib-new-1-buggy.txt`, SASS of the traced
build (`/mnt/beegfs/fzheng4/realworld_t21c/build/opencv_contrib-new-1/buggy/driver`, md5 53162d4512e901c9e2e992d014ccb9da),
trace edges of `kernel_0.json`. Launch: default HOG on 64x128, `<<<(2,15), (32,2,4)>>>`; a warp is one (threadIdx.y,
threadIdx.z), i.e. two cells of 16 lanes, 12 active lanes per cell (patch_size 12, threads_cell 16).

## Groups

| # | kernel | pcs (a -> b) | file:line pair | n | class | reason |
|---|---|---|---|---|---|---|
| G1 | compute_hists_kernel_many_blocks<4> | {0x1310, 0x1650, 0x19a0, 0x1c90} -> {0x1ed0, 0x2020, 0x2140, 0x2240, 0x23c0} | hog.cu:191 STS -> hog.cu:199 LDS, RAW | 20 | **(a)** | lane t+6 accumulates hist column t+6 (plain `+=`), lane t (t<6) reads it through the volatile alias at L199; same warp, no `__syncwarp` before L208. Oracle DR pair |
| G2 | same | {0x1470, 0x17b0, 0x1af0, 0x1cc0} -> same 5 LDS | hog.cu:192 STS -> hog.cu:199 LDS, RAW | 20 | **(a)** | as G1 for the second vote (bin.y) |
| G3 | same | {0x5f0, 0x630, 0x660, 0x680, 0x6a0, 0x6c0, 0x6e0, 0x6f0, 0x850} -> {0x1ed0, 0x2020, 0x2140, 0x2240, 0x23c0} | hog.cu:167 STS (zeroing) -> hog.cu:199 LDS, RAW | 9 | **(a)** | lane t+6 zeroes column t+6 of every bin row (L167); for rows lane t+6 never votes into, the zero is the value lane t reads at L199. Same mechanism as G1 (the record's corrected `accesses` already names L167). All 9 are the `other_reports.csv` rows |
| G4 | same | 0x1f20->0x1f60, 0x2040->0x2060, 0x2170->0x2190, 0x2260->0x2280, 0x2420->0x2450 | hog.cu:199 STS -> hog.cu:201 LDS, RAW | 5 | **(a)** | lane t+3 (t<3) stores hist_[t+3] at L199, lane t loads it at L201; volatile on both sides (SC in PTX source, plain LDS/STS in SASS -> DR per D20). Oracle SC pair |
| G5 | same | 0x1f90->{0x1fb0, 0x1fc0}, 0x20a0->{0x20c0, 0x20d0}, 0x21c0->{0x21e0, 0x21f0}, 0x22a0->{0x22c0, 0x22d0}, 0x2480->{0x24a0, 0x24b0} | hog.cu:201 STS -> hog.cu:204 LDS, RAW | 10 | **(a)** | lanes 1 and 2 store hist_[1], hist_[2] at L201, lane 0 loads them at L204; volatile both sides |

Totals: 64 reports, 64 class (a), 0 (b), 0 (c), 0 (d); one distinct race (the warp-synchronous histogram reduction, the oracle's),
no new race. Each group's pcs are the 4-way unrolled copies of the bin loop (the 5th LDS pc 0x23c0 is the remainder copy).
No WAR or WAW pair exists in this reduction (each step writes columns no later step of the same row writes, and each row is
reduced once), and none is reported. No report matches the LDS vs ATOMS.CAST.SPIN false-report class.

## Mechanism and ordering

The accumulation (L166-L193) writes the per-lane column through a plain `float*`; the reduction (L196-L205) reads and writes
through `volatile float* hist_`. The first `__syncthreads()` after the reduction is at L208. Thread pairs (block (1,8,0) as in
racecheck): thread (6,0,1) stores column 6 at L192 (0x1cc0), thread (0,0,1) loads it at L199 (0x1ed0); thread (3,0,1) stores
hist_[3] at L199, thread (0,0,1) loads it at L201. Same warp (threadIdx.y = 0, threadIdx.z = 1), same block. racecheck reports
these as "Warp Level Programming" warnings (166,335 in total; the displayed 2,000 are L191/L192->L199 754 each, L199->L201 329,
L201->L204 113, L167->L199 50). Trace edges of all 64 reported pc pairs are `intra_warp` only (41,580 pairs, 0 intra-block).

SASS: the accumulation stores are plain `STS` at 0x0eb0..0x1cc0 (each `+=` is LDS+STS, data-dependent row, not kept in
registers) and come before the reduction in program order. The reduction is unrolled by four plus a remainder, fully
predicated: per bin `@!P4 LDS, @!P4 LDS, @!P4 STS` (L199), `@P3 LDS, @P3 LDS, @P3 STS` (L201), `@!P1 LDS x3` (L204), then
`@!P1 STS` to final_hist (L203): every volatile load and store of the source is present (8 LDS + 2 STS per bin). There is no
BSSY, BSYNC or WARPSYNC between the accumulation and L204; the lanes 12-15 of each cell branch around the whole block at 0x210
(`@P0 BRA`) and wait at `WARPSYNC 0xffffffff` / `BAR.SYNC` (0x2510/0x2530, L208). So on this build the 12 active lanes execute
the reduction converged, in one instruction stream: formal only.

## Driver check (grad/qangle filled on the host)

The driver (`targets/opencv_contrib-new-1/r2/common/driver.cu`) replaces `compute_gradients_8UC1` with pseudo-random host data:
bin pairs (b, (b+1) % 9) and two non-negative votes, which is the structure the gradient kernel produces (adjacent bins, two
weights). This cannot change which accesses race: every lane writes only its own column `cell_thread_x` of the histogram
(L163-L165), the bin values only select the row, and every row of the column is zeroed at L167 regardless of the data. So for
any input, column t+6 (resp. t+3, 1, 2) is written by lane t+6 (resp. t+3, 1, 2) and read by lane t at L199 (L201, L204). The
data only decide which rows also get L191/L192 stores (G1/G2) rather than only the L167 store (G3); out-of-range bins would
write out of bounds, and the host data stay in [0, 9). The grad pitch (2*width floats) differs from a GpuMat pitch only for
global addresses.

## Header check (opencv core 03160275da vs the contrib pin)

hog.cu includes `opencv2/core/cuda/{common,reduce,functional,warp_shuffle}.hpp` and `opencv2/cudev/ptr2d/texture.hpp`. The
kernel uses only `PtrStep<T>::ptr()` (cuda_types.hpp), `::expf`, `::fabs` and the `__constant__` symbols defined in hog.cu.
The opencv commit current at the contrib pin's time (2026-10-09 08:11 +0300) is 0a74032072dac88b25b68d184bcac35313f1297a;
`git diff 0a740320 03160275da -- modules/core/include` touches 17 files: `core/base.hpp` (host-only `cv_abs` overflow fix, no
`__device__` code), `core/hal/intrin_*.hpp` (CPU SIMD), `core/mat.hpp`, `core/mat.inl.hpp`, `core/opencl/ocl_defs.hpp`. Nothing
under `core/cuda/`, `cuda_types.hpp` or `cvdef.h` changed (last change to cuda_types.hpp: 32b08d2b9, 2026-09-24, a GCC-version
`#pragma` guard). cudev comes from the pinned contrib commit itself. So the headers cannot affect the kernel.

## Not checked

Non-default HOG configurations (nblocks 1-3) and `compute_hists_kernel_many_blocks<1..3>` were not traced (the driver uses
the default configuration only).

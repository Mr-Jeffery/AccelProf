# opencv_contrib-new-1 reproducer: expected output

Build: `bash build.sh`. Compile-checked on a `normal` node (2026-10-25, CUDA 13.4): all three build. **Not run.**

Input: 64x128 image, default HOG configuration, `compute_hists_kernel_many_blocks<4><<<(2,15), (32,2,4)>>>`; votes are small
integers and are added unweighted, so every histogram bin is an exact integer. The host reference sums, for each of the
105 HOG blocks x 4 cells x 9 bins = 3,780 bins, the votes of the cell's 12x12 patch.

| binary | expected stdout (last line) | wrong output looks like |
|---|---|---|
| `repro` | `opencv_contrib-new-1 repro: bins=3780 wrong=0 -> output correct` | `hist i: got X expected Y` lines, then `wrong=N -> WRONG OUTPUT` |
| `repro_fixed` | `... repro_fixed: bins=3780 wrong=0 -> output correct` | same |
| `repro_perturb 0` | `... mode=0: bins=3780 wrong=0 -> output correct` | same |
| `repro_perturb 1` | predicted `wrong=0 -> output correct` | `wrong>0` would mean the faithful perturbation produced a wrong histogram |
| `repro_perturb 2` | predicted `wrong>0 -> WRONG OUTPUT` (up to all 3,780 bins) | n/a: this mode realizes the bad schedule on purpose |

Why (SASS): in the target and in `repro` the reduction L196-L205 is unrolled and fully predicated (`@!P4 LDS/STS`,
`@P3 LDS/STS`, `@!P1 LDS`): the only branches are the uniform loop-control branches on `cnbins`, and there is no BSSY and no WARPSYNC between L191/L192 and L204, so the 12 active lanes of a cell
execute it converged. Mode 1 adds `if (cell_thread_x == 3) __nanosleep(ns)` before L199; ptxas brackets it with
`BSSY B2 ... BSYNC B2` in every unrolled iteration, so the lanes reconverge before L199: no wrong output can be produced
this way. In mode 2 lane 3 runs the reduction in its own noinline instance (`reduce_hists<1>`); the two paths rejoin only at
the `WARPSYNC`/`BAR.SYNC` of L208, so lanes 0-2 can read hist_[3..5] (L201) before lane 3 has added hist_[9] (L199).

`repro_fixed`: `__ballot_sync` (VOTE) plus `__syncwarp(mask)`, which ptxas lowers to `BRA.CONV` + `CALL` to a WARPSYNC stub
(2 WARPSYNC, 11 CALL in the binary); in a converged warp the stub is skipped. If cuVein still reports on `repro_fixed`, that is
a detector-model gap (see the droidslam-new-1 note and hecbench-hungarian-1 in REALWORLD.md), not a residual race.

Results: TO BE RUN (see `../../opencv_contrib-new-1.md`).

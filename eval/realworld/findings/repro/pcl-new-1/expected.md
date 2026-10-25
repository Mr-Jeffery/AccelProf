# pcl-new-1 reproducer: expected output

Build: `bash build.sh`. Compile-checked on a `normal` node (2026-10-25, CUDA 13.4): all three build. **Not run.**

Input: 2,000 points on a slightly noisy plane, 40 neighbours each (lanes 0-7 loop twice), `EstimateNormalsKernel<<<250, 256>>>`
(one warp per point). Lane 0 writes the six reduced covariance entries; the host recomputes them in double and flags a
point when any entry differs by more than 1e-4*(1+|ref|) (float summation-order error is ~1e-6; one lost lane is ~1/32).

| binary | expected stdout (last line) | wrong output looks like |
|---|---|---|
| `repro` | `pcl-new-1 repro: points=2000 wrong=0 -> output correct` | `point i: cov00 got X expected Y` lines, then `wrong=N -> WRONG OUTPUT` |
| `repro_fixed` | `pcl-new-1 repro_fixed: points=2000 wrong=0 -> output correct` | same |
| `repro_perturb 0` | `... mode=0: points=2000 wrong=0 -> output correct` | same |
| `repro_perturb 1` | predicted `wrong=0 -> output correct` | `wrong>0` would mean the faithful perturbation produced wrong output |
| `repro_perturb 2` | predicted `wrong>0 -> WRONG OUTPUT` (lanes 0-15 read buffer[16] before lane 16 stored c.x, so the centroid and every cov entry are off) | n/a |

Why (SASS): every `if (lane < 16)` block of Warp::reduce is bracketed by `BSSY B0 ... BSYNC B0`, so lanes 16-31 wait for
lanes 0-15 before the next cross-lane access (L174, the next reduce's L164, L115, L141); inside the block the five steps are
straight-line. `__threadfence_block()` (L109) is `MEMBAR.SC.CTA`. Mode 1's `if (lane == 16) __nanosleep()` before the c.x
reduce is bracketed by its own BSSY/BSYNC: no wrong output can be produced this way. In mode 2 lane 16 enters the c.x reduce
through its own noinline instance (`reduce<1>`); the two calls are inside one BSSY/BSYNC that closes only after both
returned, so the instances run diverged.

`repro_fixed`: `__syncwarp()` / `__syncwarp(0xffff)` lower to `BRA.CONV` + `CALL` to a WARPSYNC stub (1 WARPSYNC, 112 CALL in
the binary); in a converged warp the stub is skipped. If cuVein still reports on `repro_fixed`, that is a detector-model gap
(see droidslam-new-1), not a residual race. The Eigen33 report groups (405 of the 657 target reports) are not exercised by
these binaries (Eigen33 is trimmed).

Results: TO BE RUN (see `../../pcl-new-1.md`).

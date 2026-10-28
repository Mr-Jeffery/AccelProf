# droidslam-new-1-2 reproducer: expected output

Build: `bash build.sh`. Compile-checked on a `normal` node (2026-10-25, CUDA 13.4): all three build. **Not run.**

Input as the target driver: 4 frames of 48x64, the 6 pairs i<j, `frame_distance_kernel<<<6, 256>>>`. Frame f is filled with
the value f+1, so every thread's total is 12*(ii[b]+1) (12 pixels per thread); a thread that read the swapped index gets
12*(jj[b]+1).

| binary | expected stdout (last line) | wrong output looks like |
|---|---|---|
| `repro` | `droidslam-new-1-2 repro: blocks=6 wrong_blocks=0 wrong_threads=0 -> output correct` (the race window is never hit without perturbation, very likely) | `block b (ii=.. jj=..): N threads read the swapped frame index`, then `-> WRONG OUTPUT` |
| `repro_fixed` | `... repro_fixed: blocks=6 wrong_blocks=0 wrong_threads=0 -> output correct` | same |
| `repro_perturb 0` | as `repro` | same |
| `repro_perturb 1` | predicted `wrong_blocks=6 wrong_threads=1344 -> WRONG OUTPUT` (all of warps 1-7, 224 threads x 6 blocks), or close to it | n/a |

Why (SASS of these builds): as in the target binary, the load of `ix` is hoisted before the pixel loop (`LDS R4, [RZ]`
right after the barrier) and thread 0's swap is `@!P1 STS.64 [RZ]` after its loop, before the `BAR.SYNC` of L654, with no
barrier between them. In mode 1 the ten `NANOSLEEP`s of warps 1-7 come before their `LDS [RZ]` (kept there by the
`asm volatile("" ::: "memory")`), while warp 0 finishes its 12 iterations and swaps within microseconds, so warps 1-7 read
`ix = jj[b]`. This is a cross-warp race and does not depend on lock-step: wrong output is expected.

cuVein: `repro` and `repro_perturb` should report the shared WAR `LDS [RZ]` (L-equivalent of droid_kernels.cu:608/611) vs
`STS.64 [RZ]` (L651), different warps of one block; `repro_fixed` should be clean (the pair is separated by the added
`BAR.SYNC`). racecheck on the target run reported 0 errors (18,591 warnings, all displayed ones intra-warp); whether racecheck
flags this pair on `repro` is to be seen.

Results: TO BE RUN (see `../../droidslam-new-1-2.md`).

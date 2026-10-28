# droidslam-new-1 reproducer: expected output

Build: `bash build.sh` (CUDA 13.4, `-arch=sm_89 -lineinfo --cudart shared -O3`). Compile-checked on a `normal` node
(2026-10-25, cuda_13.4.r13.4/compiler.38855100_0): all three build. **Not run** (no GPU there).

| binary | expected stdout (last line) | wrong output looks like |
|---|---|---|
| `repro` | `droidslam-new-1 repro: blocks=4096 wrong=0 -> output correct` | `wrong=N>0 -> WRONG OUTPUT`, with up to 5 `block b: got X expected Y` lines |
| `repro_fixed` | `droidslam-new-1 repro_fixed: blocks=4096 wrong=0 -> output correct` | same |
| `repro_perturb 0` | `... mode=0 ...: blocks=1024 wrong=0 -> output correct` (no perturbation) | same |
| `repro_perturb 1` | predicted `wrong=0 -> output correct` | `wrong>0` would mean the faithful perturbation produced a wrong sum |
| `repro_perturb 2` | predicted `wrong>0 -> WRONG OUTPUT` (likely all 1024 blocks) | n/a: this mode realizes the bad schedule on purpose |

Expected value per block b: `sum_{t<256} (t % 7 + 1 + b % 5)` = 1018 + 256*(b%5), exact in float.

Why each prediction (SASS of these builds, `cuobjdump -sass`):
- `repro`: the six warpReduce steps are straight-line LDS/LDS/FADD/STS inside `if (tid < 32)` (one BSSY/BSYNC around the
  whole call, no WARPSYNC inside); warp 0 takes the branch as a whole, so the steps execute converged. 17 LDS / 9 STS.
- `repro_perturb` mode 1: the inserted `if (tid == 16) __nanosleep(ns)` compiles to `BSSY B0; @P0 BRA; NANOSLEEP; BSYNC B0`:
  lane 16 sleeps, the other lanes wait at BSYNC, and the steps run converged after it. No wrong output can be produced this way.
- `repro_perturb` mode 2: lane 16 calls `warpReduceP<1>`, the others `warpReduceP<0>` (two noinline functions); there is no
  BSSY around the if/else, the paths rejoin only at the `WARPSYNC 0xffffffff` of the next `__syncthreads()`. While lane 16
  sleeps, the other path can run all six steps, so lane 0 reads sdata[16] before lane 16 added sdata[48]. The order in which
  the scheduler runs the two paths is not specified, so "wrong" is likely, not certain.
- `repro_fixed`: each `__syncwarp()` is lowered to `BRA.CONV ~URZ, next; MOV; CALL.REL.NOINC <stub with WARPSYNC R5>`
  (2 WARPSYNC, 12 CALL in the binary). In a converged warp `BRA.CONV` skips the call, so **no WARPSYNC executes**. The output
  is correct either way; whether cuVein reports the fixed build clean depends on how it treats this lowering (REALWORLD.md
  records the same lowering for hecbench-hungarian-1). If cuVein still reports warpReduce pairs on `repro_fixed`, that is a
  detector-model gap (bar.warp.sync in PTX, no WARPSYNC on the executed path), not a residual race.

Results: TO BE RUN (see the dossier `../../droidslam-new-1.md`).

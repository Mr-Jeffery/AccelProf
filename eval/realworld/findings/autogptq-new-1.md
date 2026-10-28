# Finding autogptq-new-1: no warp barrier between the unpack and repack phases of `gptq_repack_kernel` (intra-warp shared RAW)

Repository AutoGPTQ/AutoGPTQ, pinned commit `9f7d37072917ab3a7545835f23e808294a542153`, which equals origin HEAD. The repository was archived on 2025-04-11. Class **DR**, shared memory, intra-warp RAW, warp-synchronous, formal only (T21 corpus note 4). Triage: `eval/realworld/candidates/triage/autogptq-new-1.md`.

## 1. The accesses

| role | file:line @ 9f7d3707 | statement | SASS (traced build) |
|---|---|---|---|
| write (lane t) | `autogptq_extension/marlin/marlin_repack.cu:30` | `block[block_idx][i][offset] = v1 & 0xf;` | `STS.U8` 0x210, 0x240, 0x270, 0x2c0, 0x2f0, 0x320, 0x350, 0x380 (i = 0..7, unrolled) |
| write (lane t) | `:32` | `block[block_idx][i + 8][offset] = v2 & 0xf;` | `STS.U8` 0x3b0, 0x3e0, 0x410, 0x430, 0x440, 0x450, 0x460, 0x470 |
| read (lane t') | `:58` | `v[j] = block[i][idx[j][0]][idx[j][1]];` | 32 × `LDS.U8` 0x510–0x8d0 |

`__shared__ uint8_t block[4][16][pad_len]` (L19–L20). The launch is `<<<dim3(m/2, n/64), 32>>>` (L82–L91): one warp per block. The kernel (L8–L66) contains no `__syncthreads`, `__syncwarp` or shuffle. The SASS has no `BAR`, `WARPSYNC`, `MEMBAR`, `SHFL` or `VOTE`, only `BSSY`/`BSYNC` (convergence) around the unpack loop.

## 2. Thread pair and why nothing orders it

- **Pair.** Block (0,0): lane 0 (block_idx 0, offset 0) stores `block[0][2][0]` at L30 (i = 2). Lane 1 (srow 2, scol 0) loads `block[0][2][0]` at L58 (i = 0, j = 0).
- **Why it is a DR.** Under PTX §8.7, threads of one warp are distinct threads with no implicit ordering; independent thread scheduling, sm_70+, makes this explicit. Only `bar.warp.sync` (or a CTA barrier) orders them, and there is none. Plain vs plain: DR.
- **In practice.** Every trip count is warp-uniform: 2 `offset` iterations and constant inner loops. The warp stays converged and `BSYNC B0` (0x490) reconverges it before the loads, so the output is correct (formal only).

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/autogptq-new-1-buggy.json`, scalar-clock)

- **Reports.** 112 RACE reports, `STS.U8` × `LDS.U8`, RAW, shared, DR, `observed_distance: warp`. 56 from L30 and 56 from L32 (8 stores × 7 loads each).
- **Edges.** E.g. `1296←1040`: `intra_warp 8`.
- **Not reports.** 16 more pairs of the same shape were classed ORDERED / `barrier-ordered` in this barrier-free kernel. That is a possible detector false negative; see the triage. The race itself is reported 112 times.
- **Racecheck.** 0 errors, **1008 warnings**, all "(Warp Level Programming) Potential RAW hazard", L30/L32 vs L58. Output `mismatches=0/128` (also 0/128 natively, 3/3).

## 4. Reproducer (`eval/realworld/findings/repro/autogptq-new-1/`)

- **`repro.cu`.** `gptq_repack_kernel` L8–L66 copied (only comment and line joins changed), launched as `gptq_repack()`.
  - Trimmed: the torch includes and the libtorch host wrapper.
  - m = 64, n = 256 (grid 32×4), 50 launches, host reference (unpack all lanes, then repack).
- **`repro_fixed.cu`.** `__syncthreads()` between the phases.
  - `__syncwarp()` is equally correct under PTX. But the compile check showed ptxas 13.4 emits **no `WARPSYNC`** for `__syncwarp()` here: the instruction disappears from the SASS. A SASS-level detector would then still report the pair.
  - Because blockDim is 32, `__syncthreads()` is the same barrier and is visible as `BAR.SYNC`.
- **`repro_perturb.cu`.** `if (t >= 16) __nanosleep(100000);` at the top of each unpack iteration, so lanes 16..31 write late.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/autogptq_extension/marlin/marlin_repack.cu   (9f7d3707)
+++ b/autogptq_extension/marlin/marlin_repack.cu
@@ -34,6 +34,7 @@ __global__ void gptq_repack_kernel(
     }
   }
 
+  __syncwarp();  // the repack phase reads bytes written by other lanes
   // repack
   // ref: _get_perms @ https://github.com/IST-DASLab/marlin/blob/master/marlin/__init__.py
   uint32_t srow = (t % 4) * 2;
```

`__syncthreads()` works equally, since the kernel always runs with 32 threads.

## 6. Already known?

- **Issues and PRs** (GitHub, AutoGPTQ/AutoGPTQ, 2026-10-25):
  - Issue semantic search "marlin repack wrong result race syncwarp": 0 results.
  - PR search "marlin repack": #539 "Marlin repacking CUDA kernel" (fxmarty, merged 2024-02-14, code credited to chu-tianxiang, no review discussion, nothing on synchronization), #603, #522.
  - Web search "AutoGPTQ marlin_repack gptq_repack_kernel syncthreads race": no report. The hits are vLLM's different `gptq_marlin_repack` kernel, which uses `__syncthreads`.
  - Checked: https://github.com/AutoGPTQ/AutoGPTQ/pull/539.
- **Commits.** `git log --oneline --all -- autogptq_extension/marlin/marlin_repack.cu` lists two commits: `b206969` "fast marlin repacking" and `b7927db` "Marlin repacking CUDA kernel (#539)". The file was never changed after it was added. There is no fix.
- **Verdict.** Nothing found describes this race. **New**, as far as checked. The repository is archived, so no fix can land.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "The warp never diverges, so both phases run in lockstep; it has worked for years."
- **Answer.**
  - The PTX memory model does not give lockstep any ordering meaning. Since Volta the programming guide requires `__syncwarp()` for intra-warp shared-memory communication, so under PTX this is a data race.
  - We claim a formal race only. No wrong output is expected or claimed.
  - The perturbation test is expected to show **no** wrong output, because `BSYNC` reconverges the warp before the loads. If it stays correct, say so plainly.
  - Racecheck flags it too, as warp-level warnings.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |

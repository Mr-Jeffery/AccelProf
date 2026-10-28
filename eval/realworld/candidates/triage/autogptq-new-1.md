# Triage: autogptq-new-1 (T21c step 3)

Pinned commit: AutoGPTQ/AutoGPTQ `9f7d37072917ab3a7545835f23e808294a542153`. Route R2: `autogptq_extension/marlin/marlin_repack.cu` and `.cuh`, byte-identical (`targets/autogptq-new-1/r2/blob.check`), `#include`d by `r2/common/driver.cu`. The driver uses m = 2, n = 64, grid (1,1), 32 threads, with a host reference.
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/autogptq-new-1-buggy.json`). 1 kernel JSON (`gptq_repack_kernel`), `n_race = 112`, `n_sc = 0`. Kernel summary: `races 112, ordered 16, skipped 22`.
No rows for this id in `other_reports.csv`.

## Groups

| # | kernel | pcs | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `gptq_repack_kernel` | `STS.U8` 0x210, 0x240, 0x270, 0x2c0, 0x2f0, 0x320, 0x350, 0x380 (unrolled i = 0..7) × `LDS.U8` at L58 (7 each) | `marlin_repack.cu:30` / `:58` | 56 | **(a) DR**, intra-warp RAW, warp-synchronous | Lane t writes tile rows 0..7 of columns `t%8` and `t%8+8`. Other lanes read them in the repack phase. There is no barrier, `__syncwarp` or shuffle in the kernel. |
| 2 | `gptq_repack_kernel` | `STS.U8` 0x3b0, 0x3e0, 0x410, 0x430, 0x440, 0x450, 0x460, 0x470 × `LDS.U8` at L58 (7 each) | `:32` / `:58` | 56 | **(a) DR**, same race, rows 8..15 | The `block[block_idx][i + 8][offset]` half of the same unpack. |

Class counts: (a) 2 groups (112 reports). They form one race, with one dossier: `eval/realworld/findings/autogptq-new-1.md`. (b) 0, (c) 0, (d) 0. Not a same-value WAW.

## Reasoning

- **SASS** (traced binary).
  - The unpack loop runs from `BSSY B0` 0x020 to `BSYNC B0` 0x490: 16 `STS.U8` per iteration. The loop over `offset` is not unrolled; the back edge is at 0x480.
  - The repack phase follows: 32 `LDS.U8` 0x510–0x8d0 (L58), then `STG.E` (L64) and `EXIT`.
  - There is no `BAR`, `WARPSYNC`, `MEMBAR`, `SHFL` or `VOTE` anywhere in the kernel.
  - `BSSY`/`BSYNC` is a convergence barrier, i.e. scheduling. It is not a PTX memory-ordering operation: there is no `bar.warp.sync` in the PTX source.
- **Concrete pair.** Block (0,0), one warp: lane 0 stores `block[0][2][0]` (L30, i = 2, offset 0). Lane 1 loads `block[0][2][0]` (L58, i = 0, j = 0: srow 2, scol 0).
  - Both are plain `u8` shared accesses by different threads with no ordering, so the pair is a DR (intra-warp RAW).
  - Under independent thread scheduling (sm_70+) the lanes are not required to execute in lockstep.
- **Trace evidence.**
  - Every site verdict has `observed_distance: warp`.
  - Edges such as `1296←1040` show `intra_warp 8` (some `intra_thread 1`: a lane reading its own byte).
- **Practical effect.**
  - All trip counts are warp-uniform (2 `offset` iterations, constant inner loops), so the warp stays converged. `BSYNC` reconverges it before the loads.
  - Native runs: `mismatches=0/128` (3/3). Under racecheck: also `mismatches=0/128`.
  - Formal-only (T21 corpus note 4).
- **Racecheck** (`eval/realworld/racecheck/autogptq-new-1-buggy.txt`): 0 errors, 1008 warnings, all `(Warp Level Programming) Potential RAW hazard`. The aggregates are "Race reported between Write access at … marlin_repack.cu:30/32 and Read access at … :58". Racecheck sees the same race and classes it as warp-level.

## Non-report observation (not part of the report set; possible detector false negative)

- The kernel summary lists **16 ORDERED site verdicts with `hb_class: barrier-ordered`**, in a kernel that has no barrier at all.
  - The pairs are the loads 0x530, 0x600, 0x750, 0x850 (L58: `[R26+0xa2]`, `+0x12`, `+0x90`, `+0x0`) against four stores each, at L30 or L32.
  - Their trace edges show conflicts by other lanes (`intra_warp 7–8`), just like the 112 RACE pairs.
- By `eval/FP_DIAGNOSIS.md` §3b, "barrier-ordered" means the offline barrier-only pass found no unordered cross-thread conflict for the pair in `hb_events`.
- These four loads read tile `i = 0`, columns `scol = t/4 ∈ 0..7`, which lanes 0..7 wrote in the first unpack iteration. The writer lane t/4 is never above the reader lane t.
- Why the pass called them ordered was not checked.
- To decide it: rerun the barrier-only pass on this dump with per-pair logging, or a vector-clock run, which was skipped. If confirmed, this is a class-(c) false negative: no report is lost for the race, since 112 other pairs report it, but 16 pairs are missing.

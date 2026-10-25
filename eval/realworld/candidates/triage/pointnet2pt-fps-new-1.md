# Triage: pointnet2pt-fps-new-1 (T21c step 3)

Pinned commit: erikwijmans/Pointnet2_PyTorch `b5ceb6d9ca0467ea34beb81023f96ee82228f626`, file
`pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu` (R2 copy, blob.check PASS).
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/pointnet2pt-fps-new-1-buggy.json`), 1 kernel JSON, `n_race = 1`, `n_sc = 0`.
No rows for this id in `other_reports.csv`, `other_reports_removed.csv` or `triage_inputs.json` (checked).

## Groups

| # | kernel | pcs (a / b) | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `furthest_point_sampling_kernel<512>` | 3776 `STS` / 5824 `LDS` | `sampling_gpu.cu:112` / `:170` | 1 | **(a) DR** | WAR on `dists_i[0]`. All threads read it at L170 (iteration j). Thread 0 writes it at L112 (iteration j+1). No barrier between. Cross-warp, same block. |

Class counts: (a) 1, (b) 0, (c) 0, (d) 0. The single group is the oracle pair. There are no other reports. It is not a same-value WAW.

## Reasoning

**SASS** (built `driver`, sm_89, `-O3`):
- `STS [R3.X4+0x800]` at 0xec0 (L112), then `BAR.SYNC` at 0xed0 (L113).
- Nine reduction levels follow, each ending in a `BAR.SYNC` (L119 … L167). The last is at 0x1680.
- Then `LDS R15, [0x800]` at 0x16c0 (L170), and `BRA` at 0x16f0 back to the loop head (L89).
- No `BAR`, `MEMBAR` or `WARPSYNC` lies between 0x16c0 and the next 0xec0. Both accesses are plain, so the pair is a DR.

**Thread pair.**
- Racecheck shows Read thread (479,0,0) (warp 14) at +0x16c0 against Write thread (0,0,0) at +0xec0.
- Thread 0's path from L170 of iteration j to L112 of iteration j+1 runs through L171, the loop increment, and the distance loop L95–L110 (global memory only, with the `mag <= 1e-3` skip). It contains no `bar.sync`. There is no happens-before edge, so this is a data race under PTX §8.7.1.
- This is the record's thread pair (thread 33 vs thread 0) with a different reader warp.

**Trace evidence.**
- The reuse edge `3776 ← 5824` has `intra_block 451, intra_thread 57, intra_warp 0` (of 508).
- `hb_sync_pass [3776, 5824, 508, 2, 5824, 3776]` (field meanings not checked).

**Observable.**
- Displayed racecheck hazards (`eval/realworld/racecheck/pointnet2pt-fps-new-1-buggy.txt`, print limit 2000): WAR `R@0x16c0/W@0xec0` (1136 cross-warp errors, 68 same-warp warnings) and RAW `W@0xec0/R@0x16c0` (796).
- Under racecheck the driver's host reference check printed `mismatches=503/512`. All three native runs printed `0/512`.
- So the output is wrong under a legal schedule. The race is not formal-only.

**Benign?** No. This is the same consequence as mmcv-fps-new-1.

Finding: `eval/realworld/findings/pointnet2pt-fps-new-1.md`.

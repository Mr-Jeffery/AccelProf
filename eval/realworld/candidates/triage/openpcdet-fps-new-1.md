# Triage: openpcdet-fps-new-1 (T21c step 3)

Pinned commit: open-mmlab/OpenPCDet `233f849829b6ac19afb8af8837a0246890908755`.
Files: `pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu` (batch) and `pcdet/ops/pointnet2/pointnet2_stack/src/sampling_gpu.cu` (stack); R2 copies, blob.check PASS.
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/openpcdet-fps-new-1-buggy.json`), 3 kernel JSONs, `n_race = 3`, `n_sc = 0`.
No rows for this id in `other_reports.csv`, `other_reports_removed.csv` or `triage_inputs.json` (checked).

## Groups

| # | kernel | pcs (a / b) | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `pcdet_batch::farthest_point_sampling_kernel<1024>` | 3024 `STS` / 5296 `LDS` | batch `sampling_gpu.cu:147` / `:212` | 1 | **(a) DR** | WAR on `dists_i[0]`. All threads read it at L212 (iteration j). Thread 0 writes it at L147 (iteration j+1). No barrier in between. Cross-warp, same block. |
| 2 | `pcdet_stack::farthest_point_sampling_kernel<1024>` | 3024 `STS` / 5296 `LDS` | stack `sampling_gpu.cu:71` / `:136` | 1 | **(a) DR** | Same race in the stack file's copy of the batch kernel. |
| 3 | `pcdet_stack::stack_farthest_point_sampling_kernel<1024>` | 5856 `STS` / 8128 `LDS` | stack `sampling_gpu.cu:250` / `:315` | 1 | **(a) DR** | Same race in the stacked-batch kernel (always launched `<<<batch_size, 1024>>>`, L340). |

Class counts: (a) 3, (b) 0, (c) 0, (d) 0. All three groups are the oracle pairs. There are no other reports.
None is a same-value WAW.

## Reasoning

**SASS** (built `driver`, sm_89):
- Group 1:
  - `STS [R0.X4+0x1000]` at 0xbd0 (L147), then `BAR.SYNC` at 0xbe0 (L148).
  - Ten reduction `BAR.SYNC`s follow (L154 … L209). The last is at 0x1470.
  - Then `LDS R7, [0x1000]` at 0x14b0 (L212), and `BRA` at 0x14e0 back to the loop head (L125).
- Group 2 has the identical layout (0xbd0 L71, last BAR 0x1470 L133, LDS 0x14b0 L136).
- Group 3:
  - `STS [R18.X4+0x1000]` at 0x16e0 (L250), first BAR at 0x16f0 (L251).
  - Last BAR at 0x1f80 (L312), then `LDS R9, [0x1000]` at 0x1fc0 (L315).
  - `BRA` at 0x2000 back to the loop head (L228).
- None of the three paths from the read to the next write contains a `BAR`, `MEMBAR` or `WARPSYNC`.
- All accesses are plain `STS`/`LDS`, so each pair is a DR.

**Thread pair.**
- Racecheck gives Read thread (191,0,0) (warp 5) at +0x14b0 against Write thread (0,0,0) (warp 0) at +0xbd0, for the batch kernel.
- In general, any thread t ≥ 32 reading `dists_i[0]` at L212 in iteration j conflicts with thread 0 writing it at L147 in iteration j+1.
- Thread 0's path between the two accesses: L213–L214, the loop increment, and the distance loop L131–L145 (global loads/stores only). It contains no `bar.sync`. So there is no happens-before edge from the read to the write, and the two plain conflicting accesses race (PTX §8.7.1).
- The stack kernels behave the same way.

**Trace evidence.**
- Reuse edges `3024 ← 5296`:
  - batch `intra_block 421 / intra_thread 87` (of 508);
  - stack-batch `intra_block 102 / intra_thread 22` (of 124);
  - edge `5856 ← 8128`: stacked `intra_block 96 / intra_thread 28` (of 124).
  - `intra_warp` is 0 in all three. The previous access before thread 0's write is mostly a read from another warp.
- `hb_sync_pass` entries: `[3024, 5296, 508, 2, …]`, `[3024, 5296, 124, 2, …]`, `[5856, 8128, 124, 2, …]`. The field meanings were not checked.

**Observable.**
- In `eval/realworld/racecheck/openpcdet-fps-new-1-buggy.txt`, the displayed hazards are WAR `R@0x14b0/W@0xbd0` (1024 cross-warp errors, 20 same-warp warnings) and RAW `W@0xbd0/R@0x14b0` (956). The RAW direction is a reader that actually saw thread 0's new value.
- All 2000 displayed hazards are in `pcdet_batch::farthest_point_sampling_kernel`. The print limit hides the hazards of the two stack kernels, so their racecheck pairs are not checked.
- Under racecheck the driver's host reference check printed:
  - batch `mismatches=507/512`;
  - stack `124/128`;
  - stacked `124/128`.
- Native runs printed 0 mismatches in all three kernels, three times.
- So the race corrupts the output under a legal schedule. It is not formal-only.

**Benign?** No. This is the same consequence as mmcv-fps-new-1: a late warp computes the next iteration from a wrong reference point.

Finding: `eval/realworld/findings/openpcdet-fps-new-1.md` (one finding: three kernel copies in one repository).

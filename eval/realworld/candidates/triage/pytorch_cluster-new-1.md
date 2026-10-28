# Triage: pytorch_cluster-new-1 (T21c step 3)

Pinned commit: rusty1s/pytorch_cluster `e9a855c284b45edcbf0282cf70ac09bee0ce4e49`, file `csrc/cuda/fps_cuda.cu` (R2 copy, blob.check PASS).
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/pytorch_cluster-new-1-buggy.json`), 1 kernel JSON (`fps_kernel<float>`), `n_race = 14`, `n_sc = 0`.
No rows for this id in `other_reports.csv`, `other_reports_removed.csv` or `triage_inputs.json` (checked).
All 14 reports are on the oracle's source lines, L54/L55 and L56.

## Groups

The 14 reports are the 7 conflicting reduction steps (i = 1, 2, 4, 8, 16, 32, 64; the loop at L51 is fully unrolled), each on two arrays. I group them by source-line pair.

| # | kernel | pcs (a / b), one pair per step | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `fps_kernel<float>` | `LDS`/`STS`: 5168/5216, 5344/5392, 5520/5568, 5680/5728, 5840/5888, 6000/6048, 6160/6208 | `fps_cuda.cu:54` (read `best_dist[t+i]`) / `:55` (write `best_dist[t]`) | 7 | **(a) DR** | In step i, thread t reads slot t+i while thread t+i overwrites that slot, with no barrier between (the only barrier, L52, opens the step). |
| 2 | `fps_kernel<float>` | `LDS.64`/`STS.64`: 5200/5232, 5376/5408, 5552/5584, 5712/5744, 5872/5904, 6032/6064, 6192/6224 | `:56` (read `best_dist_idx[t+i]`) / `:56` (write `best_dist_idx[t]`) | 7 | **(a) DR** | The same race on the int64 index array. Value and index are copied by separate accesses, so the pair can tear. |

Class counts: (a) 2 groups (14 reports), (b) 0, (c) 0, (d) 0. Neither group is a same-value WAW.

Step-to-pc mapping, from the SASS offset of the `t+i` load:
- `LDS R2, [R3.X4+0x4]` at 5168 is i = 1;
- +0x8 at 5344 is i = 2;
- … +0x100 at 6160 is i = 64.

The step i = 128 (`+0x200` at 6320) has no report. That is correct: in that step only threads 0..127 write, slots 0..127, and nobody reads those slots. The readers read 128..255, which nobody writes.

## Reasoning

**SASS** for each step (built `driver`, `-O2`, sm_89), in this order:
- `BAR.SYNC` (L52);
- `LDS R0, [R3.X4]` (own slot, L54);
- `LDS R2, [R3.X4+4i]` (slot t+i, L54);
- `@!P5 LDS.64 R6, [R3.X8+0x400+8i]` (index t+i, L56);
- `@!P5 STS [R3.X4], R2` (L55);
- `@!P5 STS.64 [R3.X8+0x400], R6` (L56).

The compiler merged L55's re-load of `best_dist[t+i]` into L54's load, so the value thread t copies is the value it compared. No `WARPSYNC` appears anywhere in the loop. All accesses are plain, so each pair is a DR.

**Thread pairs.**
- **Cross-warp (i = 32, 64, and warp boundaries for smaller i).**
  - Example: step i = 64. Thread 0 (warp 0) reads `best_dist[64]` and `best_dist_idx[64]`, while thread 64 (warp 2) writes them from slot 128.
  - Racecheck shows cross-warp errors such as Read thread 30 / Write thread 32 (+0x1500/+0x1520, index array, i = 2) and Read 95 / Write 96 (+0x1430/+0x1460, i = 1).
  - Only the L52 barrier of the same step precedes both accesses, and none follows before the next step's L52. So the read and the write are unordered under PTX §8.7.1.
- **Intra-warp (i < 32, lanes t and t+i in one warp).**
  - Example: Read 161 / Write 162 at +0x1430/+0x1460 (racecheck warning).
  - PTX gives no ordering between different threads of a warp without `bar.warp.sync`, and ptxas emitted no `WARPSYNC`. So these are DR too.
  - In practice a converged warp issues all lanes' `LDS` before any lane's `STS`, so the read sees the old value.

**Trace evidence.**
- Reuse edges such as `5216 ← 5168` (`intra_warp 31486, intra_block 1142`) and `6048 ← 6000` (`intra_block 23789`, i = 32, all cross-warp) show both relations.
- `hb_sync_pass` lists all 14 pcs pairs with counts from 32628 (i = 1, value) down to 4289 (i = 64, index). Field meanings not checked.

**Benign?** Partly, and not in general.
- Reading a *newer* consistent (value, index) pair of slot t+i is harmless. The new value is the max over a superset of slots, and a strict `<` keeps the reduction correct.
- A *torn* pair is harmful: the new value with the old index. For example, thread 0 at i = 64 loads `best_dist[64]` after thread 64 stored the value from slot 128, but loads `best_dist_idx[64]` before thread 64 stored the index.
  - Then slot 0 holds the global maximum value with the index of a point whose distance is smaller.
  - At i = 128 the comparison `best_dist[0] < best_dist[128]` is false for equal values, so the wrong index survives into `out[m]`.
- The other tear (old value, new index) is corrected by a later step in the cases worked through in the dossier.

**Observable.**
- Under racecheck the driver's host reference check printed `mismatches=61/256`. All three native runs printed `0/256`. The reference uses random floats, where ties have probability ~0, and the same binary was used.
- Inference, not checked instruction by instruction: with unique maxima, consistent (untorn) reads of either the old or the new slot state give the correct argmax. A mismatch under racecheck's schedule therefore points to a torn pair.
- Displayed racecheck hazards (print limit 2000, all in steps i = 1, 2, 4): WAR mostly same-warp warnings, a few cross-warp errors, and 4 RAW `W@0x15c0/R@0x1590` errors (a reader that saw the new value).

Finding: `eval/realworld/findings/pytorch_cluster-new-1.md` (one finding, both groups).

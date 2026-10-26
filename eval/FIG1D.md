# M2 — figure 1d: one loop pair, with and without the loop's barrier

Pair: `PI-conditional_edge_neighbors_block-DAG_100n_100e`, kernel `_Z11test_kernelPiS_S_S_i`, shared RAW, `0x2a0 -> 0x280`
(`eval/results/x5/hand_checks.txt`, entry "PI / loop-carried", detail `{"loop_header":".L_x_4#0","loop_nodes":3}`).
Runtime cuVein f551ca0, harness d484e42 (job 321732, node c64, RTX 4060 Ti, CUDA 13.4, `eval/x_logs/fig1d-321732.log`).

## Variants

* Source: `eval/fig1d/src/edge_block_A.cu` is the corpus file `indigo_sources/conditional_edge_neighbors_block/conditional_edge_neighbors_block.cu` unchanged.
  `edge_block_B.cu` is A with line 65 (`__syncthreads();`, the last statement of the `for (stride ...)` body) deleted; `diff` shows that line only.
* Build: `nvcc -O3 -arch=sm_89 -lineinfo --cudart shared -ccbin /usr/bin/g++ -I indigo_include` (the recipe of `build_indigo_full.py`).
  Run: manifest row of the hand-checked id with only `id` and `exe` changed (`eval/results/fig1d/manifest_fig1d.csv`), `parallel.py run --reps 3 --timeout-cap 1200`, X1b's knobs (`BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16`).
* Corpus check: variant A's SASS equals the corpus binary's (`bin/PI/conditional_edge_neighbors_block`) except the `identifier =` lines and `code version = [9,4]` (`fig1d_A.sass.txt` vs `corpus_bin.sass.txt`, encodings stripped: 8 differing lines of 158, each an `identifier =` or `code version` line). The binaries differ by sha256 (`binaries.sha256`).
* No corpus pair has the loop-barrier variant. The corpus sibling `conditional_edge_neighbors_block_syncBug` differs from `_block` by deleting line 59 (the `__syncthreads()` before the loop), not line 65. B is therefore not a corpus program.

## The two instructions

| | pc | SASS | source (`-lineinfo`) |
|---|---|---|---|
| u (ancient) | 0x2a0 | `@!P1 STS [R9.X4], R2 ;` | `edge_block_{A,B}.cu:63` |
| v (current) | 0x280 | `@!P1 LDS R5, [R4] ;` | `edge_block_{A,B}.cu:63` |

Line 63 is `s_carry[tid] = max(s_carry[tid], s_carry[tid + stride]);`. Both instructions have the same pc in A and B; they match `hand_checks.txt` (`pair 0x2a0 -> 0x280`, `shared RAW`).
Loop (A): `0x240`–`0x2d0`, one block; `0x2b0 BAR.SYNC.DEFER_BLOCKING 0x0` (source line 65) lies between `u` and the branch `0x2d0 @P1 BRA 0x240`. In B the loop is `0x240`–`0x2c0`, with `0x2b0 ISETP.NE.AND` (line 61) and `0x2c0 @P1 BRA 0x240`; there is no BAR in it.

## Verdicts (`eval/results/fig1d/pairs.json`, `baselines-cuvein-shardfig1d0_1.csv`)

Pair `0x2a0 -> 0x280` (record: `ancient_pc` 0x2a0, `current_pc` 0x280), observed distance `block`, R1 strength `none`, contested weight 384, `conflict_class` DR, 1 kernel launch, 1 `kernel_*.json`.

| variant | mode | class (`hb_class`) | pair verdict | harness verdict, reps 1–3 | report id |
|---|---|---|---|---|---|
| A (BAR at 0x2b0) | vector-clock | barrier-ordered | ORDERED | CLEAN, CLEAN, CLEAN | none |
| A | scalar-clock | barrier-ordered | ORDERED | CLEAN, CLEAN, CLEAN | none |
| B (no BAR) | vector-clock | structural | RACE | RACE, RACE, RACE | `shared:0x280-0x2a0:RAW` (`edge_block_B.cu:63`) |
| B | scalar-clock | none recorded (`hb_class` null; harness note `classes=race:1`) | RACE | RACE, RACE, RACE | `shared:0x280-0x2a0:RAW` (`edge_block_B.cu:63`) |

The verdict differs between A and B in both modes. Each of the 12 harness rows has `rc` 0 and no timeout (cap 1200 s).

The second pair of the kernel, `0x1c0 -> 0x280` (`STS [R9.X4], R6` line 58 -> the LDS above), is ORDERED in all four (variant, mode) cells: observed distance `block`, R1 strength `block`, `hb_class` ordered (vector-clock) / null (scalar-clock). It orders through the BAR at 0x1e0, which both variants keep.

## Not established here

* The brief's loop shape is a barrier whose back edge skips it. In this kernel the BAR (0x2b0) is inside the loop block, between `u` and the back-edge branch; whether the CFG gives a path from `u` around the BAR was not checked in this task.
* Event counts differ between A and B (`events=640` vs `events=384` in the harness notes); not investigated.

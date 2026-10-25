# hecbench-hungarian-1, other reports, groups #01–#40 (part 1 of 2)

ORNL/HeCBench `src/hungarian-cuda/main.cu`. Buggy 5be7a451e091caac6eb9ca0271c529d64d757fce, fixed 44ed88e1ae1bb57411c4e83dc281d90fe7a0f553.
Build (both, `make.txt`): `nvcc -lineinfo -D_n_=64 -D_range_=64 -std=c++17 -arch=sm_89 -O3`. With n = 64, `n_threads_reduction` and `n_blocks_reduction` are both 64, `n_rows_per_block` and `n_cols_per_block` are 1, and `n_blocks_step_4` is 1.

Line numbers below are buggy-file lines unless marked "fixed". In step_2 the fixed file is shifted by +10 (buggy L281 = fixed L291). In the warp reductions the shift grows by one per inserted `__syncwarp()`.

**Result: all 40 groups (41 lines, because #40 is split) are class (a), 141 rows.**

| class | race_class | groups | rows |
|---|---|---|---|
| a | SC (PTX; reported DR, D20 (i)) | #01–#37 | 130 |
| a | DR | #38, #39, #40a, #40b | 11 |
| b, c, d | — | none | 0 |

## Evidence used

- **Sources:** `git show <commit>:src/hungarian-cuda/main.cu` from `~/incoming/realworld/HeCBench.git`. The md5s were re-checked after a scratchpad collision: buggy fd5425d4…, fixed 3d8b7e61…, group file 169d5b54….
- **Attribution:** `attrib/hecbench-hungarian-1-{buggy,fixed}.json`, `modes.*.reports[]`.
- **Thread ids:** `vector-clock/kernel_*.json` `hb_races`, scanned over every kernel JSON listed for these reports (1,074 files per build).
  - `a_tid`/`b_tid` decode as `blockIdx.x*1024 + threadIdx.x`. This matches the `loc_block` field: a_tid 33808 is block 33, thread 16.
  - The scalar-clock kernel JSONs have no `hb_races` key (only `hb_sync_pass`), so all tids come from vector-clock.
- **SASS:** `dots/main.sm_89.dot` of both builds.
- **PTX:** `cuobjdump -ptx` of both `main` binaries (CUDA 13.3), dumped on a compute node.
- **Harness:** `rw_score.py` (TOL = 2; the `known` list at L231) and `rw_attribute.py` (race_type taken from `sd.analyze` verdicts).

---

## Mechanism M1: unsynchronised warp-synchronous min reductions (groups #01–#37, 130 rows)

**Source (buggy).** Three helpers reduce shared `sdata` through a `volatile data*` parameter. Each step is `sdata[tid] = min(sdata[tid], sdata[tid + k])` for k = 32, 16, 8, 4, 2, 1, called under `if (tid < 32)`. No `__syncwarp` separates the steps. The helpers are:
- `min_in_rows_warp_reduce`: L144–L149, inlined from L177 into `calc_min_in_rows`.
- `min_in_cols_warp_reduce`: L185–L190, inlined from L222 into `calc_min_in_cols`.
- `min_warp_reduce<blockSize>`: L456–L461.
  - Via `min_reduce1`, inlined from L494 <- L533: `min_reduce_kernel1`, blockSize 64.
  - Via `min_reduce2`, inlined from L510 <- L537: `min_reduce_kernel2`, blockSize 32. This kernel skips L456.

**PTX (buggy, dumped).** Every warp-reduce access is `ld.volatile.shared.u32` / `st.volatile.shared.u32`, with no `bar.warp.sync`, `bar.sync` or `membar`/`fence` between the steps. In `calc_min_in_cols` the volatile run goes from `[%r12+128]` to `[%r12+4]`, and `min_reduce_kernel2` has the same shape.

**PTX (fixed, dumped).** The accesses are plain `ld.shared`/`st.shared`, with `bar.warp.sync -1` between consecutive steps and nothing inside a step.

**SASS (buggy, dot).** Each step is a plain `LDS [R.X4+4k]` (the load of sdata[tid+k]), then `LDS [R.X4]`, `IMNMX`, `STS [R.X4]`. The first step reuses the register copy of sdata[tid] and has no second LDS. There is no `.STRONG` token, no WARPSYNC and no BAR between the steps. A BAR sits only before the first step, and `BSYNC B0` only after the last. The reported pcs are:

| step k | cols line: LDS[+k] / STS | rows line: LDS[+k] / STS | min_reduce_kernel1 line: LDS[+k] / STS | min_reduce_kernel2 line: LDS[+k] / STS |
|---|---|---|---|---|
| 32 | L185: 0x1b0 / 0x1d0 | L144: 0x1a0 / 0x1c0 | L456: 0x380 / 0x3a0 | — |
| 16 | L186: 0x1e0 / 0x210 | L145: 0x1d0 / 0x200 | L457: 0x3b0 / 0x3e0 | L457: 0x130 / 0x150 |
| 8 | L187: 0x220 / 0x250 | L146: 0x210 / 0x240 | L458: 0x3f0 / 0x420 | L458: 0x160 / 0x190 |
| 4 | L188: 0x260 / 0x290 | L147: 0x250 / 0x280 | L459: 0x430 / 0x460 | L459: 0x1a0 / 0x1d0 |
| 2 | L189: 0x2a0 / 0x2d0 | L148: 0x290 / 0x2c0 | L460: 0x470 / 0x4a0 | L460: 0x1e0 / 0x210 |
| 1 | L190: 0x2e0 / 0x310 | L149: 0x2d0 / 0x300 | L461: 0x4b0 / 0x4e0 | L461: 0x220 / 0x250 |

**Thread relation (vector-clock `hb_races`).** All entries for these pairs have `dist = warp`, `a2_uncertain = 0` and class DR, and appear in every launch: 100 launches each of rows and cols, 387 each of min_reduce_kernel1 and min_reduce_kernel2.
- Launch configurations: `calc_min_in_rows`/`calc_min_in_cols` <<<64,64>>>, `min_reduce_kernel1` <<<64,64>>>, `min_reduce_kernel2` <<<1,32>>>. Only warp 0 of each block runs the reduction.
- `b_tid - a_tid` is constant per pair: ±k for the load of sdata[tid+k].
- The sampled address is sdata[k], at byte offset 4k.
- The per-launch `count` is 64 blocks × (32 − k) lane pairs (for example 1,024 for k = 16), or 1 × (32 − k) for min_reduce_kernel2. So every lane t < 32 − k conflicts with lane t + k (inferred from the counts).

**What orders them.** Nothing. The two accesses are in different lanes of one warp, connected only by program order within each lane. There is no `__syncwarp`/WARPSYNC, no `_sync` shuffle or vote, no barrier and no fence between them, so they are unordered under PTX. Warp lockstep is not an ordering under independent thread scheduling (warp-synchronous).

**Class (a), SC.** Both accesses are `ld/st.volatile.shared` in PTX, which is strong (relaxed, .sys scope), so each pair is an unordered morally-strong conflict, which makes it SC. cuVein labels them DR because the sm_89 SASS has plain LDS/STS without `.STRONG`. That is the D20 (i) model-boundary fact (the "DETECTED-AS-DR" outcome the oracle pair already gets).

**Three shapes:**
- **R, adjacent-step RAW.** Lane 2k stores sdata[2k] in the step with offset 2k, and lane 0 loads it as sdata[0+k] in the next step. This is the oracle race itself at other line pairs. The oracle's `buggy_expected` names these pairs (L144→L149, L185–L190, L456–L461), but `recall_pairs.json` registers only 144/145.
- **W, cross-step WAR.** Lane 0 loads sdata[k] in step k, and lane k stores sdata[k] in a later step.
- **I, intra-step WAR.** Lane 0 loads sdata[k] and lane k stores sdata[k] in the same step. This is the fixed-build residual shape.

**Fixes (one line each):**
- **F1, for R and W.** Put `__syncwarp();` between consecutive steps, which is what upstream 44ed88e did. Each lane's step-k accesses then happen-before the other lanes' later-step accesses.
- **F2, for I** (F1 does not remove it). Split each step, e.g. `int v = sdata[tid+k]; __syncwarp(); sdata[tid] = min(sdata[tid], v); __syncwarp();`. Alternatively, reduce in registers with `v = min(v, __shfl_down_sync(0xffffffff, v, k));`.

**Fixed build.**
- R and W pairs: absent. In the fixed attribution, these kernels have only same-line intra-step pairs.
- I pairs: present as plain DRs in groups #53–#57 (cols), #58–#60 (rows) and #61–#65 (min_warp_reduce). The fixed rows lines L146/L148 are matched by the registered residual instead.

**Why these groups are "other" (fact, from `rw_score.py`).**
- The known pairs are the primary 144/145 and the fixed residual 146/146, each with ±2 lines. They are applied to buggy reports too: `known = pairs + both_builds + fx_all(spec)`, L231.
- So buggy rows pairs with both lines in L144–L148 were absorbed. Some, such as 145/148, are absorbed only by the fixed-file residual, whose L146 is a different statement from buggy L146.
- That leaves only the L149 pairs (#17–#21) from rows. No cols or min_warp_reduce line falls inside a window.

**Impact (inferred from the min semantics, not run).**
- R pairs can make lane 0 read a stale value and drop inputs. That is the upstream bug.
- W and I pairs can only make a lane read a value that is already the min over more valid inputs. For rows, cols and min_reduce_kernel1 they cannot change the result.
- Exception (source observation, outside the reports): `min_reduce_kernel2` is launched with 32 threads and 128 bytes of dynamic shared memory (main.cu:618), yet `min_warp_reduce<32>` at L457 reads sdata[tid+16] up to sdata[47]. Lanes 16–31 therefore read past the allocation, and a W or I reordering there could propagate that value into sdata[0]. memcheck was not run.

### Per-group table, M1

Lanes are lanes of warp 0 in every block. The vector-clock sample is from block 33 for rows, cols and min_reduce_kernel1, and block 0 for min_reduce_kernel2. "→" marks the first and second access of the `hb_races` entry. All entries have dist warp. All groups are class (a), SC, high confidence.

| group | rows | kernel(s) | pcs | access A (first) | access B (second) | addr | shape | fix | fixed build |
|---|---|---|---|---|---|---|---|---|---|
| #01 | 2 | calc_min_in_cols | 0x1d0→0x1e0 | L185 STS sdata[16], lane 16 (a_tid 33808) | L186 LDS sdata[0+16], lane 0 (b_tid 33792) | sdata[16] | R | F1 | no |
| #02 | 2 | calc_min_in_cols | 0x1e0→0x210 | L186 LDS sdata[16], lane 0 | L186 STS sdata[16], lane 16 | sdata[16] | I | F2 | yes, fixed L192 (#53) |
| #03 | 4 | calc_min_in_cols | 0x1e0→0x250; 0x210→0x220 | L186 LDS lane 0; L186 STS lane 8 | L187 STS lane 16; L187 LDS lane 0 | sdata[16]; sdata[8] | W + R | F1 | no |
| #04 | 2 | calc_min_in_cols | 0x1e0→0x290 | L186 LDS lane 0 | L188 STS lane 16 | sdata[16] | W | F1 | no |
| #05 | 2 | calc_min_in_cols | 0x1e0→0x2d0 | L186 LDS lane 0 | L189 STS lane 16 | sdata[16] | W | F1 | no |
| #06 | 2 | calc_min_in_cols | 0x1e0→0x310 | L186 LDS lane 0 | L190 STS lane 16 | sdata[16] | W | F1 | no |
| #07 | 2 | calc_min_in_cols | 0x220→0x250 | L187 LDS lane 0 | L187 STS lane 8 | sdata[8] | I | F2 | yes, fixed L194 (#54) |
| #08 | 4 | calc_min_in_cols | 0x220→0x290; 0x250→0x260 | L187 LDS lane 0; L187 STS lane 4 | L188 STS lane 8; L188 LDS lane 0 | sdata[8]; sdata[4] | W + R | F1 | no |
| #09 | 2 | calc_min_in_cols | 0x220→0x2d0 | L187 LDS lane 0 | L189 STS lane 8 | sdata[8] | W | F1 | no |
| #10 | 2 | calc_min_in_cols | 0x220→0x310 | L187 LDS lane 0 | L190 STS lane 8 | sdata[8] | W | F1 | no |
| #11 | 2 | calc_min_in_cols | 0x260→0x290 | L188 LDS lane 0 | L188 STS lane 4 | sdata[4] | I | F2 | yes, fixed L196 (#55) |
| #12 | 4 | calc_min_in_cols | 0x260→0x2d0; 0x290→0x2a0 | L188 LDS lane 0; L188 STS lane 2 | L189 STS lane 4; L189 LDS lane 0 | sdata[4]; sdata[2] | W + R | F1 | no |
| #13 | 2 | calc_min_in_cols | 0x260→0x310 | L188 LDS lane 0 | L190 STS lane 4 | sdata[4] | W | F1 | no |
| #14 | 2 | calc_min_in_cols | 0x2a0→0x2d0 | L189 LDS lane 0 | L189 STS lane 2 | sdata[2] | I | F2 | yes, fixed L198 (#56) |
| #15 | 4 | calc_min_in_cols | 0x2a0→0x310; 0x2d0→0x2e0 | L189 LDS lane 0; L189 STS lane 1 | L190 STS lane 2; L190 LDS lane 0 | sdata[2]; sdata[1] | W + R | F1 | no |
| #16 | 2 | calc_min_in_cols | 0x2e0→0x310 | L190 LDS lane 0 | L190 STS lane 1 | sdata[1] | I | F2 | yes, fixed L200 (#57) |
| #17 | 2 | calc_min_in_rows | 0x1d0→0x300 | L145 LDS lane 0 | L149 STS lane 16 | sdata[16] | W | F1 | no |
| #18 | 2 | calc_min_in_rows | 0x210→0x300 | L146 LDS lane 0 | L149 STS lane 8 | sdata[8] | W | F1 | no |
| #19 | 2 | calc_min_in_rows | 0x250→0x300 | L147 LDS lane 0 | L149 STS lane 4 | sdata[4] | W | F1 | no |
| #20 | 4 | calc_min_in_rows | 0x290→0x300; 0x2c0→0x2d0 | L148 LDS lane 0; L148 STS lane 1 | L149 STS lane 2; L149 LDS lane 0 | sdata[2]; sdata[1] | W + R | F1 | no |
| #21 | 2 | calc_min_in_rows | 0x2d0→0x300 | L149 LDS lane 0 | L149 STS lane 1 | sdata[1] | I | F2 | yes, fixed L154 (#60) |
| #22 | 2 | min_reduce_kernel1 | 0x3a0→0x3b0 | L456 STS lane 16 | L457 LDS lane 0 | sdata[16] | R | F1 | no |
| #23 | 4 | k1; k2 | 0x3b0→0x3e0; 0x130→0x150 | L457 LDS lane 0 | L457 STS lane 16 | sdata[16] | I | F2 | yes, fixed L468 (#61) |
| #24 | 8 | k1; k2 | k1 0x3b0→0x420, 0x3e0→0x3f0; k2 0x130→0x190, 0x150→0x160 | L457 LDS lane 0; L457 STS lane 8 | L458 STS lane 16; L458 LDS lane 0 | sdata[16]; sdata[8] | W + R | F1 | no |
| #25 | 4 | k1; k2 | 0x3b0→0x460; 0x130→0x1d0 | L457 LDS lane 0 | L459 STS lane 16 | sdata[16] | W | F1 | no |
| #26 | 4 | k1; k2 | 0x3b0→0x4a0; 0x130→0x210 | L457 LDS lane 0 | L460 STS lane 16 | sdata[16] | W | F1 | no |
| #27 | 4 | k1; k2 | 0x3b0→0x4e0; 0x130→0x250 | L457 LDS lane 0 | L461 STS lane 16 | sdata[16] | W | F1 | no |
| #28 | 4 | k1; k2 | 0x3f0→0x420; 0x160→0x190 | L458 LDS lane 0 | L458 STS lane 8 | sdata[8] | I | F2 | yes, fixed L470 (#62) |
| #29 | 8 | k1; k2 | k1 0x3f0→0x460, 0x420→0x430; k2 0x160→0x1d0, 0x190→0x1a0 | L458 LDS lane 0; L458 STS lane 4 | L459 STS lane 8; L459 LDS lane 0 | sdata[8]; sdata[4] | W + R | F1 | no |
| #30 | 4 | k1; k2 | 0x3f0→0x4a0; 0x160→0x210 | L458 LDS lane 0 | L460 STS lane 8 | sdata[8] | W | F1 | no |
| #31 | 4 | k1; k2 | 0x3f0→0x4e0; 0x160→0x250 | L458 LDS lane 0 | L461 STS lane 8 | sdata[8] | W | F1 | no |
| #32 | 4 | k1; k2 | 0x430→0x460; 0x1a0→0x1d0 | L459 LDS lane 0 | L459 STS lane 4 | sdata[4] | I | F2 | yes, fixed L472 (#63) |
| #33 | 8 | k1; k2 | k1 0x430→0x4a0, 0x460→0x470; k2 0x1a0→0x210, 0x1d0→0x1e0 | L459 LDS lane 0; L459 STS lane 2 | L460 STS lane 4; L460 LDS lane 0 | sdata[4]; sdata[2] | W + R | F1 | no |
| #34 | 4 | k1; k2 | 0x430→0x4e0; 0x1a0→0x250 | L459 LDS lane 0 | L461 STS lane 4 | sdata[4] | W | F1 | no |
| #35 | 4 | k1; k2 | 0x470→0x4a0; 0x1e0→0x210 | L460 LDS lane 0 | L460 STS lane 2 | sdata[2] | I | F2 | yes, fixed L474 (#64) |
| #36 | 8 | k1; k2 | k1 0x470→0x4e0, 0x4a0→0x4b0; k2 0x1e0→0x250, 0x210→0x220 | L460 LDS lane 0; L460 STS lane 1 | L461 STS lane 2; L461 LDS lane 0 | sdata[2]; sdata[1] | W + R | F1 | no |
| #37 | 4 | k1; k2 | 0x4b0→0x4e0; 0x220→0x250 | L461 LDS lane 0 | L461 STS lane 1 | sdata[1] | I | F2 | yes, fixed L476 (#65) |

(k1 = min_reduce_kernel1 <- main.cu:494 <- 533, k2 = min_reduce_kernel2 <- main.cu:510 <- 537; the rows and cols frames are `<- main.cu:177` and `<- main.cu:222`.)

Each group's rows split evenly between buggy vector-clock and buggy scalar-clock, with one row per pc pair per mode. The scalar-clock rows are the same pc pairs; their tids are not recorded. No member of any group differs in mechanism, so no M1 group is split.

**Concrete thread pair, for example #01.** Thread 16 and thread 0 of block 33 (warp 0) in `calc_min_in_cols`. Thread 16 executes the L185 store `sdata[16] = min(sdata[16], sdata[48])`, and thread 0 executes the L186 load `sdata[0+16]`. There is no `__syncwarp` between them.

---

## Mechanism M2: step_2 racy cover_row / cover_column claim (groups #38–#40, 11 rows)

**Source (buggy L270–L299; fixed L280–L309, unchanged except +10).** `step_2` is launched as one block, with blockDim = zeros_size (106–135 in the recordings, grid 1). Each thread takes one zero `z` and computes `l = z & row_mask` and `c = z >> log2_n`. It then does the following:
- L281: `if (cover_row[l] == 0 && cover_column[c] == 0)`, a plain pre-check.
- L283: `if (!atomicExch(&cover_row[l], 1))` claims the row.
- L285: `if (!atomicExch(&cover_column[c], 1))` claims the column, and on success writes the star.
- L291: otherwise `cover_row[l] = 0;`, a plain release, followed by `repeat = true` (L292–L293).

`__syncthreads()` appears only at the top of the `do` loop (L271, L273) and after the `for` loop (L298).

**PTX (dumped, both builds).** The pre-check is `ld.global.u32`, which is weak. The claims are `atom.global.exch.b32`, with no `.sem`, which means relaxed at gpu scope. The release is `st.global.u32`, also weak. There is no `membar`/`fence`.

**SASS (dot, both builds identical).**
- 0x170 `LDG.E` cover_row[l]
- 0x200 `LDG.E` cover_column[c]
- 0x240 `ATOMG.E.EXCH.STRONG.GPU` cover_row[l]
- 0x270 `ATOMG.E.EXCH.STRONG.GPU` cover_column[c]
- 0x2d0 `@P2 STG.E [R4.64], RZ` (cover_row[l] = 0)

There is no MEMBAR and no BAR between 0x0b0 and 0x380.

**What orders them.** Nothing within one do-iteration. The two threads handle different zeros in the same row (or column) between the same pair of barriers. The atomics are relaxed, there is no fence, and nothing reads a flag with acquire. So every pair below has at least one weak access and no happens-before relation, which makes it a DR (class (a)). The BARs order accesses only across do-iterations.

### #38: main.cu:281 vs device_atomic_functions.hpp:127 <- main.cu:283 / :285 (4 rows: buggy vector-clock 2, scalar-clock 2)

- **Accesses:**
  - A: L281 `LDG.E` (0x170 for cover_row[l], 0x200 for cover_column[c]), global, plain.
  - B: `atomicExch` (hpp:127, inlined at L283 for 0x240 and L285 for 0x270), `ATOMG.E.EXCH.STRONG.GPU`, global.
- **Threads (vector-clock, buggy, 100 launches).** There are 200 entries per pc pair over the 100 launches: 100 with dist warp and 100 with dist block. Samples:
  - 0x170→0x240: t43 (w1 l11) loads, t32 (w1 l0) exchanges (same warp); t69 (w2) vs t96 (w3) (cross-warp).
  - 0x200→0x270: t108 (w3) vs t107 (w3); t70 (w2) vs t114 (w3).
  - `a2_uncertain` is 0 in all entries.
- **Order:** none (see above).
- **Class (a), DR, high confidence.** A weak load conflicts with another thread's atomic RMW.
- **Fix:** make the pre-check strong, e.g. `cuda::atomic_ref<int, cuda::thread_scope_device>(cover_row[l]).load(cuda::memory_order_relaxed)`, and the same for cover_column[c]. Alternatively, drop the pre-check, since the atomicExch already decides.
- **Fixed build:** same pair (fixed L291 vs L293/L295). These are the 4 rows of #40b.
- **Label note.** The attribution and the CSV say RAW, while every `hb_races` entry has the load first (kind WAR). The `race_type` comes from the pc-dependency verdict (`rw_attribute.py:247`). In the edges of 40 sampled launches both directions are observed (ancient 0x240 → current 0x170, and ancient 0x170 → current 0x240), so the label is one observed order, not an error.

### #39: main.cu:281 vs main.cu:291 (2 rows: buggy vector-clock 1, scalar-clock 1)

- **Accesses:**
  - A: L281 `LDG.E` cover_row[l] (0x170), plain.
  - B: L291 `STG.E` cover_row[l] = 0 (0x2d0), plain.
  - Both global.
- **Threads (vector-clock).** 198 entries: dist block in 100, dist warp in 98. Samples: t38 (w1 l6) loads, t5 (w0 l5) stores 0 (cross-warp); t88 (w2) vs t77 (w2) (same warp).
- **Order:** none within the do-iteration.
- **Class (a), DR, high confidence.** Both accesses are weak.
- **Fix:** `atomicExch(&cover_row[l], 0);` at L291, plus a strong pre-check as in #38.
- **Fixed build:** yes, fixed L291/L301, group #66 (fixed vector-clock and scalar-clock).
- The race_type label is RAW, against WAR in `hb_races`, for the same reason as #38. The edges also show ancient 0x2d0 → current 0x170.

### #40: device_atomic_functions.hpp:127 vs main.cu:291 (5 rows). Split: this group key merges two different code pairs because fixed line numbers are shifted by 10.

- **#40a (1 row, buggy vector-clock):**
  - Accesses: A `atomicExch(&cover_row[l],1)` at hpp:127 <- L283 (0x240, `ATOMG.E.EXCH.STRONG.GPU`); B L291 `cover_row[l] = 0` (0x2d0, `STG.E`, plain); global, WAW.
  - Threads (vector-clock, 197 entries, block 100 / warp 97): t38 (w1) exchanges, t5 (w0) later stores 0; t88/t77 (w2) same warp.
  - Order: none. Thread t5 won the row with its own exchange and then releases it with a plain store. Thread t38's exchange read t5's atomic value, which gives no happens-before to t5's store.
  - **Class (a), DR, high confidence.** A plain store conflicts with an atomic.
  - Fix: `atomicExch(&cover_row[l], 0);` at L291.
  - Fixed build: yes, group #67 (fixed vector-clock only). Neither build's scalar-clock attribution has this pc pair. That is a fact; the cause (the separate recording's interleaving, or the mode) was not checked.
- **#40b (4 rows, fixed vector-clock 2, scalar-clock 2):**
  - These are fixed L291 `LDG.E` vs `atomicExch` at hpp:127 <- fixed L293 / L295 (0x170/0x240, 0x200/0x270).
  - Same mechanism, classification and fix as #38: fixed vector-clock samples t36 (w1) vs t0 (w0), and t102 (w3) vs t104 (w3); 200 entries, warp and block.
  - **Class (a), DR, high confidence.**
  - Present in both builds; the buggy counterpart is #38.

---

## Defects

No class (c) group in #01–#40. The following harness observations do not change any class above:

1. **Fixed-build residual spec applied to buggy reports by line number.** In `rw_score.py` L231, `known = spec["pairs"] + both_builds + fx_all(spec)` has no variant condition. That it is applied to the buggy build is inferred from this code and confirmed by the missing 145/148 report.
   - The residual `fixed L146` (±2 lines) therefore also "explains" buggy `calc_min_in_rows` pairs at L144–L148. Buggy L146 is the k = 8 statement, not the fixed file's k = 16 statement.
   - Example: buggy 0x1d0/0x2c0 (L145/L148) is in the buggy attribution and matches only the residual window, so it is absent from `other_reports.csv`.
   - Effect: these buggy reports are counted as explained by a fixed-file pair. They are the same M1 mechanism, so nothing is lost for triage.
2. **`groups.csv` keys on (target, line pair) across builds.** Fixed and buggy reports with coincident line numbers but different code are merged, as in #40 (split above).
3. **Scalar-clock kernel JSONs carry no `hb_races`.** Thread ids are available only for vector-clock. The rows in this share are the same pc pairs in both modes, except #40a, which is vector-clock only.

## Not done

- No GPU runs.
- memcheck was not run for the `min_reduce_kernel2` out-of-bounds read noted under M1.
- The cause of the vector-clock-only #40a pair was not investigated.

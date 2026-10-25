# hecbench-hungarian-1, other reports, groups #41-#79 (T21c step 3, part 2)

Repo ORNL/HeCBench, `src/hungarian-cuda/main.cu`. Buggy 5be7a451e091caac6eb9ca0271c529d64d757fce, fixed 44ed88e1ae1bb57411c4e83dc281d90fe7a0f553. Build: the app's Makefile, `-O3 -arch=sm_89 -lineinfo -D_n_=64 -D_range_=64` (n=64, n_tests=100). The oracle race (warp-synchronous `volatile` min-reduce) is not what these groups are.

39 groups, 1,878 rows (buggy #41-#52: 915 rows, fixed #53-#79: 963 rows). Every group is class (a): 31 DR groups with 904 rows, 8 SC groups with 974 rows. No class (b), (c) or (d) groups.

## Evidence used

- **Source.** `git show <commit>:src/hungarian-cuda/main.cu` from `~/incoming/realworld/HeCBench.git`. The local copies' md5 matches ARC: buggy fd5425d4..., fixed 3d8b7e61....
- **SASS.** `dots/main.sm_89.dot` of both stores, md5 checked against BeeGFS.
  - `step_2`, `step_4`, `step_5a` and `step_5b` are instruction-for-instruction identical in buggy and fixed, apart from branch-label numbers (checked with `diff`).
  - So every buggy group #41-#52 has a fixed twin at the same pcs, shifted +10 source lines: #41<->#68, #42<->#69, #43<->#70, #44<->#71, #45<->#72, #46<->#73, #47<->#74, #48<->#75, #49<->#76, #50<->#77, #51<->#78, #52<->#79.
- **Thread relation.** `hb_races` of the vector-clock kernel JSONs (`realworld-2026-10/hecbench-hungarian-1-{buggy,fixed}/vector-clock/`).
  - Up to 6 pc pairs per group, 2 kernel instances each. For #66/#67, all 100 instances.
  - `a2_uncertain` was 0 in every record sampled.
- **Launch shapes** (from the kernel JSONs):
  - `step_2` and `step_4`: grid 1, block = min(zeros_size, 256), observed 109-151 threads. That is one block, several warps.
  - `step_5a` and `step_5b`: 1x64.
  - `calc_min_in_rows` and `calc_min_in_cols`: 64x64.
  - `min_reduce_kernel1`: 64x64. `min_reduce_kernel2`: 1x32.
- **Thread ids.** For the 64-block kernels, a_tid/b_tid are printed as block*1024+threadIdx (e.g. 31744 = block 31, thread 0). The block number matches `loc_block`.
- **Shared-flag layout, from SASS:**
  - `step_4`: `[0x0]` s_found, `[0x1]` s_goto_5, `[0x2]` s_repeat_kernel. Thread 0 initialises them at 0x070/0x080/0x0a0.
  - `step_2`: `[0x0]` repeat, `[0x1]` s_repeat_kernel.
- **Global arrays, from the SASS address arithmetic** (constant bank c[0x4]):
  - +0x38 cover_row; +0x40 cover_column; +0x48 column_of_prime_at_row; +0x30 column_of_star_at_row.
  - +0x28 row_of_star_at_column; +0x50 row_of_green_at_column.
  - The trace addresses agree with this: cover_row, cover_column and column_of_prime_at_row occupy consecutive 256-byte ranges.

## Mechanisms

### M1. step_2 shared bool flags, same-value WAW (#41, #42, #68, #69)

- **Source** (buggy L292/L293, fixed L302/L303): `repeat = true; s_repeat_kernel = true;` in the `else` branch taken when a thread won `atomicExch(&cover_row[l],1)` but lost `atomicExch(&cover_column[c],1)`.
- **SASS:** `@P2 STS.U8 [RZ]` at 0x320 and `@P2 STS.U8 [0x1]` at 0x340. These are plain `__shared__ bool` stores, every writer storing 1.
- **Ordering:** `__syncthreads` sits only at the top of the do-loop (BAR 0x080/0x0a0) and after the for-loop (BAR 0x390). All writers of one iteration are in the same barrier interval, and nothing orders them.
- **Class (a) DR, same-value.**

### M2. step_2 `repeat_kernel = true` by every thread (#43, #70)

- **Source** (buggy L301, fixed L311): `if (s_repeat_kernel) repeat_kernel = true;` with no `i == 0` guard. `repeat_kernel` is a `__managed__ __device__ bool`.
- **SASS:** `STG.E.U8` at 0x430, executed by every thread of the block after the final BAR.
- **Class (a) DR, same-value, plain WAW.** `step_4` guards the same store with `i == 0` (buggy L389, fixed L399).

### M3. step_2 row release `cover_row[l] = 0` is a plain store (#66, #67; fixed only)

- **Source** (fixed): L291 `if (cover_row[l] == 0 && cover_column[c] == 0)` is a plain load (LDG.E 0x170). L293 `atomicExch(&cover_row[l],1)` is ATOMG.E.EXCH.STRONG.GPU at 0x240. L301 `cover_row[l] = 0;` is a plain STG.E at 0x2d0.
- **Ordering:** a thread X that won the row exchange but lost the column exchange releases the row with the plain store. Another thread Y tests the row with a plain load and exchanges it. Nothing orders X's store with Y's load or with Y's exchange: the exchanges are relaxed `.gpu` RMWs with no fence, and the next BAR comes only after the for-loop.
- **Class (a) DR.** The store is weak, and in #66 both accesses are weak.
- **Buggy twins:** the same pair in the buggy build is #39 (L281 vs L291) and the buggy row of #40. Both belong to the part-1 share.

### M4. step_4 volatile cover flags: unordered strong conflicts (#44, #45, #49, #50, #71, #72, #76, #77)

- **Source.** In `step_4`, `v_cover_row` and `v_cover_column` are `volatile int*` to global memory:
  - L370 (fixed L380): `if (!v_cover_column[c] && !v_cover_row[l])`.
  - L375 (fixed L385): `v_cover_row[l] = 1;`, then L376 (fixed L386): `__threadfence();`, then L377 (fixed L387): `v_cover_column[c1] = 0;`.
- **SASS.** The inner `for n<10` is fully unrolled into 10 copies, 0x150 apart. Copy 0 is:
  - 0x190 `LDG.E.STRONG.SYS` cover_column[c];
  - 0x250 `LDG.E.STRONG.SYS` cover_row[l];
  - 0x300 `STG.E.STRONG.SYS` cover_row[l]=1;
  - 0x310 `MEMBAR.SC.GPU`, ERRBAR, CCTL.IVALL;
  - 0x340 `STG.E.STRONG.SYS` cover_column[c1]=0.
  - All four accesses are strong at system scope, a scope that covers both threads (same block).
- **What orders them, or fails to.**
  - The only barriers are at the top (0x090, 0x0b0) and bottom (0xf90) of the do-loop. Every reported pair is between two threads inside one barrier interval.
  - The fence lies between the writer's own two stores. It can order other accesses only through an observed release/acquire chain. It never orders a flag access against the other thread's access to the same flag, which is exactly the communication.
  - No `__syncwarp`, shuffle or vote is used.
  - The pairs are therefore really unordered.
- **Class (a) SC.** These are unordered strong conflicts, not data races under PTX.
- **The four buggy groups:**
  - **#44:** cover_column load (L370) vs `cover_column[c1]=0` (L377). WAR and RAW.
  - **#45:** cover_row load (L370) vs `cover_row[l]=1` (L375).
  - **#49:** WAW `cover_row[l]=1`, same value. Two threads with zeros in the same row.
  - **#50:** WAW `cover_column[c1]=0`, same value. c1 = column_of_star_at_row[l], and stars are a matching, so the two threads share row l.
- **Same threads across groups.** The same tid pairs (e.g. 10/57 and 99/105 in buggy kernel_11) appear in #46, #49 and #50. This is consistent with two threads entering the L371-L377 body for the same row in one interval. Inferred from the matching tids and addresses.

### M5. step_4 `column_of_prime_at_row[l] = c` (#46, #73)

- **Source** (buggy L372, fixed L382): a plain `STG.E` (0x2a0 + 0x150k), executed by every thread whose zero (l,c) passed the L370 test in the same interval.
- **Values:** two different zeros in the same row have different c, so the two writes carry different values. This is a fact from the source: each j indexes a distinct zero from `compress_matrix`.
- **Ordering:** the same as M4. The writer's later strong store `cover_row[l]=1` comes after the plain store, with no fence before it. So it is not a release that covers the plain store.
- **Class (a) DR, different-value WAW.**

### M6. step_4 shared bool flags, same-value WAW (#47, #48, #74, #75)

- **Source** (buggy L371, fixed L381): `s_found = true; s_repeat_kernel = true;`.
  - SASS: STS.U8 [0x0] at 0x2b0 + 0x150k and STS.U8 [0x2] at 0x2c0 + 0x150k.
  - Each of #47 and #74 splits 110 rows s_found + 110 rows s_repeat_kernel. The split is by address only; the mechanism is the same, so the group is not split.
- **Source** (buggy L380, fixed L390): `s_goto_5 = true;`, SASS `@!P1 STS.U8 [0x1]` at 0x2d0 + 0x150k. All 99 rows of #48 and 100 rows of #75 are this store.
- **Ordering:** many threads in one barrier interval write 1 to the same plain `__shared__ bool`.
- **Class (a) DR, same-value.** Thread 0's `s_found = false` (L358/L368) is barrier-separated and not part of these pairs.

### M7. step_5a joining paths (#51, #78)

- **Source:**
  - Buggy L412 / fixed L422: `row_of_green_at_column[c_Z0] = i;`. SASS 0x120 `STG.E [green + c_Z0*4], R7`, where R7 = i.
  - Buggy L416 / fixed L426: the loop store `row_of_green_at_column[c_Z0] = r_Z0;`. SASS 0x1b0.
  - cuVein's frame for 0x120 says L416/L426. By its operands, though, 0x120 is the pre-loop L412/L422 store. Why the line table reports L416 was not checked.
- **Pairs:**
  - Two threads whose rows have primes in the same column write their own row index there (0x120/0x120, e.g. tids 1 and 30). These are different values.
  - The other pairs are a pre-loop store vs another path's loop store (0x120/0x1b0, tids 36/6), and two loop stores (0x1b0/0x1b0).
  - After two paths join they read only arrays that `step_5a` does not write, so the later stores carry the same value (inferred from the source).
- **Class (a) DR**, plain WAW in one kernel with no synchronization. The kernel's comment "Eliminates joining paths" shows the last-writer-wins race is intended.

### M8. step_5b `row_of_star_at_column` check vs path update (#52, #79)

- **Source:**
  - Buggy L430 / fixed L440: thread j reads `row_of_star_at_column[j] < 0`, a plain `LDG.E` at 0xd0.
  - Buggy L444 / fixed L454: another thread's alternating path writes `row_of_star_at_column[c_Z0] = r_Z0` with c_Z0 = j, a plain `STG.E` at 0x1c0.
- **Ordering:** nothing between them; there is no barrier in the kernel.
- **Class (a) DR.**
- **Inferred:** column j lies on the path only if it held a star, so the old value is >= 0. The new value r_Z0 is also >= 0. The reader therefore exits either way and the outcome is value-benign.

### M9. fixed warp reduce: intra-step read/write (#53-#65)

- **Source** (fixed): each step is `sdata[tid] = min(sdata[tid], sdata[tid + k]);`, with `__syncwarp()` only between steps.
  - rows: L146 +16, L148 +8, L150 +4, L152 +2, L154 +1.
  - cols: L190 +32, L192 +16, L194 +8, L196 +4, L198 +2, L200 +1.
  - min_warp_reduce: L466 +32, L468 +16, L470 +8, L472 +4, L474 +2, L476 +1.
- **SASS:** per step `LDS [R.X4+4k]; LDS [R.X4]; IMNMX; STS [R.X4]`, then `BRA.CONV` + `CALL` to the `__cuda_sm70_warpsync` stub (WARPSYNC R4). There is no WARPSYNC between a step's LDS and its STS.
- **Pair:** lane t loads sdata[t+k] while lane t+k stores sdata[t+k] in the same step. These are plain shared accesses in the same warp, unordered.
- **Class (a) DR, warp-synchronous.** Under independent thread scheduling, lane t may read lane t+k's new value. For a min-reduction that is value-benign (inferred).
- **Already scored, not re-triaged (#53, #61).**
  - #53 (cols L192) and #61 (min_warp_reduce L468) are the +16 steps, i.e. the "parallel col/min_warp_reduce steps" of the already-scored residual.
  - They landed here because `eval/realworld/recall_pairs.json` registers only `main.cu:146 vs 146` as the fixed residual. `oracle/hecbench-hungarian-1.json` `fixed.reason` names L146-L154 "and the same lines of the other two functions".
  - The other steps (#54-#60, #62-#65) have the same mechanism with k = 8, 4, 2, 1, and are not in the registered residual either.
- **Buggy builds:** the buggy build has the same intra-step pairs (part-1 groups #02, #07, #11, #14, #16, #21, #23, #28, #32, #35, #37). The fix did not remove them.

## Per group

The notation is `kernel_N`: tid A (pc) vs tid B (pc), dist, kind, count. Unless stated otherwise, the thread pairs are vector-clock `hb_races` records in buggy kernel_6 for `step_2` and kernel_11 for `step_4` (block 127).

### Buggy groups #41-#52

#### #41: main.cu:292 vs 292 (2 rows, buggy)

- **Accesses:** `repeat = true`, STS.U8 shared [0x0] at 0x320, both sides.
- **Threads:** kernel_6: tid 5 vs 9, warp, WAW, count 23; tid 5 vs 45, block, count 82.
- **Ordering and class:** M1. (a) DR, same-value.
- **Fix:** make `repeat` an int and set it with `atomicExch(&repeat, 1)`, or store it through a relaxed `cuda::atomic_ref<bool, cuda::thread_scope_block>`.
- **Fixed build:** yes, #68.

#### #42: main.cu:293 vs 293 (2 rows, buggy)

- **Accesses:** `s_repeat_kernel = true`, STS.U8 shared [0x1] at 0x340.
- **Threads:** kernel_6: tid 5 vs 9, warp, count 23; tid 5 vs 45, block, count 82.
- **Ordering and class:** M1. (a) DR, same-value.
- **Fix:** an atomic or relaxed atomic_ref store, as for #41.
- **Fixed build:** yes, #69.

#### #43: main.cu:301 vs 301 (2 rows, buggy)

- **Accesses:** `repeat_kernel = true`, STG.E.U8 to global (managed) at 0x430.
- **Threads:** kernel_6: tid 0 vs 1, warp, count 1953; tid 0 vs 32, block, count 6048.
- **Ordering and class:** M2. (a) DR, same-value.
- **Fix:** `if (i == 0 && s_repeat_kernel) repeat_kernel = true;`.
- **Fixed build:** yes, #70.

#### #44: main.cu:370 vs 377 (175 rows, buggy; 88 pc pairs)

- **Accesses:** LDG.E.STRONG.SYS `v_cover_column[c]` (0x190, 0x360 + 0x150k, ...) vs STG.E.STRONG.SYS `v_cover_column[c1]=0` (0x340 + 0x150k), global.
- **Threads:**
  - kernel_11: tid 7 (0x190) vs 10 (0x340), warp, WAR, count 12; tid 19 vs 65, block, count 22.
  - kernel_47: tid 72 (STG 0x880) vs 118 (LDG 0x8a0), block, RAW, count 9.
- **Ordering and class:** M4. (a) SC, really unordered.
- **Fix:** none is needed for PTX race freedom. Making the accesses `cuda::atomic_ref` relaxed would still leave an SC. Only separating the test and update phases with `__syncthreads()` would order them, and that changes the algorithm.
- **Fixed build:** yes, #71.

#### #45: main.cu:370 vs 375 (173 rows, buggy; 87 pc pairs)

- **Accesses:** LDG.E.STRONG.SYS `v_cover_row[l]` (0x250, 0x3a0, ...) vs STG.E.STRONG.SYS `v_cover_row[l]=1` (0x300 + 0x150k).
- **Threads:**
  - kernel_11: tid 57 (0x250) vs 10 (0x300), block, WAR; tid 120 vs 97, warp.
  - kernel_47: tid 71 (STG 0x840) vs 17 (LDG 0xa30), block, RAW.
- **Ordering and class:** M4. (a) SC.
- **Fix:** to make one thread own the row, `if (atomicExch(&cover_row[l], 1) == 0)` replaces the load and the store. That is an algorithm change, and the remaining conflicts are still atomic.
- **Fixed build:** yes, #72.

#### #46: main.cu:372 vs 372 (98 rows, buggy; 50 pc pairs)

- **Accesses:** STG.E `column_of_prime_at_row[l] = c` (0x2a0 + 0x150k) vs the same, global.
- **Threads:**
  - kernel_11: tid 99 vs 105, warp, count 2; tid 10 vs 57, block.
  - kernel_619: tid 2 (0x3f0) vs 107 (0x7e0), block.
- **Ordering and class:** M5. (a) DR, different-value WAW.
- **Fix:** `atomicExch(&column_of_prime_at_row[l], c);`. The last writer still wins, but without a data race.
- **Fixed build:** yes, #73.

#### #47: main.cu:371 vs 371 (220 rows, buggy; 110 pc pairs)

- **Accesses:** STS.U8 `s_found` [0x0] (110 rows) and `s_repeat_kernel` [0x2] (110 rows) `= true`, shared.
- **Threads:**
  - kernel_11: tid 10 vs 18, warp, count 45; tid 10 vs 42, block, count 108.
  - s_repeat_kernel: tid 10 (0x2c0) vs 117 (0xd40), block, count 128.
- **Ordering and class:** M6. (a) DR, same-value.
- **Fix:** relaxed atomic stores (int flags with `atomicExch`, or `cuda::atomic_ref` relaxed).
- **Fixed build:** yes, #74.

#### #48: main.cu:380 vs 380 (99 rows, buggy; 50 pc pairs)

- **Accesses:** STS.U8 `s_goto_5 = true` [0x1] (0x2d0 + 0x150k), shared.
- **Threads:**
  - kernel_29 (block 130): tid 34 vs 67, block; tid 67 vs 81, warp.
  - kernel_11: tid 29 (0x6c0) vs 117 (0xab0), block.
- **Ordering and class:** M6. (a) DR, same-value.
- **Fix:** a relaxed atomic store.
- **Fixed build:** yes, #75.

#### #49: main.cu:375 vs 375 (68 rows, buggy; 39 pc pairs)

- **Accesses:** STG.E.STRONG.SYS `v_cover_row[l] = 1` vs the same, global.
- **Threads:**
  - kernel_11: tid 99 vs 105, warp; tid 10 vs 57, block.
  - kernel_2411: tid 69 (0xed0) vs 124 (0x6f0), block.
- **Ordering and class:** M4. (a) SC, same-value.
- **Fix:** none needed for PTX. Claiming the row with `atomicExch` (see #45) removes the pair.
- **Fixed build:** yes, #76.

#### #50: main.cu:377 vs 377 (68 rows, buggy; 39 pc pairs)

- **Accesses:** STG.E.STRONG.SYS `v_cover_column[c1] = 0` vs the same, global.
- **Threads:** kernel_11: tid 10 vs 57, block; tid 99 vs 105, warp.
- **Ordering and class:** M4. (a) SC, same-value.
- **Fix:** as #49.
- **Fixed build:** yes, #77.

#### #51: main.cu:416 vs 416 (6 rows, buggy; 3 pc pairs)

- **Accesses:** STG.E `row_of_green_at_column[...]`, global. 0x120 is the pre-loop store (source L412, frame says L416) and 0x1b0 the loop store (L416).
- **Threads:**
  - kernel_12 (1x64): tid 1 vs 30 (0x120/0x120), warp; tid 36 (0x120) vs 6 (0x1b0), block; tid 1 vs 30 (0x1b0/0x1b0), warp.
  - kernel_88: tid 15 vs 45, block.
- **Ordering and class:** M7. (a) DR. Different values at the join column, same values after it (inferred).
- **Fix:** `atomicExch(&row_of_green_at_column[c_Z0], ...)` for both stores.
- **Fixed build:** yes, #78.

#### #52: main.cu:430 vs 444 (2 rows, buggy)

- **Accesses:** LDG.E `row_of_star_at_column[j]` (0xd0) vs STG.E `row_of_star_at_column[c_Z0] = r_Z0` (0x1c0), global.
- **Threads:** kernel_13 (1x64): tid 13 vs 34, block, WAR, count 5; tid 50 vs 54, warp, count 5.
- **Ordering and class:** M8. (a) DR, value-benign (inferred).
- **Fix:** relaxed atomics on both sides, e.g. `cuda::atomic_ref<int, cuda::thread_scope_device>` load at L430 and store at L444.
- **Fixed build:** yes, #79.

### Fixed groups #53-#65 (warp reduce, M9)

All are (a) DR, warp-synchronous, same warp, WAR. The same pair exists in the buggy build (part-1 groups), so same_in_fixed is n-a.

The fix for every step is `int v = min(sdata[tid], sdata[tid+k]); __syncwarp(); sdata[tid] = v; __syncwarp();`, or a `__shfl_down_sync` reduction.

| group | line, step | kernel | pcs | thread pair (instance) |
|---|---|---|---|---|
| #53 (2 rows) | L192, +16 | calc_min_in_cols | LDS 0x220 / STS 0x250 | block 31: thread 0 reads sdata[16], thread 16 writes it (a_tid 31744 vs b_tid 31760), warp, count 1024 (kernel_3) |
| #54 (2) | L194, +8 | calc_min_in_cols | 0x2a0 / 0x2d0 | block 31: thread 0 vs 8, sdata[8], count 1536 |
| #55 (2) | L196, +4 | calc_min_in_cols | 0x320 / 0x350 | block 31: thread 0 vs 4 |
| #56 (2) | L198, +2 | calc_min_in_cols | 0x3a0 / 0x3d0 | block 31: thread 0 vs 2 |
| #57 (2) | L200, +1 | calc_min_in_cols | 0x420 / 0x450 | block 31: thread 0 vs 1 |
| #58 (2) | L150, +4 | calc_min_in_rows | 0x310 / 0x340 | block 31: thread 0 vs 4, sdata[4] (kernel_1) |
| #59 (2) | L152, +2 | calc_min_in_rows | 0x390 / 0x3c0 | block 31: thread 0 vs 2 |
| #60 (2) | L154, +1 | calc_min_in_rows | 0x410 / 0x440 | block 31: thread 0 vs 1 |
| #61 (4) | L468, +16 | min_reduce_kernel1, min_reduce_kernel2 | k1 0x3f0 / 0x420; k2 0x160 / 0x190 | k1 block 58: thread 0 vs 16 (kernel_31); k2 block 0: thread 0 vs 16 (kernel_32) |
| #62 (4) | L470, +8 | both | k1 0x470 / 0x4a0; k2 0x1e0 / 0x210 | thread 0 vs 8 |
| #63 (4) | L472, +4 | both | k1 0x4f0 / 0x520; k2 0x260 / 0x290 | thread 0 vs 4 |
| #64 (4) | L474, +2 | both | k1 0x570 / 0x5a0; k2 0x2e0 / 0x310 | thread 0 vs 2 |
| #65 (4) | L476, +1 | both | k1 0x5f0 / 0x620; k2 0x360 / 0x390 | thread 0 vs 1 |

#53 and #61 are the already-scored residual's cols and min_warp_reduce +16 steps. They are listed for the row count only and were not re-triaged.

### Fixed groups #66-#79

#### #66: main.cu:291 vs 301 (2 rows, fixed only)

- **Accesses:** LDG.E `cover_row[l]` (0x170, plain) vs STG.E `cover_row[l] = 0` (0x2d0, plain), global.
- **Threads:**
  - kernel_6 (1x127): tid 96 (load) vs 38 (store), block, count 15; tid 90 vs 88, warp.
  - All 197 records across the 100 `step_2` instances are WAR, with the load recorded first. The report row says RAW; see Observations.
- **Ordering and class:** M3. (a) DR.
- **Fix:** `atomicExch((int*)&cover_row[l], 0);` at L301, plus a strong load at L291 (e.g. `((volatile int*)cover_row)[l]`).
- **Buggy twin:** #39 (part 1).

#### #67: device_atomic_functions.hpp:127 (atomicExch at main.cu:293) vs main.cu:301 (1 row, fixed vector-clock only)

- **Accesses:** ATOMG.E.EXCH.STRONG.GPU `cover_row[l]` (0x240) vs STG.E `cover_row[l] = 0` (0x2d0).
- **Threads:** kernel_6: tid 96 (exchange) vs 38 (store), block, WAW, count 15. All 196 records across the 100 instances are WAW.
- **Ordering and class:** M3. (a) DR: a weak store against an atomic.
- **Fix:** `atomicExch((int*)&cover_row[l], 0);` at L301.
- **Buggy twin:** the buggy row of #40 (part 1).

#### #68: main.cu:302 vs 302 (2 rows, fixed)

- **Accesses:** STS.U8 `repeat = true` [0x0] at 0x320.
- **Threads:** kernel_6: tid 9 vs 11, warp, count 52; tid 9 vs 38, block, count 119.
- **Ordering and class:** M1. (a) DR, same-value.
- **Fix:** as #41.
- **Buggy twin:** #41.

#### #69: main.cu:303 vs 303 (2 rows, fixed)

- **Accesses:** STS.U8 `s_repeat_kernel = true` [0x1] at 0x340.
- **Threads:** kernel_6: tid 9 vs 11, warp; tid 9 vs 38, block.
- **Ordering and class:** M1. (a) DR, same-value.
- **Fix:** as #42.
- **Buggy twin:** #42.

#### #70: main.cu:311 vs 311 (2 rows, fixed)

- **Accesses:** STG.E.U8 `repeat_kernel = true` at 0x430.
- **Threads:** kernel_6: tid 0 vs 1, warp, count 1953; tid 0 vs 32, block, count 6048.
- **Ordering and class:** M2. (a) DR, same-value.
- **Fix:** add the `i == 0` guard.
- **Buggy twin:** #43.

#### #71: main.cu:380 vs 387 (176 rows, fixed)

- **Accesses:** as #44.
- **Threads:**
  - kernel_11: tid 42 (LDG 0x190) vs 68 (STG 0x340), block, WAR, count 17; tid 67 vs 83, warp.
  - kernel_35: tid 52 (STG 0x880) vs 34 (LDG 0x8a0), warp, RAW.
- **Ordering and class:** M4. (a) SC.
- **Buggy twin:** #44.

#### #72: main.cu:380 vs 385 (174 rows, fixed)

- **Accesses:** as #45.
- **Threads:** kernel_11: tid 124 (LDG 0x250) vs 68 (STG 0x300), block, count 10; tid 122 vs 105, warp.
- **Ordering and class:** M4. (a) SC.
- **Buggy twin:** #45.

#### #73: main.cu:382 vs 382 (100 rows, fixed)

- **Accesses:** as #46.
- **Threads:** kernel_11: tid 82 vs 53, block, count 5; tid 105 vs 122, warp.
- **Ordering and class:** M5. (a) DR, different-value.
- **Fix:** `atomicExch(&column_of_prime_at_row[l], c)`.
- **Buggy twin:** #46.

#### #74: main.cu:381 vs 381 (220 rows, fixed)

- **Accesses:** as #47 (110 rows s_found, 110 rows s_repeat_kernel).
- **Threads:** kernel_11: tid 34 vs 36, warp, count 79; tid 34 vs 68, block, count 131.
- **Ordering and class:** M6. (a) DR, same-value.
- **Buggy twin:** #47.

#### #75: main.cu:390 vs 390 (100 rows, fixed)

- **Accesses:** as #48 (s_goto_5).
- **Threads:** kernel_35 (block 130): tid 72 vs 82, warp; tid 72 vs 5, block.
- **Ordering and class:** M6. (a) DR, same-value.
- **Buggy twin:** #48.

#### #76: main.cu:385 vs 385 (70 rows, fixed)

- **Accesses:** as #49.
- **Threads:** kernel_11: tid 82 vs 53, block, count 5; tid 105 vs 122, warp.
- **Ordering and class:** M4. (a) SC, same-value.
- **Buggy twin:** #49.

#### #77: main.cu:387 vs 387 (70 rows, fixed)

- **Accesses:** as #50.
- **Threads:** kernel_11: tid 82 vs 53, block; tid 105 vs 122, warp.
- **Ordering and class:** M4. (a) SC, same-value.
- **Buggy twin:** #50.

#### #78: main.cu:426 vs 426 (6 rows, fixed)

- **Accesses:** as #51; 0x120 is the L422 statement.
- **Threads:** kernel_12: tid 1 vs 30 (0x120/0x120), warp; tid 60 (0x120) vs 6 (0x1b0), block; tid 1 vs 30 (0x1b0/0x1b0), warp.
- **Ordering and class:** M7. (a) DR.
- **Buggy twin:** #51.

#### #79: main.cu:440 vs 454 (2 rows, fixed)

- **Accesses:** as #52.
- **Threads:** kernel_13: tid 45 vs 47, warp, WAR, count 4; tid 27 vs 50, block.
- **Ordering and class:** M8. (a) DR.
- **Buggy twin:** #52.

## Defects

None. No group in #41-#79 is class (c). No shared float/64-bit atomics are involved: the only atomics here are 32-bit `ATOMG.E.EXCH`. No pair crosses a barrier or a `__syncwarp`, and no report rests on an `a2_uncertain` record.

## Observations for the harness (not detector defects)

1. **#66 label.** The other_reports/attribution row for #66 says `RAW`, but all 197 `hb_races` records for 0x170/0x2d0 are `WAR`, with the load recorded first. `rw_attribute.py` takes `race_type` from the per-kernel pc-edge verdict (`race_type=v.get("race_type")`), not from `hb_races`. The class of the pair is unaffected. Comparing that edge's current/ancient pcs with the `hb_races` direction would decide whether the label is wrong.
2. **Residual registration gap.** `recall_pairs.json` registers the fixed residual as `main.cu:146 vs 146` only. The other intra-step lines in the fixed build therefore show up as other reports: L150-L154 rows, L192-L200 cols, L468-L476 min_warp_reduce (#53-#65, 36 rows). The oracle JSON's `fixed.reason` already names L146-L154 "and the same lines of the other two functions". Registering those lines as residual equivalents would absorb these rows.
3. **step_5a line attribution.** cuVein's frame for `step_5a` pc 0x120 is main.cu:416 (fixed 426). By its operands, the instruction is the L412 (fixed L422) pre-loop store `row_of_green_at_column[c_Z0] = i`. The cause, presumably the ptxas line table, was not checked.

# cmssw-1: triage of 18 other reports (4 groups)

- Repo: cms-sw/cmssw. Buggy commit 37a05c6b, fixed commit d1ce91e5.
- File: `HeterogeneousCore/CUDAUtilities/interface/prefixScan.h` (abbreviated `ps` below).
- The fix makes `ci`/`co` `volatile` (fixed L142-143) and adds `__threadfence()` before the block counter (fixed L157).
- Line numbers: lines up to L140 are equal in both builds; buggy L155/L172/L179 are fixed L158/L175/L182.
- Kernel: `multiBlockPrefixScan<unsigned int>`.
  - kernel_1 has grid 2 x 1024, size 2000.
  - kernel_3 has grid 20 x 1024, size 20000.
- Tids: `(block << 10) | thread`.

**SASS facts (`dots/driver.sm_89.dot`):**
- **Buggy:**
  - `STG.E` at 0x360 (L22, `co[i] = x`);
  - `STG.E` at 0x6f0 (L77);
  - `ATOMG.E.ADD.STRONG.GPU` at 0x7a0 (L155), with no `MEMBAR` anywhere in the kernel;
  - after `BAR.SYNC` 0x820, the last block does `LDG.E` 0x1000 and `STG.E` 0x1050 (L179).
- **Fixed:**
  - `STG.E.STRONG.SYS` at 0x360 (L22) and `LDG.E.STRONG.SYS` at 0x380 (L66);
  - `BAR.SYNC` 0x770, `MEMBAR.SC.GPU` 0x7c0, then `ATOMG.E.ADD.STRONG.GPU` 0x820 (thread 0);
  - `BAR.SYNC` 0x8a0;
  - last block: `LDG.E.STRONG.SYS` 0x9b0 (L175), then `LDG.E.STRONG.SYS` 0x1090 and `STG.E.STRONG.SYS` 0x10f0 (L182).
  - There is no `MEMBAR` after the atomic.

| class | groups | rows |
|---|---|---|
| (a) DR | #01 | 6 |
| (a) SC | #02 #03 #04 | 12 (of which #03 and #04, 9 rows, are the already-scored residual) |

## cmssw-1#01: ps:179 vs ps:22 (6 rows, buggy: ve-main, ve-certain, sc)

- **Accesses:**
  - A: ps:22 `co[i] = x` in `warpPrefixScan` (<- ps:61 blockPrefixScan <- ps:150), plain STG.E global, by every thread of a non-last block;
  - B: ps:179 `co[i] += psum[k]` in the last block, LDG.E (0x1000, RAW) and STG.E (0x1050, WAW), plain global.
- **Threads:**
  - kernel_1: RAW a_tid 1376 (block 1, thread 352) vs b_tid 352 (block 0, thread 352), count 976; WAW 1184 (block 1, thread 160) vs 160 (block 0, thread 160).
  - kernel_3: RAW 1376 vs 18784 (block 18, thread 352); WAW 1728 vs 19136.
  - dist=grid, a2_uncertain 0.
  - Counts: 0x360/0x1000 has count 976 against 944 for the registered L77 pair 0x6f0/0x1000. The 32 extra per block are warp 0's elements (local index < 32), which only L22 writes.
- **Ordering:**
  - Within block b: L22 →po `BAR.SYNC` (L69, L74, L79) →sync thread 0 →po relaxed `atomicAdd(pc,1)`. There is no fence, so there is no release pattern.
  - The last block has no fence after its atomicAdd either, so there is no acquire.
  - Nothing orders A before B, and both are plain.
- **Class:** (a) DR. This is the oracle's own root cause (missing `__threadfence` before the counter), and the oracle header names L22 among the block writes. The pair L22-L179 is not in `recall_pairs.json`, which registers L77-L172 (primary), L22-L172 and L77-L179 (extra). Registering it would absorb these 6 rows. Same in fixed: yes, as an SC pair (#03).
- **Concrete pair:** block 1 thread 352 writes co[1376] at L22; last block 0 thread 352 reads and writes co[1376] at L179 (kernel_1).
- **Fix:** in thread 0, put `__threadfence()` both before and after `atomicAdd(pc, 1)`. The upstream fix adds only the one before.

## cmssw-1#02: ps:175 vs ps:22 (3 rows, fixed: ve-main, ve-certain, sc)

- **Accesses:** A: ps:22 `co[i] = x`, `STG.E.STRONG.SYS` (volatile) at 0x360, global. B: fixed ps:175 `psum[i] = (j < size) ? co[j] : T(0)`, `LDG.E.STRONG.SYS` at 0x9b0, global.
- **Threads:** kernel_3: a_tid 2047 (block 1, thread 1023) vs b_tid 1 (block 0, thread 1), dist=grid, count 18, a2_uncertain 0.
  - Address co[2047] is block 1's last element.
  - The same read is also reported (and matched as the registered residual L77-L175) against 0x740, the L77 store by block 1 thread 991 (tid 2015) that overwrites co[2047] after `BAR.SYNC` L74.
- **Ordering:**
  - Release side: thread 0's `MEMBAR.SC.GPU` comes after the block's last barrier (0x770), so block 1's stores are covered.
  - Acquire side: the last block's thread 0 does the relaxed atomicAdd, then `STS.U8` isLastBlockDone and `BAR.SYNC`. There is no fence, so there is no acquire pattern.
  - Both accesses are morally strong (relaxed.sys), so this is an unordered strong conflict, not a DR.
- **Is it really unordered?** Yes under strict PTX: the only route from block 1 to the last block is the relaxed RMW chain on `pc`, with no acquire after it. It is ordered only under the fence + counter idiom reading (REVIEW item 2). Same decision as the registered residual.
- **Class:** (a) SC. Same in fixed: yes. In buggy, the corresponding L22-L172 pair is a registered extra DR pair.
- **Concrete pair:** block 1 thread 1023's store co[2047] at L22 vs last block thread 1's load at L175 (kernel_3).
- **Fix:** `__threadfence()` after `atomicAdd(pc, 1)` in thread 0 (fixed L158).

## cmssw-1#03: ps:182 vs ps:22 (6 rows, fixed): not re-triaged

- The caller lists L22 vs the last-block RMW at L182 as already scored.
- **Facts recorded:**
  - 0x360 (`STG.E.STRONG.SYS`, L22) vs 0x1090 (`LDG.E.STRONG.SYS`, RAW) and 0x10f0 (`STG.E.STRONG.SYS`, WAW), both L182;
  - kernel_1: a_tid 1536 (block 1, thread 512) vs b_tid 512 (block 0, thread 512); kernel_3: 1696 vs 672;
  - dist=grid; SC.
- **Class:** (a) SC, consistent with the residual (same missing acquire as #02).

## cmssw-1#04: ps:182 vs ps:66 (3 rows, fixed): not re-triaged

- The caller lists L66 vs L182 as already scored.
- **Facts recorded:**
  - A: ps:66 `ws[warpId] = co[i]` by lane 31 (`LDG.E.STRONG.SYS` at 0x380, <- ps:152); B: L182 store 0x10f0; WAR;
  - kernel_1: a_tid 1567 (block 1, thread 543 = lane 31 of warp 16) vs b_tid 543 (block 0); kernel_3: 1727 vs 703;
  - dist=grid; SC.
- **Class:** (a) SC, consistent with the residual.

## Defects

None found in this target.

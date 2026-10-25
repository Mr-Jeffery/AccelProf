# lit-shoc-1: triage of 160 other reports in 16 groups

repo vetter/shoc | buggy 785d9ee6 | fixed 700ab826 | file `src/cuda/level1/scan/scan_kernel.h`

**Result:** all 16 groups (160 rows) are class (a), DR, high confidence, and identical on buggy and fixed. They share one mechanism: the warp-synchronous last-warp tail of `reduce<T, 256>` (L122-L132). None of them is the oracle `bottom_scan` `s_seed` race.

## Shared mechanism (applies to every group)

**Source.** At both commits, L122-L132 of `reduce` are:

```
if (tid < warpSize) {
    // NB2: This section would also need __sync calls if warp
    // synchronous execution were not assumed
    if (blockSize >= 64) sdata[tid] += sdata[tid + 32];   // L126
    if (blockSize >= 32) sdata[tid] += sdata[tid + 16];   // L127
    if (blockSize >= 16) sdata[tid] += sdata[tid + 8];    // L128
    if (blockSize >= 8)  sdata[tid] += sdata[tid + 4];    // L129
    if (blockSize >= 4)  sdata[tid] += sdata[tid + 2];    // L130
    if (blockSize >= 2)  sdata[tid] += sdata[tid + 1];    // L131
}
```

- `sdata` is `volatile T*` over dynamic shared memory (L83-L84).
- The fix commit changes only whitespace in `reduce`. The line numbers are unchanged; the diff hunk is `@@ -130,7 +130,7 @@`.

**SASS.** Taken from `dots/driver.sm_89.dot`, kernel `_Z6reduceIdLi256EEvPKT_PS0_i`. The buggy build (cuda-13.4) and the fixed build (cuda-13.3) are byte-identical in this range:

```
0a00: BAR.SYNC.DEFER_BLOCKING 0x0        ; end of L120 step
0a10: @P1 BRA (.L_x_17)                   ; tid >= 32 skips
0a20: LDS.64 R4, [R2.X8]                  ; L126 sdata[tid]
0a30: LDS.64 R6, [R2.X8+0x100]            ; L126 sdata[tid+32]
0a50: STS.64 [R2.X8], R4                  ; L126 write sdata[tid]
0a60: LDS.64 R6, [R2.X8]   0a70: LDS.64 R8, [R2.X8+0x80]   0a90: STS.64 [R2.X8], R6   ; L127
0aa0: LDS.64 R8, [R2.X8]   0ab0: LDS.64 R10,[R2.X8+0x40]   0ad0: STS.64 [R2.X8], R8   ; L128
0ae0: LDS.64 R10,[R2.X8]   0af0: LDS.64 R12,[R2.X8+0x20]   0b10: STS.64 [R2.X8], R10  ; L129
0b20: LDS.64 R4, [R2.X8]   0b30: LDS.64 R12,[R2.X8+0x10]   0b50: STS.64 [R2.X8], R4   ; L130
0b60: LDS.64 R6, [R2.X8]   0b70: LDS.64 R12,[R2.X8+0x8]    0b90: STS.64 [R2.X8], R6   ; L131
0ba0: BSYNC B0
```

- `reduce<float, 256>` has the same shape, shifted by +0x10, with plain `LDS`/`STS` at 0xa60, 0xa80/0xaa0, 0xac0/0xae0, 0xb00/0xb20, 0xb40/0xb60 and 0xb80/0xba0.
- Every access is a plain LDS/STS with no `.STRONG`, matching D20 (i) for volatile shared.
- Between the BAR at 0xa00 and the BSYNC at 0xba0 there is no BAR, WARPSYNC, SHFL or VOTE, and no fence.
- The reported LDS of each line is the `sdata[tid+k]` load (+0x80/+0x40/+0x20/+0x10/+0x8 for double). The `sdata[tid]` own-slot loads (0xa60, 0xaa0, ...) are never reported, which is consistent with the analysis.

**Thread relation.** These come from `vector-clock/kernel_{0,3}.json` `hb_races` on both builds; 20 entries per kernel map one-to-one onto the 20 pc pairs.

- The tid encoding is `a_tid = loc_block*1024 + threadIdx.x`. This is inferred: `a_tid // 1024 == loc_block` in every entry, and `addr / sizeof(T)` equals the slot that the decoded writer owns.
- Every entry has `dist = warp`, `a2_uncertain = 0` and `class = DR`.
- Both threads are in warp 0 of the same block, because only `tid < 32` runs this section.
- `count` equals 64 blocks times the number of conflicting lanes. For example, 1024 = 64 x 16 for the k=16 slot pairs, and 1984 = 64 x 31 for k=1.
- The scalar-clock kernel JSONs have no `hb_races` (n_races 0). The sc rows are the same pc pairs from the scalar matrix, so tids come from the ve entries only.

**What orders them.** Nothing does.

- Inside the `tid < 32` branch, the only intended ordering is lockstep execution of warp 0; the source comment NB2 says so.
- Under independent thread scheduling, program order of lane 0 and lane k gives no cross-thread order.
- With no `__syncwarp`, `_sync` shuffle or vote between the accesses, the pairs are unordered.
- Both accesses are weak (volatile shared lowers to plain LDS/STS on sm_89, D20 (i)), so each conflict is a DR.
- Note (inferred): even if volatile were taken as relaxed.sys at the PTX level, the pairs would still be unordered, so they would be an SC rather than no report.

**Class.** (a) DR, warp-synchronous, for every group.

**Fix (all groups).** Replace L126-L131 with a register reduction:

```
T v = sdata[tid] + sdata[tid+32];
for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffff, v, o);
if (tid == 0) sdata[0] = v;
```

Alternatively, split each step into `T v = sdata[tid] + sdata[tid+k]; __syncwarp(); sdata[tid] = v; __syncwarp();`. A `__syncwarp()` placed only between lines does not fix the same-line WAR groups (#02, #07, #11, #14, #16).

**Concrete pc map.** For each line, the reported load is L(k), which reads `sdata[tid+k]`, and the store is S, which writes `sdata[tid]`. Both are in shared space.

| line | k | double LDS.64 / STS.64 | float LDS / STS |
|---|---|---|---|
| L126 | 32 | (not reported) / 0xa50 | (not reported) / 0xa60 |
| L127 | 16 | 0xa70 / 0xa90 | 0xa80 / 0xaa0 |
| L128 | 8 | 0xab0 / 0xad0 | 0xac0 / 0xae0 |
| L129 | 4 | 0xaf0 / 0xb10 | 0xb00 / 0xb20 |
| L130 | 2 | 0xb30 / 0xb50 | 0xb40 / 0xb60 |
| L131 | 1 | 0xb70 / 0xb90 | 0xb80 / 0xba0 |

Each group below has rows for buggy/ve, buggy/sc, fixed/ve and fixed/sc, for both `reduce<double,256>` and `reduce<float,256>`.

- **same_in_fixed:** yes for all groups.
- **Thread pair notation:** `bB.tT` means block B, threadIdx.x T, which is warp 0 lane T. These are the representative tids from the buggy vector-clock JSON.

## lit-shoc-1#01: L126 vs L127 (8 rows)
- **Accesses:**
  - A: scan_kernel.h:126 STS (write `sdata[tid]`), shared.
  - B: scan_kernel.h:127 LDS (read `sdata[tid+16]`), shared. RAW.
  - pcs: double 0xa50/0xa70, float 0xa60/0xa80.
- **Threads:** writer b31.t16 and reader b31.t0, on `sdata[16]` (addr 128 for double, 64 for float). dist = warp, count 1024 per kernel.
- **Ordering:** none (see the shared mechanism). The write at L126 by lane 16 and the read at L127 by lane 0 have no `__syncwarp` between them.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** thread 16 writes `sdata[16]` at L126 and thread 0 reads it at L127. Fix with the shuffle reduction above, or `__syncwarp()` after the L126 store.

## lit-shoc-1#02: L127 vs L127 (8 rows)
- **Accesses:**
  - A: L127 LDS (`sdata[tid+16]`).
  - B: L127 STS (`sdata[tid]`).
  - Shared, WAR. pcs: double 0xa70/0xa90, float 0xa80/0xaa0.
- **Threads:** reader b31.t0 and writer b31.t16, on `sdata[16]`. dist = warp, count 1024.
- **Ordering:** none. This is the same statement in two different lanes.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** thread 0 reads `sdata[16]` and thread 16 writes `sdata[16]`, both at L127. Fix: `T v = sdata[tid] + sdata[tid+16]; __syncwarp(); sdata[tid] = v;`.

## lit-shoc-1#03: L127 vs L128 (16 rows, one mechanism, no split)
- **Accesses:**
  - WAR: L127 LDS (`sdata[tid+16]`) vs L128 STS (`sdata[tid]`). pcs: double 0xa70/0xad0, float 0xa80/0xae0.
  - RAW: L127 STS (`sdata[tid]`) vs L128 LDS (`sdata[tid+8]`). pcs: double 0xa90/0xab0, float 0xaa0/0xac0.
  - Both in shared space.
- **Threads:**
  - WAR: b31.t0 reads `sdata[16]` and b31.t16 writes it. The fixed double kernel's representative is b33.t0/t16. Count 1024.
  - RAW: b31.t8 writes `sdata[8]` and b31.t0 reads it. Count 1536.
  - All dist = warp.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pairs and fix:** (t0 reads `sdata[16]` at L127, t16 writes it at L128) and (t8 writes `sdata[8]` at L127, t0 reads it at L128). Fix with the shuffle reduction, or `__syncwarp()` around each step's store.

## lit-shoc-1#04: L127 vs L129 (8 rows)
- **Accesses:** L127 LDS (`sdata[tid+16]`) vs L129 STS (`sdata[tid]`), shared, WAR. pcs: double 0xa70/0xb10, float 0xa80/0xb20.
- **Threads:** b31.t0 reads `sdata[16]` and b31.t16 writes it. dist = warp, count 1024.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L127 and t16 writes at L129. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#05: L127 vs L130 (8 rows)
- **Accesses:** L127 LDS (`sdata[tid+16]`) vs L130 STS (`sdata[tid]`), shared, WAR. pcs: double 0xa70/0xb50, float 0xa80/0xb60.
- **Threads:** b31.t0 reads `sdata[16]` and b31.t16 writes it. dist = warp, count 1024.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L127 and t16 writes at L130. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#06: L127 vs L131 (8 rows)
- **Accesses:** L127 LDS (`sdata[tid+16]`) vs L131 STS (`sdata[tid]`), shared, WAR. pcs: double 0xa70/0xb90, float 0xa80/0xba0.
- **Threads:** b31.t0 reads `sdata[16]` and b31.t16 writes it. The float representative is b5.t0/b5.t16. dist = warp, count 1024.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L127 and t16 writes at L131. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#07: L128 vs L128 (8 rows)
- **Accesses:** L128 LDS (`sdata[tid+8]`) vs L128 STS (`sdata[tid]`), shared, WAR. pcs: double 0xab0/0xad0, float 0xac0/0xae0.
- **Threads:** b31.t0 reads `sdata[8]` and b31.t8 writes it. The fixed double kernel's representative is b33.t0/t8. dist = warp, count 1536.
- **Ordering:** none. This is the same statement in two lanes.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads `sdata[8]` and t8 writes it, both at L128. Fix: `T v = sdata[tid] + sdata[tid+8]; __syncwarp(); sdata[tid] = v;`.

## lit-shoc-1#08: L128 vs L129 (16 rows, one mechanism, no split)
- **Accesses:**
  - WAR: L128 LDS (`sdata[tid+8]`) vs L129 STS. pcs: double 0xab0/0xb10, float 0xac0/0xb20.
  - RAW: L128 STS (`sdata[tid]`) vs L129 LDS (`sdata[tid+4]`). pcs: double 0xad0/0xaf0, float 0xae0/0xb00.
  - Both in shared space.
- **Threads:**
  - WAR: b31.t0 and b31.t8 on `sdata[8]`. Count 1536.
  - RAW: b31.t4 writes `sdata[4]` and b31.t0 reads it. Count 1792.
  - All dist = warp.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pairs and fix:** (t0 reads at L128, t8 writes at L129) and (t4 writes at L128, t0 reads at L129). Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#09: L128 vs L130 (8 rows)
- **Accesses:** L128 LDS (`sdata[tid+8]`) vs L130 STS, shared, WAR. pcs: double 0xab0/0xb50, float 0xac0/0xb60.
- **Threads:** b31.t0 and b31.t8 on `sdata[8]`. dist = warp, count 1536.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L128 and t8 writes at L130. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#10: L128 vs L131 (8 rows)
- **Accesses:** L128 LDS (`sdata[tid+8]`) vs L131 STS, shared, WAR. pcs: double 0xab0/0xb90, float 0xac0/0xba0.
- **Threads:** b31.t0 and b31.t8 on `sdata[8]`. The float representative is b5.t0/b5.t8. dist = warp, count 1536.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L128 and t8 writes at L131. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#11: L129 vs L129 (8 rows)
- **Accesses:** L129 LDS (`sdata[tid+4]`) vs L129 STS (`sdata[tid]`), shared, WAR. pcs: double 0xaf0/0xb10, float 0xb00/0xb20.
- **Threads:** b31.t0 reads `sdata[4]` and b31.t4 writes it. dist = warp, count 1792.
- **Ordering:** none. This is the same statement in two lanes.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads and t4 writes `sdata[4]`, both at L129. Fix: split the read and write with `__syncwarp()`, or use the shuffle reduction.

## lit-shoc-1#12: L129 vs L130 (16 rows, one mechanism, no split)
- **Accesses:**
  - WAR: L129 LDS (`sdata[tid+4]`) vs L130 STS. pcs: double 0xaf0/0xb50, float 0xb00/0xb60.
  - RAW: L129 STS vs L130 LDS (`sdata[tid+2]`). pcs: double 0xb10/0xb30, float 0xb20/0xb40.
  - Both in shared space.
- **Threads:**
  - WAR: b31.t0 and b31.t4 on `sdata[4]`. Count 1792.
  - RAW: b31.t2 writes `sdata[2]` and b31.t0 reads it. Count 1920.
  - All dist = warp.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pairs and fix:** (t0 reads at L129, t4 writes at L130) and (t2 writes at L129, t0 reads at L130). Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#13: L129 vs L131 (8 rows)
- **Accesses:** L129 LDS (`sdata[tid+4]`) vs L131 STS, shared, WAR. pcs: double 0xaf0/0xb90, float 0xb00/0xba0.
- **Threads:** b31.t0 and b31.t4 on `sdata[4]`. The float representative is b5.t0/b5.t4. dist = warp, count 1792.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads at L129 and t4 writes at L131. Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#14: L130 vs L130 (8 rows)
- **Accesses:** L130 LDS (`sdata[tid+2]`) vs L130 STS, shared, WAR. pcs: double 0xb30/0xb50, float 0xb40/0xb60.
- **Threads:** b31.t0 reads `sdata[2]` and b31.t2 writes it. dist = warp, count 1920.
- **Ordering:** none. This is the same statement in two lanes.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads and t2 writes `sdata[2]`, both at L130. Fix: split the read and write with `__syncwarp()`, or use the shuffle reduction.

## lit-shoc-1#15: L130 vs L131 (16 rows, one mechanism, no split)
- **Accesses:**
  - WAR: L130 LDS (`sdata[tid+2]`) vs L131 STS. pcs: double 0xb30/0xb90, float 0xb40/0xba0.
  - RAW: L130 STS vs L131 LDS (`sdata[tid+1]`). pcs: double 0xb50/0xb70, float 0xb60/0xb80.
  - Both in shared space.
- **Threads:**
  - WAR: b31.t0 and b31.t2 on `sdata[2]`. The float representative is b5. Count 1920.
  - RAW: b31.t1 writes `sdata[1]` and b31.t0 reads it. The float buggy representative is b5.t1/b5.t0. Count 1984.
  - All dist = warp.
- **Ordering:** none.
- **Class:** (a) DR, warp-synchronous.
- **Pairs and fix:** (t0 reads at L130, t2 writes at L131) and (t1 writes at L130, t0 reads at L131). Fix: shuffle reduction or a per-step `__syncwarp()`.

## lit-shoc-1#16: L131 vs L131 (8 rows)
- **Accesses:** L131 LDS (`sdata[tid+1]`) vs L131 STS, shared, WAR. pcs: double 0xb70/0xb90, float 0xb80/0xba0.
- **Threads:** b31.t0 reads `sdata[1]` and b31.t1 writes it. The float representative is b5. dist = warp, count 1984.
- **Ordering:** none. This is the same statement in two lanes.
- **Class:** (a) DR, warp-synchronous.
- **Pair and fix:** t0 reads and t1 writes `sdata[1]`, both at L131. Fix: split the read and write with `__syncwarp()`, or use the shuffle reduction.

## Defects
None. No group is class (c).

## Notes
- **Facts used:**
  - Groups and pcs come from `~/t21c_triage/lit-shoc-1.md`.
  - Frames and cuda_home come from `attrib/lit-shoc-1-{buggy,fixed}.json`; buggy is cuda-13.4 and fixed is cuda-13.3.
  - tids, dist and count come from `realworld-2026-10/lit-shoc-1-{buggy,fixed}/vector-clock/kernel_{0,3}.json`.
  - SASS comes from `dots/driver.sm_89.dot`.
  - The source comes from `shoc.git` at both commits.
- **Inferred:** the tid encoding `loc_block*1024 + threadIdx.x`.
- **Not checked:** whether the race changes `reduce`'s numeric output on this GPU.
  - The buggy native run (meta.json native_err) reports the SP scan FAILED (128 mismatches); the fixed run passes.
  - Since `reduce` is unchanged between the builds, that failure most likely comes from the oracle `bottom_scan` race (inferred, not tested).

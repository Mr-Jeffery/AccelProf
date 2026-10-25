# hecbench-dxtc2-1: triage of the other reports (T21c step 3)

ORNL/HeCBench `src/dxtc2-cuda`. Buggy fe80f0f7475d8e68fa91e6c31270255826040efc, fixed 6e11c2bb2d354bce70a84e3b301757fa50b3cafd.
There are 98 rows in 28 groups. All 98 are class (a) DR, warp-synchronous, high confidence. None is also on the fixed build.

| class | groups | rows |
|---|---|---|
| (a) DR | 28 | 98 |
| (b) | 0 | 0 |
| (c) | 0 | 0 |
| (d) | 0 | 0 |

## Evidence used

- **Source.** `main.cu` and `helper_math.h` at both commits, from `~/incoming/realworld/HeCBench.git`.
- **SASS.** `dots/main.sm_89.dot` of `realworld-2026-10/hecbench-dxtc2-1-{buggy,fixed}`.
- **Vector-clock records.** `vector-clock/kernel_0.json` `hb_races`, matched to each row by (kernel, {a_pc, b_pc}). Every vector-clock row matches exactly one hb_race.
- **Scalar-clock records.** The scalar-clock `kernel_0.json` files have no `hb_races`. Their 49 rows have exactly the same pc pairs as the 49 vector-clock rows. The tids below therefore come from the vector-clock records.
- **Attribution.** `attrib/hecbench-dxtc2-1-{buggy,fixed}.json`.
- **Oracle and recall pairs.** `eval/realworld/oracle/hecbench-dxtc2-1.json` and `recall_pairs.json`.
- **Tid encoding.** The tid is written as `b<block>t<threadIdx.x>w<warp>`. The decoding is a_tid = 1024*block + threadIdx.x. This is inferred: it agrees with `loc_block` in every record (for example a_tid 33800 has loc_block 33, which gives thread 8).
- **Shared layout.** Inferred from the SASS immediates and the hb_race addresses:
  - covariance[96]: 0x000-0x17f
  - dps[16]: 0x180-0x1bf
  - colors[16]: 0x540-0x5ff (float3, 12 B each)
  - sums[16]: 0x600-0x6bf
  - xrefs[16]: 0x6c0

## Facts common to all 28 groups

1. **Where the accesses are.** Every access in these groups is in `loadColorBlock`, inlined at main.cu:479. It runs under `if (idx < 16)` (main.cu:157), that is, lanes 0-15 of warp 0 of each 64-thread block (NUM_THREADS = 64, main.cu:46). Every vector-clock record has:
   - both tids in warp 0 and below 16;
   - `dist=warp`, `class=DR`, `a2_uncertain=0` and `gate_policy=recorded`.
2. **No sync between the accesses.** In the buggy SASS, all of these accesses are plain LDS, STS, STS.64, LDS.64 or LDS.128 between pc 0x240 and 0x2120. None carries `.STRONG`.
   - The kernel's first `BAR.SYNC` is at 0x2140, which is the `cg::sync(cta)` at main.cu:481.
   - There is no WARPSYNC, SHFL, VOTE, MEMBAR, ATOM or RED anywhere before 0x2140. Only BSSY/BSYNC convergence markers appear there.
   - The source has no `__syncwarp` in this region, and the two `__syncthreads()` in bestFitLine are commented out (L95, L106).
   - Under PTX's independent thread scheduling, nothing orders a lane's access against another lane's access. Every pair below is therefore an unordered conflict of plain accesses: a DR, warp-synchronous.
3. **Why these rows are "other".** `oracle/hecbench-dxtc2-1.json` already names all of these chains in `buggy_expected` and `thread_pair_example`:
   - L71-L74;
   - L88-L93 vs L99-L104;
   - L99-L104 vs L110;
   - dps L170 -> L131;
   - L176 -> L178.

   However, `recall_pairs.json` registers only two pairs:
   - L70 -> L71 (primary);
   - L176-178 vs L176-178 (both_builds).

   So these groups are the same lock-step idiom as the oracle race, in colorSums, bestFitLine, sortColors and loadColorBlock. They are not something else. None is in evalAllPermutations, which runs after the BAR at 0x2140.
4. **Fixed build.** The fixed build has 3 reports in each mode (vector-clock and scalar-clock), all at main.cu:448 vs main.cu:448. That is the registered residual.
   - The fixed source puts `cg::sync(cta)` between every phase (L383, 391, 404, 415, 426, 437, 444, 450), and the fixed SASS has a BAR.SYNC between the phases.
   - None of these 28 pairs occurs there, so `same_in_fixed = no` for all groups.

## Mechanisms

### M1: colorSums XOR butterfly (main.cu:67-75, groups #04-#16)

- Each step `sums[idx] += sums[idx ^ k]` (L71 k=8, L72 k=4, L73 k=2, L74 k=1) compiles to:
  - three `LDS [R+0x600..0x608]` of sums[idx^k], attributed to main.cu:7x;
  - three `STS [R0+0x600..0x608]` of sums[idx], attributed to `helper_math.h:371-373` (float3 `operator+=`) <- main.cu:7x.
- Lane i's load of sums[i^k] is unordered against lane i^k's stores of sums[i^k] in the same and later steps (WAR), and against its stores in earlier steps (RAW).
- Then all lanes read sums[0] through `LDS.128 [0x600]` at 0x4f0 (main.cu:168, `bestFitLine(colors, sums[0])`), unordered against lane 0's L74 store.
- **Minimal fix:** split each step into a load and a store, with a sync after each, for example `float3 t = sums[idx ^ k]; __syncwarp(0xffff); sums[idx] += t; __syncwarp(0xffff);`. The upstream fix instead replaced the butterfly with a serial sum by thread 0 between `cg::sync`s.

### M2: covariance fill, tree reduction and eigenvector loads (main.cu:86-111, 50-58, groups #17-#27)

- **Fill.** L88-L93 compile to STS.64 at 0x590, 0x5a0 and 0x5b0, attributed to L89, L91 and L93.
- **Reduction.** L99-L104 run under `if (idx < d)` for d = 8, 4, 2, 1, unrolled at 0x5d0-0x6e0, 0x720-0x830, 0x870-0x980 and 0x9c0-0xad0.
  - Step d reads covariance[6(idx+d)+c], which lane idx+d wrote in the fill or in step 2d.
  - Within one step the readers touch only rows >= d and the writers only rows < d. So the conflicts are fill-vs-step and step-vs-next-step, which is what the commented-out barriers at L95 and L106 would have ordered.
- **Eigenvector loads.** After the loop, every lane 0-15 runs `firstEigenVector(covariance)` (L110). Its loads of covariance[0..5] are hoisted out of the power iteration as:
  - `LDS.128 [RZ]` at 0xaf0, for covariance[0..3]. The lineinfo attributes it to main.cu:104 <- 168;
  - `LDS.64 [0x10]` at 0xb00, for covariance[4..5]. The lineinfo attributes it to main.cu:57 <- 110.

  Identifying 0xaf0 with firstEigenVector's load is inferred from three things: the address (covariance[0]), its position after the final BSYNC of the reduction, and its use by the FADDs that follow.
- **Minimal fix:** replace both `//__syncthreads();` (L95, L106) with `__syncwarp(0xffff);`.
  - All of lanes 0-15 reach both points.
  - A `__syncthreads()` there would sit inside `if (idx < 16)`, which threads 16-63 of the block do not reach.

### M3: dps store vs sortColors loads (main.cu:170 vs 131, group #28)

- Each lane stores dps[idx] with `STS [R2.X4+0x180]` at 0x18e0. Then every lane reads dps[0..15] with four `LDS.128` (0x18f0, 0x1900, 0x1910, 0x1a30; L131 <- L174).
- **Minimal fix:** add `__syncwarp(0xffff);` between L172 and L174.

### M4: initial colors store vs scatter store (main.cu:161-163 vs 178, groups #01-#03)

- Lane j stores colors[j].x/.y/.z (L161-L163; STS at 0x250, 0x240 and 0x270). Later, lane i stores `colors[xrefs[i]]` (L178; STS at 0x2100-0x2120).
- The compiler forwarded `tmp = colors[idx]` (L176) and the `colors[idx]` reads of L82 and L170 from registers. The buggy SASS has no LDS of the colors range 0x540-0x5ff before 0x2140, and the L178 STS stores R15, R14 and R17, the registers computed at L161-L163.
- So in this build, the conflict on colors[j] that the oracle describes as L176 -> L178 appears as a WAW between lane j's L161-163 store and lane i's L178 store, where xrefs[i] = j. The WAW is itself an unordered pair of plain writes in the source.
- It is not a same-value write: lane i stores its own colour into colors[j].
- **Minimal fix:** add `__syncwarp(0xffff);` between L176 and L178. Lane j's L161-163 stores precede it in program order, so that sync orders them before every lane's L178 store.

## Per group

The pc pair, then the vector-clock thread pair and shared address. All pairs are in compress, buggy build, dist=warp.

### #01 main.cu:162 vs main.cu:178 (2 rows), M4
- **A:** main.cu:162 <- 479, STS colors[idx].y, pc 0x240, shared.
- **B:** main.cu:178 <- 479, STS colors[xrefs[idx]].y, pc 0x2110, shared.
- **Threads:** block 41, t15 (A) vs t0 (B), addr 0x5f8 = colors[15].y, WAW, count 968. That xrefs[0] = 15 in block 41 is inferred from the address.
- **Ordering:** none (see common fact 2).
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M4.

### #02 main.cu:161 vs main.cu:178 (2 rows), M4
- **A:** L161 STS colors[idx].x, pc 0x250.
- **B:** L178 STS, pc 0x2100.
- **Threads:** block 33, t14 vs t0, addr 0x5e8 = colors[14].x, WAW.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M4.

### #03 main.cu:163 vs main.cu:178 (2 rows), M4
- **A:** L163 STS colors[idx].z, pc 0x270.
- **B:** L178 STS, pc 0x2120.
- **Threads:** block 41, t15 vs t0, addr 0x5fc = colors[15].z, WAW.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M4.

### #04 / #05 / #06 helper_math.h:371/372/373 vs main.cu:71 (2 rows each), M1
- **A:** main.cu:71 <- 166, LDS sums[idx^8].x/.y/.z, pcs 0x2a0, 0x2b0 and 0x2c0.
- **B:** helper_math.h:371/372/373 <- main.cu:74, STS sums[idx].x/.y/.z, pcs 0x4b0, 0x4d0 and 0x4e0.
- **Threads:** block 33, t8 loads sums[0] and t0 stores sums[0] at L74. Addrs 0x600, 0x604 and 0x608. WAR, count 1024.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M1.

### #07 / #08 / #09 helper_math.h:371/372/373 vs main.cu:72 (2 rows each), M1
- **A:** main.cu:72 <- 166, LDS sums[idx^4], pcs 0x330, 0x340 and 0x350.
- **B:** L74 STS, pcs 0x4b0, 0x4d0 and 0x4e0.
- **Threads:** block 33, t4 loads sums[0] and t0 stores it. Addrs 0x600, 0x604 and 0x608. WAR.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M1.

### #10 / #11 / #12 helper_math.h:371/372/373 vs main.cu:73 (4 rows each), M1
- **A:** main.cu:73 <- 166, LDS sums[idx^2], pcs 0x3c0, 0x3d0 and 0x3e0.
- **B, two pc pairs per group:**
  - the STS at L73 (pcs 0x410, 0x430, 0x440);
  - the STS at L74 (pcs 0x4b0, 0x4d0, 0x4e0).
- **Threads:** block 33, t2 loads sums[0] and t0 stores it at L73 and at L74. Addrs 0x600, 0x604 and 0x608. WAR.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M1.

### #13 / #14 / #15 helper_math.h:371/372/373 vs main.cu:74 (4 rows each), M1
- **First pc pair (RAW):**
  - A: STS sums[idx] at L73 (pcs 0x410, 0x430, 0x440);
  - B: LDS sums[idx^1] at L74 (pcs 0x450, 0x460, 0x470).
  - Block 33, t1 stores sums[1] and t0 loads it. Addrs 0x60c, 0x610 and 0x614.
- **Second pc pair (WAR):**
  - A: LDS at L74 (pcs 0x450, 0x460, 0x470);
  - B: STS at L74 (pcs 0x4b0, 0x4d0, 0x4e0).
  - t1 loads sums[0] and t0 stores it. Addrs 0x600, 0x604 and 0x608.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M1.

### #16 helper_math.h:371 vs main.cu:168 (2 rows), M1
- **A:** helper_math.h:371 <- main.cu:74, STS sums[0].x, pc 0x4b0.
- **B:** main.cu:168 <- 479, LDS.128 [0x600] (sums[0] for bestFitLine), pc 0x4f0.
- **Threads:** block 33, t0 (A) vs t1 (B), addr 0x600, RAW, count 960 (64 blocks x 15 reader lanes).
- **Note on the wide load.** The LDS.128 also covers 0x60c-0x60f (sums[1].x), which the source does not read. The reported conflict is at 0x600, an element the source does read, so the over-wide bytes do not decide this report.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M1 (the `__syncwarp` after the L74 store).

### #17 / #18 / #19 main.cu:89/91/93 vs main.cu:99/101/103 (2 rows each), M2 fill vs reduction
- **A:** STS.64 at 0x590, 0x5a0 and 0x5b0: covariance[6idx+0..1], [6idx+2..3] and [6idx+4..5].
- **B:** LDS at 0x5d0, 0x5f0 and 0x610, step d=8: covariance[6(idx+8)+0/2/4].
- **Threads:** block 33, t8 stores and t0 loads. Addrs 0xc0, 0xc8 and 0xd0 (covariance[48], [50] and [52]). RAW, count 512.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M2, at L95.

### #20 to #25 main.cu:99..104 vs the same line (6 rows each), M2 step vs next step
- Each group is one component c = 0..5, which is L99+c (`covariance[6*idx+c] += covariance[6*(idx+d)+c]`). It has three pc pairs:

| step pair | storing lane | loading lane | covariance index | count |
|---|---|---|---|---|
| d=8 store vs d=4 load | t4 | t0 | 24+c | 256 |
| d=4 store vs d=2 load | t2 | t0 | 12+c | 128 |
| d=2 store vs d=1 load | t1 | t0 | 6+c | 64 |

- The exact pcs (STS/LDS) and addresses per group:

| group | line | d=8 vs d=4 | d=4 vs d=2 | d=2 vs d=1 |
|---|---|---|---|---|
| #20 | L99 | 0x650/0x720 @0x60 | 0x7a0/0x870 @0x30 | 0x8f0/0x9c0 @0x18 |
| #21 | L100 | 0x670/0x730 @0x64 | 0x7c0/0x880 @0x34 | 0x910/0x9d0 @0x1c |
| #22 | L101 | 0x690/0x740 @0x68 | 0x7e0/0x890 @0x38 | 0x930/0x9e0 @0x20 |
| #23 | L102 | 0x6b0/0x750 @0x6c | 0x800/0x8a0 @0x3c | 0x950/0x9f0 @0x24 |
| #24 | L103 | 0x6d0/0x760 @0x70 | 0x820/0x8b0 @0x40 | 0x970/0xa00 @0x28 |
| #25 | L104 | 0x6e0/0x770 @0x74 | 0x830/0x8c0 @0x44 | 0x980/0xa10 @0x2c |

- **Threads:** all block 33, RAW. The storing lane wrote at step d and lane 0 reads at step d/2. Only the commented-out `__syncthreads()` at L106 stood between them.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M2, at L106.

### #26 main.cu:99 vs main.cu:104 (2 rows), M2 last step vs firstEigenVector
- **A:** main.cu:99 <- 168, STS covariance[0], step d=1 (lane 0 only), pc 0xa40.
- **B:** LDS.128 [RZ] = covariance[0..3], pc 0xaf0, executed by lanes 0-15.
  - The lineinfo attributes it to main.cu:104 <- 168. In the source, the read is `firstEigenVector(covariance)` at L110 -> L56-L58 (inferred, see M2).
- **Threads:** block 33, t0 (A) vs t1 (B), addr 0x0, RAW, count 960.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M2, at L106.
- The line attribution of B differs from the source line but does not change the class. Every element of the LDS.128 is read by the source.

### #27 main.cu:103 vs main.cu:57 (2 rows), M2 last step vs firstEigenVector
- **A:** main.cu:103 <- 168, STS covariance[4], step d=1, pc 0xac0.
- **B:** main.cu:57 <- 110, LDS.64 [0x10] = covariance[4..5] (matrix[4], matrix[5]), pc 0xb00.
- **Threads:** block 33, t0 vs t1, addr 0x10, RAW, count 960.
- **Class:** (a) DR, warp-synchronous.
- **Fix:** M2, at L106.

### #28 main.cu:131 vs main.cu:170 (8 rows), M3
- **A:** main.cu:170 <- 479, STS dps[idx], pc 0x18e0.
- **B:** main.cu:131 <- 174, LDS.128 of dps[0..3], [4..7], [8..11] and [12..15], pcs 0x18f0, 0x1900, 0x1910 and 0x1a30.
- **Threads (block 33, RAW, count 960 each):**

| B pc | storing lane | loading lane | addr |
|---|---|---|---|
| 0x18f0 | t0 | t1 | 0x180 |
| 0x1900 | t4 | t0 | 0x190 |
| 0x1910 | t8 | t0 | 0x1a0 |
| 0x1a30 | t12 | t0 | 0x1b0 |

- **Class:** (a) DR, warp-synchronous.
- **Fix:** M3.

## Defects
None found in these groups. Every report is a pair the source does not order under PTX, and the addresses and tids match the source semantics.

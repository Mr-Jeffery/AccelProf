# hecbench-morphology-1: triage of the other reports (T21c step 3)

ORNL/HeCBench `src/morphology-cuda`. Buggy e245737e759f0bba355d4e7148ecd1185dedb2c3, fixed 7be8747ef1156a96b273f91cab7f9b6e3e6c3429.
There are 8 rows in 1 group. The group is class (a) DR, high confidence, and is not on the fixed build.

| class | groups | rows |
|---|---|---|
| (a) DR | 1 | 8 |
| (b) | 0 | 0 |
| (c) | 0 | 0 |
| (d) | 0 | 0 |

## Evidence used

- **Source.** `morphology.cu` at both commits.
- **SASS.** `dots/morphology.sm_89.dot`.
- **Vector-clock records.** `vector-clock/kernel_{0..3}.json` `hb_races`, matched by (kernel, {a_pc, b_pc}).
- **Scalar-clock records.** These JSONs carry no `hb_races`. The 4 scalar-clock rows have the same pc pairs as the 4 vector-clock rows.
- **Attribution and oracle.** `attrib/hecbench-morphology-1-{buggy,fixed}.json`, `oracle/hecbench-morphology-1.json` and `recall_pairs.json`.
- **Tid encoding.** The tid is written as `b<block>t<tid>w<warp>`. The decoding is a_tid = 1024*block + linear thread index (inferred, as for dxtc2).
- **Block shape.** vhgw_vert has block (1, 64), so its linear index equals threadIdx.y. The oracle gives the driver as `./main 64 64 192 192 1`, which makes selSize 64 and blocks of 64 threads, 2 warps.

## #01 morphology.cu:98 vs morphology.cu:98 (8 rows)

### Accesses
- **Statement.** `opArray[tid] = elementOp<opType>(opArray[tid], opArray[tid + offset]);`, the reverse scan of `twoWayScan` (L97-L98), inlined into vhgw_horiz (<- L128) and vhgw_vert (<- L160). The space is dynamic shared memory, with plain single-byte accesses.
  - **Load:** A, `LDS.U8` of opArray[tid+offset], at pc 0x2d0 (vhgw_horiz<0>, vhgw_horiz<1>) or 0x2f0 (vhgw_vert<0>, vhgw_vert<1>).
  - **Store:** B, `STS.U8` of opArray[tid], at pc 0x320 (horiz) or 0x340 (vert).
- **Rows.** 4 kernel instances x 2 modes. All four instances have the same instructions at these pcs; only the IMNMX polarity differs between op 0 and op 1.
- **Why this row is "other".** The oracle's `buggy_expected` names this pair ("plus the reverse-scan pair L98 vs L98"). However, `recall_pairs.json` registers only the forward-scan pair, morphology.cu:94-95 vs 95.

### Thread relation
Each row's pc pair matches three `hb_races`, all `class=DR` and `a2_uncertain=0`:

| row | kernel | file | WAR @0xa0, dist=block | WAR @0xa1, dist=warp | RAW @0xa0, dist=block |
|---|---|---|---|---|---|
| 2399 | horiz<0> | kernel_2 | b110: t31(w0) loads opArray[32], t32(w1) stores it; count 17789 | b110: t32 loads opArray[33], t33 stores it; count 130752 | b574: t32(w1) stores opArray[32], t31(w0) loads it; count 67 |
| 2400 | horiz<1> | kernel_0 | b77: t31/t32; count 17688 | b77: t32/t33; count 130752 | b75: t32 store, t28 load; count 168 |
| 2401 | vert<0> | kernel_3 | b94: t31/t32; count 17726 | b94: t32/t33; count 130752 | b13: t32 store, t30 load; count 130 |
| 2402 | vert<1> | kernel_1 | b177: t31/t32; count 17819 | b177: t32/t33; count 130752 | b471: t32 store, t31 load; count 37 |

- The scalar-clock rows 2403-2406 are the same four pc pairs.
- Addresses 0xa0 and 0xa1 are opArray[32] and opArray[33]. This assumes `opArray = sMem + 2*selSize` = 0x80 for selSize 64, which is inferred from L115/L146 and the addresses.

### What orders them, or fails to
- Within one iteration of `for (offset ...)` (L92), thread tid loads opArray[tid+offset]. In the same iteration, thread tid+offset stores opArray[tid+offset] whenever `tid+offset <= selSize-1-offset` (L97).
- The only barrier is the `__syncthreads()` at L100, after both scans (BAR.SYNC at 0x330 horiz, 0x350 vert). Nothing sits between the LDS at 0x2d0/0x2f0 and the other thread's STS at 0x320/0x340 in the same iteration.
- The kernels contain no WARPSYNC, SHFL, VOTE, MEMBAR or ATOM.
- The t31/t32 pair is cross-warp, so it is a plain DR whether or not warps run in lock step. The t32/t33 pair is the same statement inside warp 1 (warp-synchronous).

### Class
(a) DR. These are unordered conflicting plain accesses to the same byte by different threads.
- **Concrete pair:** vhgw_horiz<0>, block 110, offset = 1. Thread 31 (warp 0) loads opArray[32] at L98 while thread 32 (warp 1) stores opArray[32] at L98.
- **Minimal fix:** in each iteration, read both operands into registers, then `__syncthreads()` outside the `if`s, then store. This is what 7be8747 does (fixed L100-L108: barrier, then reads into `fwd_val`/`rev_val`, then `__syncthreads()`, then writes).

### Fixed build
The fixed build has 0 reports in both modes, and its vector-clock JSONs have 0 `hb_races`. `same_in_fixed = no`.

## Defects
None found in this group.

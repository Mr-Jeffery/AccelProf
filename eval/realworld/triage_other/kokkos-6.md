# kokkos-6: triage of 48 other reports (5 groups, #01 split in two)

- Repo: kokkos/kokkos. Buggy commit af652331, fixed commit 71761882.
- Files:
  - `core/src/Cuda/Kokkos_Cuda_ReduceScan.hpp` (abbreviated `rs`). The fix adds `__syncthreads()` after fixed L118, at the end of `cuda_inter_warp_reduction`, so buggy L >= 119 is fixed L+1.
  - `core/src/impl/Kokkos_FunctorAnalysis.hpp` (`fa`).
- Kernel: kernel_4, `ParallelReduce<TestRepeatedTeamReduce<Cuda>, RangePolicy<...>>` (the test's range reduction, not the team kernel of the oracle). Grid (1,1,1), block (1,256,1).
- Path: rs:697/698 → `CudaReductionsFunctor<...,false,false>::scalar_inter_block_reduction` (rs:380-422) → `scalar_intra_block_reduction` (rs:355-378) → `scalar_intra_warp_reduction` (rs:328-353).
- That warp reduction already has kokkos-5's fix (`if (lane_id != 0)` at rs:350). Its join is `fa:636 dst[i] += src[i]` (non-volatile, <- fa:979).
- Tids: `(block << 10) | threadIdx.y`; lane = threadIdx.y % 32.

**`scalar_intra_warp_reduction`:**

```cpp
mask = width == 32 ? 0xffffffff : ((1 << width) - 1) << ((threadIdx.y*blockDim.x + threadIdx.x) / width) * width;
__syncwarp(mask);
for (delta = skip_vector ? blockDim.x : 1; delta < width; delta *= 2) {
  if (lane_id + delta < 32) functor.join(value, value + delta);   // fa:636: LDS value[i], LDS value[i+delta], STS value[i]
  __syncwarp(mask);
}
if (lane_id != 0) *value = *(value - lane_id);                     // rs:351
```

**Call sites:**
- rs:363 calls it with width 32 for every warp.
- rs:374 calls it from `if (warp_id == 0)` with width = blockDim.x*blockDim.y/32 = 8. That gives per-lane masks 0xff, 0xff00, 0xff0000 and 0xff000000, while all 32 lanes of warp 0 take part.

**SASS of the width-8 loop (buggy, from rs:394):**
- `LDS` own at 0xb10, `LDS` value[i+delta] at 0xb20, `STS` own at 0xb40;
- then the `__syncwarp(mask)` sequence (a `__cuda_sm70_warpsync` call or the uniform skip);
- broadcast: `@P1 LDS` value[-lane] at 0xbe0, then `@P1 STS` at 0xc10.

| class | groups | rows |
|---|---|---|
| (a) DR | #01a #01b #02 #03 #04 #05 | 48 |

## kokkos-6#01 sub a: fa:636 vs fa:636 in the width-32 calls (20 rows: 5 pc pairs x buggy/fixed x ve/sc)

- **Accesses:** LDS (join read of value[i+delta]) vs STS (join write of value[i+delta] by lane i+delta). Shared. pc pairs:
  - 0x6b0/0x6e0 (rs:363 <- rs:394);
  - 0xfb0/0xff0, 0x1040/0x1070, 0x10b0/0x10d0 and 0x1110/0x1130 (rs:363 <- rs:417, the unrolled steps).
- **Threads:** all dist=warp, a2_uncertain 0, the same in both builds.
  - buggy: 160 vs 161 (warp 5 lanes 0/1, addr 0x284 = value[161]); 192 vs 193; 128 vs 130; 192 vs 196; 128 vs 136. The pairs are lanes 0 and delta.
  - fixed: 96 vs 97, 96 vs 98, 96 vs 100, 96 vs 104, 192 vs 193.
- **Ordering:** none within a step. Lane i's read of value[i+delta] and lane i+delta's write of value[i+delta] are in the same loop iteration, and the only `__syncwarp` is at the end of the iteration.
  - The reduction is correct only if the warp executes all loads before any store (lockstep). That is warp-synchronous code.
- **Class:** (a) DR, warp-synchronous. Same in fixed: yes.
  - kokkos-5 registers the same code as its both-build pair "tree-loop join step L547". kokkos-6 has no such registration, and its innermost frame is fa:636.
- **Concrete pair:** warp 5, lane 0 reads value[161] while lane 1 writes it, at delta = 1 (kernel_4, pcs 0x6b0/0x6e0).
- **Fix:** split the join step: `Scalar t = value[delta]; __syncwarp(mask); *value += t;` inside the guard, or use `__shfl_down_sync`.

## kokkos-6#01 sub b: fa:636 vs fa:636 in the width-8 call (8 rows: pc pairs 0xb20/0xb40 (rs:374 <- rs:394) and 0x1560/0x1580 (rs:374 <- rs:417) x buggy/fixed x ve/sc)

- **Accesses:** as in sub a, in the width-8 loop.
- **Threads:** two instances per pc pair, dist=warp:
  - 0xb20/0xb40: WAR 0 vs 1 (addr 0x4 = value[1], intra-step); RAW 8 vs 6 (addr 0x20 = value[8]: lane 8 writes its slot, lane 6 reads it at delta 2);
  - 0x1560/0x1580: the same tids.
- **Ordering:**
  - The intra-step part is as in sub a.
  - Cross-group part: lane 6 synchronizes with `__syncwarp(0xff)` and lane 8 with `__syncwarp(0xff00)`. Neither mask contains the other lane, yet the guard `lane_id + delta < 32` lets lane 6 read lane 8's slot. Nothing orders lane 8's store before lane 6's load in any step.
- **Class:** (a) DR. Same in fixed: yes.
- **Concrete pair:** lane 8 stores value[8] and lane 6 loads value[8] at delta = 2, in warp 0 of block 0.
- **Fix:** both call sites run with all 32 lanes of the warp, so `mask = 0xffffffff` in `scalar_intra_warp_reduction` removes the cross-group part. The intra-step part needs the sub-a fix.
  - Also restrict the join to the group (`lane_id % width + delta < width`) if the cross-group values are meant to be excluded. That they are meant to be excluded is inferred, not stated in the source.

## kokkos-6#02: rs:351 vs fa:636 (8 rows, buggy: 4 pc pairs x ve/sc)

- **Accesses:** the width-8 call (rs:374) only.
  - 0xb20 LDS (join read of value[8] by lane 7) vs 0xc10 STS (lane 8's broadcast `*value = *(value - 8)`, i.e. store to value[8]), WAR.
  - 0xb40 STS (lane 0's join write of value[0]) vs 0xbe0 LDS (lane 8's broadcast read of value[0]), RAW.
  - The same two at 0x1560/0x1660 and 0x1580/0x1620 (<- rs:417).
- **Threads:** 7 vs 8 (addr 0x20) and 0 vs 8 (addr 0x0), dist=warp, block 0, in both instances.
- **Ordering:** lane 8 is in mask group 0xff00 and lanes 0 and 7 are in group 0xff. Lane 8's broadcast follows only its own group's `__syncwarp(0xff00)`. Nothing orders it against lane 7's join read of value[8] or lane 0's join writes of value[0].
  - Only thread 0 then reads value[0] for `*result` (rs:376). Whether lanes 8-31's broadcast copies are used later is not settled here (inferred unused).
- **Class:** (a) DR. Same in fixed: yes (#04, unchanged by the fix).
- **Concrete pair:** lane 0 writes value[0] at its last join step, while lane 8 reads value[0] for its broadcast.
- **Fix:** `mask = 0xffffffff` in `scalar_intra_warp_reduction` (both call sites are full warps), which makes the loop's `__syncwarp` order lane 8 after lane 0's last step.

## kokkos-6#03: rs:411 vs rs:411 (2 rows, buggy: ve, sc)

- **Accesses:** rs:411 `*global_flags = 0;`, plain STG.E RZ at 0xe50, global, by every thread of the block.
  - The grid has one block, so `num_teams_done == gridDim.x == 1` and the block is the last block.
- **Threads:** warp 160 vs 161 (count 3968); block 160 vs 192 (count 28672).
- **Ordering:** none among the stores after `__syncthreads_or`.
- **Class:** (a) DR, same-value (0) write-write. Same in fixed: yes (#05). This is the same code as kokkos-5#03.
- **Fix:** `if (threadIdx.x + threadIdx.y == 0) *global_flags = 0;`

## kokkos-6#04: rs:352 vs fa:636 (8 rows, fixed: ve, sc)

- Fixed twin of #02, with the same pcs (0xb20/0xc10, 0xb40/0xbe0, 0x1560/0x1660, 0x1580/0x1620) and the same tids (7 vs 8, 0 vs 8).
- **Class:** (a) DR. Fix: as in #02.

## kokkos-6#05: rs:412 vs rs:412 (2 rows, fixed: ve, sc)

- Fixed twin of #03: `STG.E RZ` at 0xe50.
- **Threads:** warp 96 vs 97, block 96 vs 160.
- **Class:** (a) DR, same-value. Fix: as in #03.

## Defects

None found in this target.

# raft-1: triage of 136 other reports (10 groups)

- Repo: rapidsai/raft. Buggy commit 32df870d, fixed commit e39ec788.
- File: `cpp/include/raft/matrix/detail/select_radix.cuh` (abbreviated `sr` below). The fixed file is the buggy file plus 10 lines after L750 (a comment and `__syncthreads()` at fixed L760), so buggy line x >= 751 is fixed line x+10.
- Kernels: `radix_kernel<float,long,8,512,{false,true},dense_layout<long>>`, launched with grid (25,2,1) and block 512. Each row `blockIdx.y` has its own `Counter` (`counters + blockIdx.y`, 0x280 bytes).
- Tids come from the vector-clock `hb_races`. They use cuVein's encoding `(linear block << 10) | (warp << 5) | lane`, where linear block = blockIdx.y*25 + blockIdx.x.
- SASS references are to `dots/driver.sm_89.dot` of each build (cuda-13.4 buggy, cuda-13.3 fixed).

| class | groups | rows |
|---|---|---|
| (a) DR | #01 #02 #03 #04 #05 #07 #08 #09 #10 | 45 |
| (c) | #06 | 91 |

## Common mechanism M1 (groups #01-#05 and #07-#09; #10 is the scored residual of the same kind)

This is the last-block-done hand-off on fields of `Counter`. The SASS of all four kernels (two builds, two `fused_last_filter` values) has the same order.

**Other block X, every thread:**
1. reads at kernel start, before the first `BAR.SYNC` (0x850 in the fused=false kernel, L244):
   - `LDG.E.128 [counter+0x0]` at pc 0xc0, which reads k and len (L672-673);
   - `LDG.E.64 [counter+0x10]` at 0xd0, which reads previous_len (L674).
2. then, between that barrier and the L318 `BAR.SYNC` (0x5000):
   - `LDG.E [counter+0x18]` at 0x940 (L265, kth_value_bits);
   - `ATOMG.E.ADD.64.STRONG.GPU [counter+0x80]` at 0x1630, 0x1e20, 0x2610 and 0x2df0 (L291, `atomicAdd(p_filter_cnt, 1)`).
3. then `MEMBAR.SC.GPU` at 0x5160 (L750). The fixed build adds `BAR.SYNC` at 0x51b0 (L760).
4. then thread 0 only: `ATOMG.E.INC.STRONG.GPU [counter+0x100]` (L754 buggy / L764 fixed).

**Last block L:**
1. thread 0's same relaxed `ATOMG.E.INC`, then `BAR.RED.OR` (`__syncthreads_or`, L757/L767);
2. then plain stores to the counter:
   - `STG.E [counter+0x18]` (L391);
   - `STG.E.128 [counter+0x0]` (L387-388; attributed to L388);
   - `STG.E.64 [counter+0x80], RZ` (L783/L793);
   - `STG.E.64 [counter+0x10]` (L781/L791);
   - in the early-stop path, `STG.E.64 [counter+0x10], RZ` and `[counter+0x8], RZ` (L761-762/L771-772).

There is no `MEMBAR` between L's atomicInc and these stores in either build.

**What orders them, and what fails to:**
- **Release side (present):** X's access →po `BAR.SYNC` →sync thread 0 →po `MEMBAR.SC.GPU` →po atomicInc. Thread 0 of X therefore has a release pattern, and every M1 access of X is before it in base causality. This holds in both builds because every M1 access of X is before the L318 barrier, which comes before the L750 fence.
- **Acquire side (missing):** L's thread 0 does a relaxed atomicInc followed only by `bar.red`, which is CTA scope. There is no acquire pattern morally strong with X's release, so L's stores are not after X's accesses in causality order.
- X's accesses are reads or writes on the same addresses, and at least one side is plain. Under strict PTX each pair is therefore a DR.
- This is exactly the condition REVIEW item 2 records for raft-1's registered fixed-build residual ("the last block's relaxed `atomicInc` has no fence after it").
- The upstream fix (`__syncthreads()` at fixed L760) only covers the post-L318 accesses (the L322 histogram merge). It does not change M1, which is why every M1 pair is in both builds:
  - #02 = #07 and #03 = #08 under the +10 line shift;
  - #05 = #09;
  - #01 and #04 carry both builds in one group.
- Inferred, not a PTX guarantee: in practice X's access completes before X's own atomicInc, and L's stores are control-dependent on L's atomicInc result.
- **One-line fix for all of M1:** in radix_kernel, inside `if (threadIdx.x == 0)`, put `__threadfence();` right after `atomicInc(&counter->finished_block_cnt, gridDim.x - 1)`. That is an acquire before `__syncthreads_or`.
- If REVIEW item 2 is decided "absent" (the idiom reading), M1 moves to (b), "fence + counter idiom", together with the residual.

## raft-1#01: sr:672 vs sr:388 (5 rows: buggy ve-main, ve-certain, sc; fixed ve, sc)

- **Accesses:**
  - A: sr:672 `current_k = counter->k` (with L673 len), LDG.E.128 global, read by every thread of X at kernel start;
  - B: sr:387-388 `counter->k = ...; counter->len = ...` in choose_bucket (<- L769 buggy / L779 fixed), STG.E.128 global (pc 0x5f10 buggy, 0x5f40 fixed), by the one thread that finds the bucket in L.
- **Threads:**
  - buggy kernel_1: a_tid 25600 (block (0,1), thread 0) vs b_tid 41166 (block (15,1), thread 206), dist=grid, count 24576, a2_uncertain 0;
  - buggy kernel_2: 25600 vs 47138 (block (21,1), thread 34);
  - fixed kernel_1: 0 (block (0,0), thread 0) vs 9444 (block (9,0), thread 228);
  - fixed kernel_2: 26624 (block (1,1), thread 0) vs 25634 (block (0,1), thread 34).
  - Always the same row, so the same counter, in different blocks.
- **Ordering:** M1. Nothing orders L's STG after X's LDG except the missing acquire.
- **Class:** (a) DR, WAR (both plain). Same in fixed: yes.
- **Concrete pair and fix:** X = block (0,1) thread 0 reads k/len at L672, and L = block (15,1) thread 206 writes them at L387-388, in pass 1 (kernel_1). Fix: the M1 fix.

## raft-1#02: sr:674 vs sr:781 (3 rows, buggy)

- **Accesses:** A sr:674 `previous_len = counter->previous_len`, LDG.E.64 global [counter+0x10], pc 0xd0. B sr:781 `counter->previous_len = current_len`, STG.E.64 global (pc 0x60f0), by L thread 0.
- **Threads:** kernel_1: a_tid 0 (block (0,0), thread 0) vs b_tid 9216 (block (9,0), thread 0). kernel_2: 25600 vs 47104 (block (21,1), thread 0). dist=grid, a2_uncertain 0.
- **Ordering:** M1.
- **Class:** (a) DR, WAR. Same in fixed: yes (#07). Fix: the M1 fix.

## raft-1#03: sr:674 vs sr:761 (6 rows, buggy; both fused_last_filter kernels)

- **Accesses:** A sr:674 LDG.E.64 [counter+0x10] (pc 0xd0, or 0xe0 for fused=true). B sr:761 `counter->previous_len = 0` in the early-stop branch, STG.E.64 RZ (pc 0x6120, or 0x7240 for fused=true), by L thread 0.
- **Threads:** kernel_2: a_tid 1024 (block (1,0), thread 0) vs b_tid 0 (block (0,0), thread 0). kernel_3 (fused=true): 25600 vs 50176 (block (24,1), thread 0). dist=grid.
- **Ordering:** M1. In the early-stop pass `filter_and_histogram` returns before L318, but A is before the L244 barrier, so the release side still holds.
- **Class:** (a) DR, WAR. Same in fixed: yes (#08). Fix: the M1 fix.

## raft-1#04: sr:265 vs sr:391 (5 rows, both builds)

- **Accesses:** A sr:265 `kth_value_bits = counter->kth_value_bits` (<- L738), LDG.E [counter+0x18], pc 0x940. B sr:391 `counter->kth_value_bits |= bucket << start_bit` (<- L769/L779), STG.E [counter+0x18], pc 0x5ef0 buggy / 0x5f20 fixed.
- **Threads:** the same tid pairs as #01 (for example 25600 vs 41166 in buggy kernel_1, and 0 vs 9444 in fixed kernel_1), dist=grid.
- **Ordering:** M1. A is between the L244 and L318 barriers. B only runs when !early_stop, and early_stop is uniform per pass, so X executed L318.
- **Class:** (a) DR, WAR. Same in fixed: yes. Fix: the M1 fix.

## raft-1#05: device_atomic_functions.hpp:226 (atomicAdd at sr:291) vs sr:783 (11 rows, buggy)

- **Accesses:**
  - A: `atomicAdd(p_filter_cnt, 1)` at sr:291 (chain device_atomic_functions.hpp:226 <- device_atomics.cuh:250/463/498 <- sr:291 <- sr:164 <- sr:311 <- sr:738), ATOMG.E.ADD.64.STRONG.GPU [counter+0x80] at four unrolled pcs: 0x1630, 0x1e20, 0x2610 and 0x2df0;
  - B: sr:783 `counter->filter_cnt = 0`, STG.E.64 RZ (pc 0x60a0), by L thread 0.
- **Threads:**
  - kernel_1: a_tid 3133 (block (3,0), thread 61) / 255 / 2157 / 127 vs b_tid 9216 (block (9,0), thread 0), dist=grid;
  - kernel_2: 25600, 25613 and 25601 vs 47104.
- **Ordering:** M1. One side is strong (atomic) and one plain, so they are not morally strong.
  - Caveat (execution-dependent): if some thread of L performed its own `atomicAdd(&filter_cnt)` after X's in modification order, X's atomic would be in observation order before it, and so causally before L's store via the L318 barrier and thread 0.
  - Executions without such an L atomic exist, for example when L has no candidates. The pair is therefore a DR in some executions.
  - What would settle the observed run: the per-address atomic order (the coherence_profile record for counter+0x80) of kernel_1/kernel_2.
- **Class:** (a) DR, WAW, medium confidence. Same in fixed: yes (#09). Fix: the M1 fix.

## raft-1#06: device_atomic_functions.hpp:226 vs device_atomic_functions.hpp:226 (91 rows: buggy 46 ve + 11 sc, fixed 23 ve + 11 sc)

This is the **known false-report class**, and it is the only such group in raft-1.

- **Accesses:** all 23 pc pairs are `LDS.64 [r]` against another thread's `ATOMS.CAST.SPIN.64 [r]`, in either order (WAR or RAW).
  - The SASS (identical pcs in both builds) has eight emulation loops of the form `LDS.64 R, [a]; IADD3/IMAD.X (+1); ATOMS.CAST.SPIN.64 R', [a], R, R'; ISETP; @!P BRA <loop head at the LDS>`. The loop heads (LDS) are at 0x1780, 0x1f70, 0x2760, 0x2f40, 0x4880, 0x4970, 0x4a60 and 0x4b50. The CAS sits 0x30 later in each loop: 0x17b0, 0x1fa0, 0x2790, 0x2f70, 0x48b0, 0x49a0, 0x4a90 and 0x4b80.
  - The address is `histogram_smem` (shared base 0x1120, 256 x 8 bytes). The hb addresses fall in 0x12e0-0x18d8.
  - Source: `atomicAdd(histogram_smem + bucket, (long)1)` at sr:255 (pass 0, <- L257) and sr:297 (pass > 0, <- L311).
  - device_atomics.cuh:250 forwards `long` to CUDA's `atomicAdd(unsigned long long*, ...)` at device_atomic_functions.hpp:226. ptxas lowers that atom.add.u64 on shared to the CAS loop on sm_89.
  - Note on attribution: the line table gives the loops at 0x1780-0x2f70 the frame sr:291, but their address base is histogram_smem, so they are the sr:297 atomicAdd (inferred from the SASS operand).
- **Threads:**
  - buggy kernel_0: 25830 vs 25632 (block 25, warps 7/1, dist=block) and 25656 vs 25654 (block 25, warp 1, lanes 24/22, dist=warp);
  - buggy kernel_1: 31806 vs 32132 (block 31, dist=block).
  - All are within one block; there are no grid pairs.
- **Ordering:** at PTX level both are parts of atomic RMWs (`atom.add.u64`), which are morally strong and never a DR. The plain LDS is only the CAS loop's speculative read; the CAS validates it.
- **Class:** (c), detector defect: the emulated atomic's load is not treated as part of the RMW. Same in fixed: yes.
- **Minimal failing input:**

```cuda
__global__ void k(unsigned long long* out) {
  __shared__ unsigned long long h;
  if (threadIdx.x == 0) h = 0;
  __syncthreads();
  atomicAdd(&h, 1ull);        // sm_89: LDS.64 + ATOMS.CAST.SPIN.64 retry loop
  __syncthreads();
  if (threadIdx.x == 0) *out = h;
}
// k<<<1, 64>>>(out): expected no report; cuVein is expected to pair warp 0's LDS.64 with warp 1's ATOMS.CAST.SPIN.64 (shared WAR/RAW, DR).
```

The expected report is inferred from raft-1's SASS and reports; this input was not run, because the task allowed no GPU jobs. Check that the build emits the CAS loop (`cuobjdump -sass` shows `ATOMS.CAST.SPIN.64`).

## raft-1#07: sr:674 vs sr:791 (2 rows, fixed)

- This is fixed-build #02 (sr:791 = buggy sr:781, `counter->previous_len = current_len`, STG.E.64 at 0x6120).
- **Threads:** kernel_1: a_tid 0 vs b_tid 9216 (block (9,0), thread 0). kernel_2: 26624 (block (1,1), thread 0) vs 25600 (block (0,1), thread 0). dist=grid.
- **Ordering:** M1. **Class:** (a) DR, WAR. Fix: the M1 fix.

## raft-1#08: sr:674 vs sr:771 (4 rows, fixed; both fused_last_filter kernels)

- This is fixed-build #03 (sr:771 = buggy sr:761, early-stop `previous_len = 0`, pc 0x6150 or 0x7270).
- **Threads:** kernel_2: a_tid 1024 vs b_tid 0. kernel_3: 25600 vs 44032 (block (18,1), thread 0). dist=grid.
- **Ordering:** M1. **Class:** (a) DR, WAR. Fix: the M1 fix.

## raft-1#09: atomicAdd at sr:291 vs sr:793 (7 rows, fixed)

- This is fixed-build #05 (sr:793 = buggy sr:783, `filter_cnt = 0`, STG.E.64 at 0x60d0).
- **Threads:** kernel_1: a_tid 3133 / 255 / 2157 / 127 vs b_tid 9216, dist=grid.
- **Ordering:** M1, with the same execution-dependent caveat as #05.
- **Class:** (a) DR, WAW, medium confidence. Fix: the M1 fix.

## raft-1#10: atomicAdd at sr:322 vs sr:786 (2 rows, fixed): not re-triaged

- **Accesses:** A = the L322 histogram merge `atomicAdd(histogram + i, histogram_smem[i])` (frames end in sr:322 <- sr:738; ATOMG.E.ADD.64.STRONG.GPU at 0x50d0). B = fixed sr:786 `histogram[i] = 0` (STG.E.64 at 0x6080).
- **Threads:** kernel_0: a_tid 32 (block (0,0)) vs b_tid 3104 (block (3,0)). kernel_1: 19649 vs 9409. dist=grid.
- The caller lists this pair (L322 vs L786) as already scored, so it is not re-triaged here. The class line follows the residual (DR under strict PTX).
- **Why it is in other_reports (fact):** `eval/realworld/recall_pairs.json` raft-1 `fixed.residual` lists only B = L361/L349/block_load.cuh:312 and L382-383. The plain reset appears only as the buggy-numbered `extra` pair L776. Adding a fixed residual entry (A sr:322, B sr:786) would absorb these 2 rows.

## Defects

- **D-raft-1-1 (#06, 91 rows):** the LDS that heads ptxas's 64-bit shared `atomicAdd` CAS-emulation loop is checked as a plain read against other threads' `ATOMS.CAST.SPIN.64`. Minimal input: under #06. Expected: the LDS..ATOMS.CAST loop is treated as one RMW, or its LDS is exempt.

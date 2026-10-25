# cccl-3: T21c step 3 triage of 222 other reports (10 groups)

repo NVIDIA/cccl | buggy 8b99dbeba05c7e5a5b83cd80075c4d7392995098 | fixed 879ab26a112fbbbeb86ad96e1d2cc5c657c890a9.
Oracle race (not these): merge_histograms atomicAdd vs the last block's histogram reads, missing `__syncthreads()` before
thread 0's `atomicInc` (agent_topk.cuh:L431-L450, L642-L684).

Result: 9 groups / 66 rows class (a) DR; 1 group / 156 rows class (c). No (b), no (d).

Evidence used:
- Sources: `cub/cub/agent/agent_topk.cuh` and `cub/cub/device/dispatch/dispatch_topk.cuh` at both commits, read from
  `~/incoming/realworld/cccl.git`. The fix diff is: two comment lines become one at L650-651, and `__syncthreads()` is
  added after `__threadfence()` (fixed L653-654). So fixed line = buggy line + 2 from L653 on.
- SASS: `dots/driver.sm_89.dot` of both stores, kernels `DeviceTopKKernel` and `DeviceTopKHistogramKernel`.
- Thread ids: `vector-clock/kernel_{0,1,2}.json` `hb_races`, matched by pc pair. Tid encoding: block = tid / 1024 and
  thread = tid % 1024, which matches `loc_block`. Launch is grid 49 x 512 threads. The scalar-clock JSONs have no
  `hb_races`; their `hb_sync_pass` lists the same pc pairs.
- Attribution: `attrib/cccl-3-{buggy,fixed}.json`, full inlined frames.
- Rows per group: main and certain vector-clock, plus main scalar-clock. All `a2_uncertain` = 0.

## Common mechanism of #01-#05 and #07-#10: the last block's acquire side

All nine groups are cross-block pairs, `dist` = grid, in one `DeviceTopKKernel` launch. In each pair, a non-last block
accesses a `Counter` field early in the pass. The last block, found by `atomicInc(&counter->finished_block_cnt)`, then
writes the same field.

| | buggy pc | fixed pc | source |
|---|---|---|---|
| fence | `MEMBAR.SC.GPU` 0xac00 | 0xac00 | `__threadfence()` L652 |
| barrier (fixed only) | none | `BAR.SYNC` 0xac40 | added at fixed L654 |
| counter | `ATOMG.E.INC.STRONG.GPU [R20.64+0x100]` 0xac70 | 0xac80 | `atomicInc` L658, thread 0 |
| barrier | `BAR.RED.OR` 0xaca0 | 0xacb0 | `__syncthreads_or` L663 |
| plain stores to `counter` | 0xad90-0xadc0, 0xbc40, 0xbc60 | +0x10 | L795-L801, L615-L621 |

- Each `DeviceTopKKernel` has exactly one `MEMBAR`, at 0xac00, and it comes before the `atomicInc` (grep of both dots).
  Nothing with acquire semantics follows the `atomicInc` in the last block.
- Release side (block X): the thread's access is followed by block barriers (`__syncthreads` L468 at 0x140, then L577
  among later ones; the last `BAR.SYNC` before the fence is at 0x9ec0), then thread 0's `fence.sc.gpu` and the relaxed
  `atomicInc`. That is a release pattern.
- Acquire side (last block L): `atomicInc`, then `bar.red`, then plain stores. There is no fence after the atomic and the
  atomic is relaxed, so there is no acquire pattern. X's release therefore synchronizes with nothing in L.
- Fence-SC order between X's and L's `fence.sc`: both fences come before their own `atomicInc`. An execution where L's
  fence is earlier in Fence-SC order but X's `atomicInc` is earlier in the counter's RMW order is allowed. In that
  execution, X's access and L's store are not related by causality order. My reading of the PTX ISA definitions: the
  observation-order term of causality order is not transitive with a base-causality prefix, so the chain
  "X's access, then X's atomic, then L's atomic" does not order X's access.
- Every pair has at least one plain access, so it is a DR under PTX §8.7.1 (my reading of the ISA text; not
  machine-checked).
- cuVein's model agrees: it needs atomic + fence on the acquire side.

Relation to the registered work:
- This is the same gap that makes the registered fixed-build residual racy: merge atomicAdd vs volatile load, and merge
  atomicAdd vs init_histograms store.
- It is the open REVIEW.md decision 2, "strict PTX vs the fence + counter idiom", which already says of raft-1 that
  "the last block's relaxed atomicInc has no fence after it".
- If Jeffery takes the idiom reading ("absent"), these nine groups move to class (b). The mechanism to name would be:
  the threadfence-reduction idiom (release fence + counter, and a control dependency on the counter value in the last
  block in place of an acquire fence), which cuVein does not model. They should be decided together with the residual.
- Inferred: no observable failure on current hardware. The last block's stores are control-dependent on the
  `atomicInc` result through `BAR.RED.OR` / `@!P2 EXIT`, and X's loads are consumed before X's fence.

One-line fix for all nine groups (inferred): in `finalize_pass`, make thread 0 run `__threadfence()` right after its
`atomicInc` (`finished = atomicInc(...); __threadfence();`), before `__syncthreads_or`. That gives an acquire pattern,
and the barrier then carries it to the bin thread. The same line would also order the registered residual.

## cccl-3#01: agent_topk.cuh:618 vs agent_topk.cuh:754 (3 rows, buggy)

- Accesses:
  - A: L754 `counter->k`, `LDG.E.128 [R20.64]` at 0x40, which also loads `len` at +8; frames `agent_topk.cuh:754 <-
    dispatch_topk.cuh:291`. All threads at kernel start, global.
  - B: L618 `counter->len = cur - prev`, merged by the compiler with L615 `counter->k = k - prev` into `STG.E.128
    [R20.64]` at 0xbc40; frames `618 <- 628 <- 677 <- 792 <- dispatch_topk.cuh:291` (choose_bucket). Global WAR.
- Thread relation: kernel_1 (pass 1), A = block 0 thread 0, B = block 34 thread 151 (the bin thread of the last block).
  `count` 24576 = 48 blocks x 512 threads; every thread of every other block conflicts. dist grid.
- Ordering: see the common mechanism. The read precedes X's barriers, fence and atomicInc; nothing acquires in L.
- Class (a) DR, both plain. Thread pair: block 0 t0 reads at L754, block 34 t151 writes at L618. Fix: the
  `__threadfence()` after `atomicInc` above.

## cccl-3#02: agent_topk.cuh:756 vs agent_topk.cuh:800 (3 rows, buggy)

- Accesses:
  - A: L756 `counter->previous_len`, `LDG.E.64 [R20.64+0x10]` at 0x80.
  - B: L800 `counter->previous_len = current_len` (counter_update_fn, thread 0 of the last block), `@P0 STG.E.64
    [R20.64+0x10]` at 0xad90; frames `800 <- 667 <- 792`. Global WAR.
- Thread relation: kernel_1, block 0 t0 vs block 34 t0, count 24576, dist grid.
- Class (a) DR. Same mechanism and fix as #01.

## cccl-3#03: agent_topk.cuh:756 vs agent_topk.cuh:795 (3 rows, buggy)

- Accesses:
  - A: L756 read as in #02.
  - B: L795 `counter->previous_len = 0` (early-stop branch of counter_update_fn), `@!P0 STG.E.64 [R20.64+0x10], RZ` at
    0xadc0. Global WAR.
- Thread relation: kernel_2 (pass 2, where block 0 is last), block 1 t0 vs block 0 t0, count 24576, dist grid.
- Class (a) DR. Same mechanism and fix.

## cccl-3#04: agent_topk.cuh:801 vs device_atomic_functions.hpp:226 (18 rows, buggy)

- Accesses:
  - A: `atomicAdd(p_filter_cnt, 1)` at L498 (f_with_out_buf), `ATOMG.E.ADD.64.STRONG.GPU [R20.64+0x80]`. Six inlined
    copies: 0x5d50/0x6190/0x65d0/0x6a10 via process_range L382 (full tiles) and 0x71b0/0x7620 via L407 (last tile).
  - B: L801 `counter->filter_cnt = 0` (thread 0 of the last block), `@P0 STG.E.64 [R20.64+0x80], RZ` at 0xada0.
    Global WAW.
- Thread relation: kernel_1, B = block 34 t0, A for example block 0 t29, block 1 t495, block 7 t357, block 48 t218. All
  dist grid.
- Ordering: the atomicAdd precedes the L577 barrier, then thread 0's fence and atomicInc. The missing barrier of the
  oracle bug does not matter here, because these atomics come before L577. The acquire side is missing as above.
- Class (a) DR: one strong access and one weak, so not morally strong, and unordered. Fix as #01.

## cccl-3#05: agent_topk.cuh:141 vs dispatch_topk.cuh:147 (12 rows, buggy and fixed)

- Accesses:
  - A: `*kth_key_bits` in `identify_candidates_op_t::operator()` (dispatch_topk.cuh:147), called from f_with_out_buf
    (agent_topk.cuh:495). `LDG.E` at 0x6740 (L382 path) and 0x7c50 (L407 path), address counter+0x18.
  - B: `prefix.bits |= bucket << start_bit` in set_kth_key_bits (agent_topk.cuh:141 <- L621 <- L628 <- L677), `STG.E
    [R20.64+0x18]` at 0xbc60 (fixed 0xbc70). Global WAR.
- Thread relation: kernel_1. A = block 0 t0 (count 24064) or block 48 t0 (count 424); B = block 34 t151 (buggy) or
  block 6 t151 (fixed). dist grid.
- Class (a) DR, same mechanism. The lines are unchanged by the fix, so one group covers both builds (6 rows each).

## cccl-3#06: device_atomic_functions.hpp:226 vs device_atomic_functions.hpp:226 (156 rows, buggy and fixed)

- Accesses: `atomicAdd(temp_storage.histogram + bucket, OffsetT{1})` in invoke_histogram_only (agent_topk.cuh:818,
  fixed :820). OffsetT is `unsigned long long`, so this is device_atomic_functions.hpp:226 `__ullAtomicAdd`, on shared
  memory, in `DeviceTopKHistogramKernel`.
- SASS (identical in both builds):
  - Each of the 8 inlined copies (0x510-0x7b0 for full tiles, 0xc10-0xee0 for the last tile) is the sequence `LDS.64
    R8,[R19]`, `IADD3/IMAD.X +1`, `ATOMS.CAST.SPIN.64 R10,[R19],R8,R10`, `ISETP R10 == 1`, `@!P0 BRA` back to the LDS.
  - The 32 distinct pc pairs are every LDS.64 x CAS combination across items. The ops are only `LDS.64~ATOMS.CAST.SPIN.64`
    in either order (shared RAW 88, WAR 68).
- Thread relation: same block, cross-warp or same warp. Examples: block 22 t266 LDS (0x510) vs t355 CAS (0x540), WAR,
  dist block; block 33 t339 vs t321, dist warp; block 48 t58 vs t260 (0xc10/0xc40).
- Ordering: at the PTX level every access here is one atomic add (inferred from the source; the dot holds SASS only).
  The LDS.64 only seeds the CAS expected value, and a stale value makes the CAS fail and retry.
- Class (c): the known false-report class from the brief. cuVein treats the seeding `LDS.64` of ptxas's CAS emulation as
  a plain load, not as part of the RMW. Not a race. Minimal failing input in Defects.

## cccl-3#07, #08, #09, #10: fixed-build twins of #01, #02, #03, #04 (3, 3, 3, 18 rows)

The fix shifts every line from L653 on by +2, so the twins land in other groups. The mechanism is the same.

| group | access A | access B | pcs | thread example | class |
|---|---|---|---|---|---|
| #07 | L756 | L618 | 0x40 / 0xbc50 | kernel_1, block 0 t0 vs block 6 t151 | (a) DR |
| #08 | L758 | L802 | 0x80 / 0xada0 | block 0 t0 vs block 6 t0 | (a) DR |
| #09 | L758 | L797 | 0x80 / 0xadd0 | kernel_2, block 1 t0 vs block 0 t0 | (a) DR |
| #10 | L498 atomicAdd | L803 | 0x5d50... / 0xadb0 | e.g. block 0 t29 vs block 6 t0 | (a) DR |

- The fix's new `BAR.SYNC` (0xac40) sits between the fence and the `atomicInc` and orders nothing on the acquire side.
- Fix: the same one line as above.

## Defects

### D-cccl3-1, class (c), detector: emulated 64-bit shared atomicAdd load is not part of the RMW (group #06, 156 rows)

```cuda
__global__ void k(unsigned long long *out) {
  __shared__ unsigned long long h;
  if (threadIdx.x == 0) h = 0;
  __syncthreads();
  atomicAdd(&h, 1ull);   // sm_89: LDS.64 + ATOMS.CAST.SPIN.64 retry loop
  __syncthreads();
  if (threadIdx.x == 0) *out = h;
}
// k<<<1, 64>>>(d_out);
```

- Expected: no report.
- cuVein's behaviour (inferred): it pairs `LDS.64` with other threads' `ATOMS.CAST.SPIN.64` as a DR, as in
  `DeviceTopKHistogramKernel` 0x510/0x540. Not run here (no GPU jobs).
- Fix direction: treat the LDS that seeds an `ATOMS.CAST(.SPIN)` loop on the same address as part of the atomic, or drop
  it from conflict checks.

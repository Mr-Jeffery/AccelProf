# kokkos-5: triage of 10 other reports (6 groups)

- Repo: kokkos/kokkos. Buggy commit 87415792, fixed commit db1a77dd.
- File: `core/src/Cuda/Kokkos_Cuda_ReduceScan.hpp` (abbreviated `rs`). The fix adds `if (lane_id != 0)` around the broadcast at L551, so buggy L >= 552 is fixed L+2.
- Other files: `core/src/impl/Kokkos_FunctorAdapter.hpp` (`fad`), and desul `core/src/desul/atomics/cuda/cuda_cc7_asm_atomic_fetch_op.inc_isglobal`.
- Kernel: the driver's `ParallelReduce<RwSumFunctor, RangePolicy<Cuda>>` (kernel_3), grid (4,1,1), block (1,256,1).
- Path: `CudaReductionsFunctor<...,false,false>::scalar_inter_block_reduction`, rs:579-621 buggy. It is a last-block-done reduction.
- Tids: `(block << 10) | threadIdx.y`.

**SASS (`driver.sm_89.dot`, buggy pcs; fixed pcs are +0x10):**

| pc | instruction | source |
|---|---|---|
| 0xa90 | `@!P0 STG.E.64` | rs:575 `*result = ...` |
| 0xac0 | `MEMBAR.SC.GPU` | rs:596 `__threadfence()` |
| 0xb10 | `BAR.SYNC` | rs:597 |
| 0xbc0 | `@P0 ATOMG.E.ADD.STRONG.GPU` | rs:604, `Kokkos::atomic_fetch_add` = desul `MemoryOrderRelaxed` per `Kokkos_Atomics_Desul_Wrapper.hpp`; thread 0 |
| 0xc50 | `BAR.RED.OR` | rs:608 `__syncthreads_or` |
| 0xc90 | `STG.E [flags], RZ` | rs:610, by every thread of the last block |
| 0xd40 | `LDG.E.64.STRONG.SYS` | fad:1571 volatile join read <- rs:614 |

There is no `MEMBAR` between 0xbc0 and 0xd40. cuVein's `hb_rmw_points` acquire lists for the RMW 0xbc0 (3008) contain only pcs 0x1690 and 0x16a0, not 0xc90 or 0xd40.

| class | groups | rows |
|---|---|---|
| (a) DR | #01 #03 #04 #06 | 8 |
| (b) | #02 #05 | 2 |

## kokkos-5#01: rs:575 vs fad:1571 (2 rows, buggy: ve, sc)

- **Accesses:** A: rs:575 `if (threadIdx.x + threadIdx.y == 0) *result = *shared_team_buffer_element;` (<- rs:593), where `result = global_team_buffer_element + blockIdx.x`. Plain STG.E.64, global. B: fad:1571 `*((volatile T*)lhs) += *((const volatile T*)rhs)` with rhs = `&global_team_buffer_element[i]` (<- rs:614, last block). `LDG.E.64.STRONG.SYS`, global.
- **Threads:** a_tid 0 (block 0, thread 0) vs b_tid 2048 (block 2, thread 0), dist=grid, count 3, a2_uncertain 0. Block 2 is the last block.
- **Ordering:**
  - Release present: thread 0's store, then `MEMBAR.SC.GPU`, then `BAR.SYNC`, then the relaxed atomic, all in one thread.
  - Acquire missing: the last block's thread 0 does the relaxed atomic, then `BAR.RED`, with no fence.
  - So B is not after A in causality order. One side is plain.
- **Class:** (a) DR under strict PTX. This is the fence + counter idiom question of REVIEW item 2, the same as raft-1's and cmssw-1's residuals.
  - The pair is not registered: kokkos-5's fixed residual is rs:577 vs Kokkos_Cuda_Parallel_Range.hpp:321, and its both-build pairs are rs:547 and rs:547 vs rs:551-552.
  - Same in fixed: yes (#04).
- **Concrete pair:** block 0 thread 0 writes global_team_buffer[0] (L575); last block 2 thread 0 reads it in the join loop (L614 -> fad:1571).
- **Fix:** after `Kokkos::atomic_fetch_add(global_flags, 1u)` in rs:603-605, add `Kokkos::memory_fence();`, or use an acq_rel fetch_add.

## kokkos-5#02: desul fetch_op:192 (atomic at rs:604) vs rs:610 (1 row, buggy ve)

- **Accesses:** A: `Kokkos::atomic_fetch_add(global_flags, 1u)` (chain cuda_cc7_asm_atomic_fetch_op.inc_isglobal:192 <- Kokkos_Atomics_Desul_Wrapper.hpp:61 <- rs:604), `ATOMG.E.ADD.STRONG.GPU` at 0xbc0. B: rs:610 `*global_flags = 0;`, plain STG.E at 0xc90, by every thread of the last block.
- **Threads:** a_tid 1024 (block 1, thread 0) vs b_tid 2080 (block 2, threadIdx.y 32), dist=grid, count 768, a2_uncertain 0.
- **What orders them:** A is block 1's increment of `global_flags`.
  - The last block's thread-0 RMW (the final increment, which reads gridDim.x-1) reads the value of the RMW chain that contains A. Every hop is a gpu-scope relaxed atomic on the same location, so the hops are morally strong. A therefore precedes the last block's RMW in PTX observation order.
  - That RMW precedes B in base causality: program order, then `BAR.RED.OR` (barrier synchronization), then thread 32's program order.
  - PTX's causality order includes "X precedes Z in observation order and Z precedes Y in base causality order". So A precedes B in causality order, and the pair is not a data race in any execution, because the last increment always reads after every other block's increment.
  - The clause is recalled from the PTX ISA memory consistency model (causality order definition); it should be checked against the ISA text before this is scored.
- **Why cuVein reports it:** its (ATOM) edges are only instance-gated release/acquire patterns (design/proof/hb_proof.tex, Containment T12). That needs an acquire fence on the last block's path after the RMW, and there is none. The observation-order clause, where the observed write itself is the conflicting access, is not modelled.
- **Class:** (b), ordered by PTX observation order (the RMW chain plus a barrier), which cuVein does not model. Stated model gap. Confidence medium, because it rests on the recalled clause. Same in fixed: yes (#05).
- **Minimal input (expected: no report; by #02's mechanism cuVein is expected to report a WAW DR between the first block's atomicAdd and the last block's thread 32 store; inferred, not run):**

```cuda
__global__ void k(unsigned* flag) {          // launch <<<2, 64>>>, *flag == 0
  __shared__ bool last;
  if (threadIdx.x == 0) last = (atomicAdd(flag, 1u) == gridDim.x - 1);
  __syncthreads();
  if (last && threadIdx.x == 32) *flag = 0;  // ordered after the other block's atomicAdd by observation order
}
```

## kokkos-5#03: rs:610 vs rs:610 (2 rows, buggy: ve, sc)

- **Accesses:** both are rs:610 `*global_flags = 0;`, plain STG.E RZ at 0xc90, global.
- **Threads:** warp: 2080 vs 2081 (block 2, threadIdx.y 32 and 33). Block: 2080 vs 2144 (threadIdx.y 32 and 96). count 3968 and 28672.
- **Ordering:** none. Every thread of the last block executes the store after `__syncthreads_or`, and nothing orders the stores among themselves.
- **Class:** (a) DR, same-value (0) write-write. Same in fixed: yes (#06).
- **Fix:** `if (threadIdx.x + threadIdx.y == 0) *global_flags = 0;`

## kokkos-5#04: rs:577 vs fad:1571 (2 rows, fixed: ve, sc)

- Fixed twin of #01: `STG.E.64` at 0xaa0 (rs:577 <- rs:595) vs `LDG.E.64.STRONG.SYS` at 0xd50 (fad:1571 <- rs:616).
- **Threads:** 0 vs 2048, dist=grid. **Ordering:** as in #01; the fixed SASS has `MEMBAR.SC.GPU` at 0xad0 and nothing after `ATOMG` 0xbd0.
- **Class:** (a) DR under strict PTX (REVIEW item 2). Fix: as in #01.

## kokkos-5#05: desul fetch_op:192 (rs:606) vs rs:612 (1 row, fixed ve)

- Fixed twin of #02: `ATOMG.E.ADD.STRONG.GPU` 0xbd0 vs `STG.E` 0xca0.
- **Threads:** 1024 vs 2144 (block 2, threadIdx.y 96), dist=grid.
- **Class:** (b), observation order; model gap as in #02.

## kokkos-5#06: rs:612 vs rs:612 (2 rows, fixed: ve, sc)

- Fixed twin of #03: `STG.E RZ` at 0xca0.
- **Threads:** warp 2144 vs 2145, block 2144 vs 2112.
- **Class:** (a) DR, same-value. Fix: as in #03.

## Defects

- **Model gap G-kokkos-5-1 (#02, #05; 2 rows):** PTX causality order's observation clause is not modelled.
  - A morally strong RMW chain from another block's atomic to the last block's atomic, followed by a barrier, orders that atomic before later accesses of the last block. cuVein orders only through fenced release/acquire patterns.
  - It is not a defect in the implemented semantics (hb_proof.tex scopes (ATOM) to gated patterns), so it is listed as a model gap. Minimal input: under #02.

# Triage: cuml-tsne-new-1 (T21c step 3)

Pinned commit: rapidsai/cuml `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Route R2:
- Five files byte-identical: `targets/cuml-tsne-new-1/r2/verbatim.check`, including `cpp/src/tsne/barnes_hut_kernels.cuh` and `barnes_hut_tsne.cuh`.
- Stubs for RAFT/RMM/cuML headers in `r2/common/stubs/`.
- Host driver `r2/common/main.cu`: `driver 1000 1`, i.e. 1,000 points, max_iter 1, one launch of every BH kernel.

Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`). 23 kernel JSONs, `n_race = 67`, `n_sc = 28`, 95 reports:
- 4 in `RepulsionKernel`, the oracle's kernel; all four are on oracle pairs (primary pair and `additional_pairs`).
- 91 in `other_reports.csv`: `SortKernel` 4, `BoundingBoxKernel` 8, `TreeBuildingKernel` 16, `SummarizationKernel` 63.
- No reports in the cub/raft-stub/Integration/attractive/Clear/Init kernels.

## Groups

pcs are decimal, as in the attribution JSON; hex where useful. "a → b" is ancient → current access.

| # | kernel | pcs | file:line pair (`barnes_hut_kernels.cuh`) | count | class | reason |
|---|---|---|---|---|---|---|
| R1 | `RepulsionKernel` | `LDS` 3024 / `STS` 3072 | 596 / 596 | 1 (matched, oracle primary) | **(a) DR, value-benign** | Warp 0 lane d writes `dq[d] = dq[d]` while lane d of warps 1..31 reads `dq[d]`. The `__syncthreads` at L598 is commented out; L599 `__threadfence_block` is `MEMBAR.SC.CTA`, a fence by one thread. The value written equals the value read. |
| R2 | `RepulsionKernel` | `STS` 3072 → `LDS` 4192 | 596 → 647 | 1 (oracle `additional_pairs`) | **(a) DR**, intra-warp | Lane d of warp w writes `dq[sbase+d]`. Another lane reads `dq[depth]` (`depth = sbase + level`) as the argument of `__all_sync` before the vote. For warps ≥ 1 the written value is new, not benign. Fix and dossier together with R1. |
| R3 | `RepulsionKernel` | `STS` 3536 → `LDS` 3600; `STS` 3552 → `LDS` 3648 | 625 → 631; 626 → 632 | 2 (oracle `additional_pairs`) | **(a) DR**, intra-warp, warp-synchronous | Lane 0 pushes the root (`pos[sbase]`, `node[sbase]`). All lanes then read the stack top. There is no `__syncwarp` and no `WARPSYNC`. |
| B1 | `BoundingBoxKernel` | `STS` 608/656/672/688 → `LDS` 848/896/944/992 | 122–125 → 130–133 | 4 | **(a) DR**, cross-warp | Thread k ≥ 256 stores `sminx[k]` etc. and never executes a barrier (`for (j = 256; j > i; …)` has 0 iterations for i ≥ 256). Thread i < 256 reads `sminx[i+256]` after a `__syncthreads` that k did not join. **New race, not in the oracle.** |
| B2 | `BoundingBoxKernel` | `STS` 880/928/976/1024 → `LDS` 848/896/944/992 | 130–133 → 130–133 | 4 | **(a) DR**, same finding as B1 | Loop-carried: thread k = i+j writes `sminx[k]` in iteration 2j and then leaves the loop (2j > k but j ≤ k). Thread i reads it after iteration j's barrier, which k does not execute. |
| T1 | `TreeBuildingKernel` | `LDG` 720/912 (L239) vs `ATOMG.CAS` 1232 (L268), 2656 (L259) | 239 vs 259/268 | 4 | **(a) DR** | Lock-free insertion. `childd` is a plain `int*` (the reference `cannylab/bh.cu` L218 has `volatile`). The traversal reads it with plain `LDG.E` while other threads CAS it. |
| T2 | `TreeBuildingKernel` | `LDG` 720/912 vs `STG` 2096/2240/2544/2880 | 239 vs 283/291/303/315 | 7 | **(a) DR** | The same plain reads vs plain publication stores. The unlock `childd[locked] = patch` (L315) is a plain store after `MEMBAR.SC.GPU`; that is not a release pattern, which would need a strong write. |
| T3 | `TreeBuildingKernel` | `ATOMG.CAS` 1232 vs `STG` 2240/2544 | 268 vs 291/303 | 2 | **(a) DR** | A CAS on a slot vs a plain store to it from another thread. Mixed atomic/plain, not morally strong. |
| T4 | `TreeBuildingKernel` | `STG` 2240/2544 → `STG` 2880; `LDG` 2400 → `STG` 2880 | 291/303 → 315; 299 → 315 | 3 | **(a) DR** | Plain stores and loads of `childd` by different threads, ordered only by a fence in one of them. |
| S1 | `SummarizationKernel` | `LDG.E.STRONG.SYS` 592/816/1040/1280 (L383), 3728/3888/4192/4384 (L442), 4672/4688/4736/4752 (L434) vs `STG.E.STRONG.SYS` 3040 (L411), 7456 (L477) | 383/434/442 vs 411/477 | 24 | **(a) SC**, by-design flag | `massd` is `volatile`, so both sides are strong (relaxed.sys). This is the publication flag the algorithm polls. Strong vs strong: not a data race. Intended, benign by design. |
| S2 | `SummarizationKernel` | `LDG.E` 1568/1616/1632/1856/1888/1920/2128/2160/2192/2464/2512/2528 (L397/401/402) and 5552/5600/5616/5920/5968/6000/6320/6368/6400/6720/6768/6800 (L459/462/463) vs `STG.E` 2672/2960/2976 (L406/408/409) and 6944/7296/7312 (L467/469/470) | 397/401/402, 459/462/463 vs 406/408/409, 467/469/470 | 39 | **(a) DR** | The payload of that flag: `countd`, `posxd`, `posyd`. The producer has a release pattern: plain stores, `MEMBAR.SC.GPU` (L410/L475), then the strong `massd` store. The consumer has no acquire: it reads `massd` (strong) and then the payload (plain) with no fence in between. |
| P1 | `SortKernel` | `LDG.E.STRONG.SYS` 320 (L509) vs `STG.E.STRONG.SYS` 592/992/1424/1808 (L522) | 509 vs 522 | 4 | **(a) SC**, by-design flag | `startd` is `volatile`: the parent publishes `startd[ch]`, the child polls `startd[k]`. Strong vs strong. The child reads no payload from other threads of this kernel: `countd`/`childd` come from earlier kernels or from its own thread. Benign by design. |

Class counts over the 95 reports:
- (a) 12 groups. DR groups: R1, R2, R3, B1, B2, T1–T4, S2, totalling 4 + 8 + 16 + 39 = 67 reports. SC groups: S1, P1, 28 reports, both by-design flag synchronization.
- One DR group is value-benign (R1). No group is a same-value WAW.
- (b) 0, (c) 0, (d) 0.

Dossiers (one per distinct race):
- R1 + R2, the `dq` copy without its barrier (one fix: restore L598): `eval/realworld/findings/cuml-tsne-new-1.md`
- R3, the per-warp stack, intra-warp: `findings/cuml-tsne-new-1-2.md`
- B1 + B2, `BoundingBoxKernel`'s barrier in a thread-dependent loop: `findings/cuml-tsne-new-1-3.md`
- S2, `SummarizationKernel` payload without acquire: `findings/cuml-tsne-new-1-4.md`. S1 is discussed there, no separate dossier: the SC conflict is the intended flag itself.
- T1–T4, `TreeBuildingKernel` plain `childd` publication: `findings/cuml-tsne-new-1-5.md`
- P1: no dossier. It is an SC flag with no payload race in the kernel; classed (a)-SC, by design.

## Reasoning per kernel

### RepulsionKernel (R1–R3)

- **SASS.** `BAR.SYNC` 0xb90 (L585), then `LDS` 0xbd0 / `STS` 0xc00 (L596) and `MEMBAR.SC.CTA` 0xc10 (L599). Then `@!P0 STS` 0xdd0 / 0xde0 (L625/L626, lane 0) and `LDS` 0xe10 / 0xe40 (L631/L632).
  - In the vote: `VOTE.ANY` 0x1050 (`__activemask`), then the `LDS` of `dq[depth]` at 0x1060, then `BRA.DIV` and the converged-path `VOTE.ALL` at 0x10a0. The divergent path calls `__cuda_sm70_votesync_all`.
  - There is no `WARPSYNC` on the converged path. The `WARPSYNC` at 0x1700/0x1740 belong to the post-loop `__shfl_down_sync`.
  - The reads at L631/L632/L647 come before any vote of the same body iteration.
- **R1 pair.** Block 0: thread 5 (warp 0) executes `dq[5] = dq[5]`; thread 37 (warp 1) loads `dq[5]` for `dq[37] = dq[5]`.
  - The last barrier is L585. L598 is commented out. `MEMBAR.SC.CTA` is a fence by one thread, which synchronizes with nothing on its own.
  - So the pair is a DR.
  - The written value equals the old value, so no output can change. Trace edge `3072←3024`: `intra_block 2112`.
- **R2.** Warp 1 lane 5 writes `dq[37]` (L596). Lane 0 of warp 1 reads `dq[32 + level]`, e.g. `dq[37]` at level 5, as the `__all_sync` argument (L647).
  - Intra-warp, no `WARPSYNC`, so a DR.
  - Before the write, `dq[32..63]` is uninitialised shared memory. A lagging writer gives a wrong vote and a wrong force: not value-benign. Formal in practice, since the warp is converged.
  - Site verdict `edge_rescued: true`, weight 1. The dependency edge saw the conflict only intra-thread (`intra_thread 32`); the event stream showed the cross-lane conflict.
- **R3.** Warp 1: lane 0 (thread 32) writes `pos[32] = 0`, `node[32] = FOUR_NNODES` (L625/L626). Lane 1 (thread 33) reads `pos[32]`, `node[32]` (L631/L632). DR, warp-synchronous. Site verdicts are `edge_rescued`, weight 1.
- **Coverage.** The pushes at L655/L656 (`STS` 0x1110/0x1130) never executed: they are absent from `kernel_10.json`'s `nodes`.
  - Every `__all_sync` returned true, so the walk accepted all of the root's children. Only 32 warp-instances ran the body (1000 bodies / 32).
  - The push → L631 pairs of the oracle's `additional_pairs` were therefore not exercised. The reproducer for -2 exercises them.

### BoundingBoxKernel (B1, B2): the racecheck hazards

- **The L122 vs L130 hazards.** Racecheck's 2,000 displayed hazards (all `Potential RAW hazard`, `BoundingBoxKernel<int,float>+0x260` (L122) write vs `+0x350` (L130) read) are **this kernel**, not `RepulsionKernel`.
  - It is the first BH kernel with shared memory, and it alone filled the print limit: 800,261 errors and 382 warnings in total.
  - Racecheck therefore says **nothing** about `RepulsionKernel` in this run. A run with `--print-limit 0` or a kernel filter would show it. Not run.
- **SASS.** `STS` 0x260/0x290/0x2a0/0x2b0 (L122–L125), then the loop: `WARPSYNC 0xffffffff` 0x2f0 + `BAR.SYNC` 0x300 (L128), then `LDS` / `STS` pairs 0x350–0x400 (L130–L133). Then `@P1 EXIT` 0x420 for i ≠ 0.
  - The `WARPSYNC` was inserted by ptxas before the barrier in divergent code.
- **B1 pair.** Thread 300 (warp 9) stores `sminx[300]` (L122). For i = 300 the loop condition `256 > 300` is false, so thread 300 executes no `BAR.SYNC` and exits.
  - Thread 44 (warp 1) executes iteration j = 256 (`BAR.SYNC`) and reads `sminx[300]` (L130).
  - No barrier operation of thread 300 exists, so there is no synchronizes-with edge (PTX §8.7: only `bar`/`barrier` operations synchronize at CTA scope). Plain vs plain: DR.
- **B2 pair.** Thread 3 writes `sminx[3]` in iteration j = 4 (4 > 3), then leaves the loop (2 > 3 is false) and exits. Thread 1 reads `sminx[1+2]` after iteration j = 2's barrier, which thread 3 never reaches.
- **Practical ordering.** The exit rule orders it in practice. By the PTX `exit` description (paraphrased; the current ISA page was not re-read verbatim), a barrier that waits only on exiting threads is released when they exit. So `bar.sync` completes only after thread 300 has exited, after its store.
  - The memory model gives exit no ordering.
  - The CUDA C++ Programming Guide (synchronization functions) allows `__syncthreads()` in conditional code "only if the conditional evaluates identically across the entire thread block". Wording as quoted in NVIDIA forum threads; the current guide was not re-read.
  - The reference `cpp/src/tsne/cannylab/bh.cu` L134–L136 at the same commit uses the uniform form `for (j = THREADS1 / 2; j > 0; j /= 2) { __syncthreads(); if (i < j) { … } }`. The cuML port moved `i < j` into the loop condition.
  - Trace edges: `848←608` `intra_block 26112`; `848←880` `intra_warp 3162, intra_block 22848`.
- **Non-report observation.**
  - The kernel's cross-block combine (L139–L142 `STG` by thread 0, `MEMBAR.SC.GPU` + `ATOMG.INC` L143–L146, then the last block's `LDG` L150–L153) executed (edges `1536←1168`, `intra_grid 25`). It produced no report.
  - The writer side has a release pattern (fence.sc + strong RMW). The last block has no acquire fence after its `atomicInc`.
  - This is the missing-acquire shape of T21 corpus note 3 (`cccl-3`, `cmssw-1`, `raft-1`). The detector treats it as ordered.
  - Class not assigned (not a report). Whether the paper counts strict-PTX missing-acquire as a race is the open note-3 decision.

### TreeBuildingKernel (T1–T4)

- **SASS.** `childd` loads are `LDG.E` (weak) at 0x2d0, 0x390 (L239) and 0x960 (L299).
  - CAS: `ATOMG.E.CAS.STRONG.GPU` 0x4d0 (L268) and 0xa60 (L259).
  - Stores: plain `STG.E` 0x830/0x8c0/0x9f0 (L283/L291/L303) and 0xb40 (L315).
  - `__threadfence` is `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL` (0xaf0–0xb20, L313).
- **Pair (T2).** Thread A inserts body i into a full slot. It locks `childd[locked]` (CAS → −2), allocates a cell c, stores `childd[c*4+j] = ch` (L291) and `childd[c*4+j'] = i` (L303), fences, and unlocks with `childd[locked] = c` (L315, plain).
  - Thread B (another block; edges show `intra_grid` and `intra_block`) reads `childd[locked]` (L239, plain). If it sees c, it continues to `childd[c*4+j]` (L239, plain).
  - A's fence followed by a *plain* store is not a release pattern. B's plain reads are not strong and are not followed by a fence. So nothing orders A's L291/L303 stores before B's reads: DR.
  - The same holds for the CAS pairs (T1, T3): an atomic vs a plain access by another thread is not morally strong.
- **By design.** This is the Burtscher lock-free insertion. The original declares `childd` volatile (cannylab `bh.cu` L218 `volatile int* const __restrict__ childd`); the port dropped it. Correctness relies on the CAS re-validating stale reads and on `CCTL.IVALL` at each outer iteration.

### SummarizationKernel (S1, S2)

- **SASS.** `massd` accesses are `LDG.E.STRONG.SYS` / `STG.E.STRONG.SYS`. The payload uses plain `LDG.E` / `STG.E`. `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL` sit at 0xbb0 (L410) and in the main loop (L475).
- **S2 pair.** Thread P (cell k) stores `countd[k]`, `posxd[k]`, `posyd[k]` (L406–L409), fences (L410) and stores `massd[k] = cm` (L411, strong): a release pattern.
  - Thread C (parent cell) reads `massd[k]` (L383, strong) into shared `mass[]`. In the same iteration it reads `countd[k]`, `posxd[k]`, `posyd[k]` (L397–L402, plain) **with no fence between**. That is not an acquire pattern, so there is no synchronizes-with: DR on the payload.
  - In the main loop, a child whose `massd` was read in an earlier iteration is ordered by L475's fence. The reported pairs come from the same-iteration case.
  - Hardware view, not tested: the payload `LDG.E` may hit an L1 line another warp of the same SM loaded after the last `CCTL.IVALL`, so a stale read is possible in principle.
  - The reference `bh.cu` makes the payload `volatile float4 posMassd` and `volatile int countd` (L388–L390), so all of it is strong.
- **S1** is the flag itself, strong vs strong: an SC conflict, intended.

### SortKernel (P1)

- `startd` is volatile. The parent stores `startd[ch] = start` (L522, `STG.E.STRONG.SYS`); the child polls `startd[k]` (L509, `LDG.E.STRONG.SYS`). SC, intended.
- After the flag the child reads only `childd[k*4+i]` (written by TreeBuilding or by itself at L517/L518) and `countd[ch]` (`LDG.E.CONSTANT`, from SummarizationKernel). So no cross-thread payload race exists inside this kernel.

## R2 harness check: do the stubs touch the racing code?

- **RepulsionKernel.** It uses `raft::WarpSize` only in the post-loop `__shfl_down_sync` reduction (L675, L678), not in the racing statements. The stub value 32 equals RAFT's.
- **The other kernels.** BoundingBox, TreeBuilding, Summarization and Sort use no stubbed symbol. `CUML_KERNEL` is `__global__ static`, copied from the pinned `cuml/common/utils.hpp`.
- **Atomics.** The kernels call `atomicCAS(int)`, `atomicAdd(int/float)`, `atomicExch(ull/float)`, `atomicInc(unsigned)` and `atomicMax(int)`. CUDA's built-ins match these exactly, so the empty `raft/util/device_atomics.cuh` stub does not change which atomic is called. RAFT's header at cuML's pin is not available locally, so its exact overload set was not checked.
- **Allocations.** `rmm::device_uvector` / `device_scalar` become plain `cudaMalloc`, which is uninitialised like RMM.
- **Host side.** `raft::handle_t`, the logger and `thrust` policies are host-only.
- **Stub kernels.** `stub_scalar_mul_kernel` ran twice with no reports. `stub_uniform_kernel` is compiled but unused under `TSNE_INIT::PCA`.
- **Conclusion.** No stub affects the racing code. Not covered by the stubs: the driver's host-built P, which replaces kNN, perplexity and symmetrisation, changes inputs only.
- **Native runs.** The checksum differed in the 7th digit across the 3 native runs (3.815908 vs 3.815909; `outputs_differ: true`). Float atomics in the attractive/Z_norm sums and the lock-free tree build order are nondeterministic. This is not attributed to any one race (not checked).

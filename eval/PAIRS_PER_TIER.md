# M4: reported pairs per configuration, one counting unit

Commands (repository root `~/wt-m2`, branch `study/r1-distance`, `.env/bin/python` of AccelProf, partition `normal`): `pairs_per_tier.py collect --workers 16 [--with-rw --retry]` (jobs 334254, 334293, 334508; `CUVEIN_DOT_PREFILTER=1` for the last, which re-ran the real-world ids and the failed ones), `pairs_per_tier.py names` (job 334254), `pairs_per_tier.py bclass` (jobs 335307, 335317, 335319, 335436), `pairs_per_tier.py report` (job 335436). The sources are the after state of `eval/R1_DISTANCE.md` (`eval/results/r1-distance/mode-pairs-after/`, fix/r1-at-widest-distance 886b6bf5). The page limit of the first brief is exceeded: Tables 1-2 and the cause splits are first, parts A and B follow.

Unit: (kernel name, unordered pc pair), launches merged, a pair under its worst class (data race = verdict RACE, strong conflict = verdict SC, RACE over SC). **cuRace alone** = collector-only recordings, setting S2 (`analyze(chain_closure=True, co_async=True, co_r3="off")`, the keywords `run_cuvein._analyze_reports` passes for `--chain-closure --co-async --co-r3 off`), re-scored here into `eval/results/pairs-per-tier/co/`: store `final-2026-11-co` for the benchmark suites and `realworld-2026-10-co` for the real-world targets (C2's `-n 1` collector-only recordings, the same recording generation as the `realworld-2026-10` clock-mode store M3 re-scored; the `-n 16` re-recordings `realworld-2026-11-co-sh` were not used: X12 found them equal to C2's). `merged-s2` of eval/co-chain-b has no per-pair output and no real-world ids, so it was not used. **Scalar clock / vector clock** = the per-pair output of `mode_pairs.py` in M3's after state (the scalar-clock pass is the vector-clock recording without `hb_races`). M3 changed 9 pair rows (5 real-world pairs of the vector-clock pass lost `model_bug`, 4 real-world pairs of the scalar-clock recordings went ORDERED to RACE; `eval/results/r1-distance/changes.csv`); the five pairs of M2 are among them. Population: programs with a result in all three configurations; P3 (ECL) and the canary program left out (counts in `Left out`). Real-world T21c (`realworld-2026-10-t21c`): M3's after state has no clock-mode result for it (M1's store list has only `realworld-2026-10`), so T21c is not in the population, and its collector-only store `realworld-2026-10-t21c-co` was not scored.

## Table 1: pairs per suite

| suite | programs | data races: cuRace alone | scalar clock | vector clock | strong conflicts: cuRace alone | scalar clock | vector clock |
|---|---|---|---|---|---|---|---|
| P1 | 400 | 1522 | 1295 | 1295 | 144 | 132 | 132 |
| P4 | 28 | 162 | 72 | 94 | 360 | 126 | 247 |
| P5 | 32 | 5 | 5 | 8 | 29 | 17 | 30 |
| P6 | 34 | 103 | 94 | 94 | 0 | 0 | 0 |
| P7 | 11 | 38 | 32 | 32 | 0 | 0 | 0 |
| P9 | 6 | 12 | 3 | 3 | 0 | 0 | 0 |
| PI | 4130 | 14166 | 16622 | 16624 | 0 | 0 | 0 |
| RW | 53 | 8745 | 2035 | 2100 | 676 | 536 | 536 |
| all | 4694 | 24753 | 20158 | 20250 | 1209 | 811 | 945 |

## Table 2: cuRace alone against the scalar clock

### data races

| suite | in both | only cuRace alone | only scalar clock | scalar-only (a) | (b) | (c) | co-only: barrier-ordered | derived | other |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 1295 | 227 | 0 | 0 | 0 | 0 | 52 | 175 | 0 |
| P4 | 59 | 103 | 13 | 8 | 0 | 5 | 47 | 44 | 12 |
| P5 | 4 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| P6 | 24 | 79 | 70 | 52 | 0 | 18 | 0 | 79 | 0 |
| P7 | 32 | 6 | 0 | 0 | 0 | 0 | 2 | 4 | 0 |
| P9 | 3 | 9 | 0 | 0 | 0 | 0 | 7 | 2 | 0 |
| PI | 12735 | 1431 | 3887 | 3882 | 0 | 5 | 840 | 546 | 45 |
| RW | 1866 | 6879 | 169 | 165 | 3 | 1 | 2639 | 4174 | 66 |
| all | 16018 | 8735 | 4140 | 4108 | 3 | 29 | 3587 | 5024 | 124 |

### strong conflicts

| suite | in both | only cuRace alone | only scalar clock | scalar-only (a) | (b) | (c) | co-only: barrier-ordered | derived | other |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 132 | 12 | 0 | 0 | 0 | 0 | 0 | 12 | 0 |
| P4 | 113 | 247 | 13 | 13 | 0 | 0 | 36 | 92 | 119 |
| P5 | 17 | 12 | 0 | 0 | 0 | 0 | 0 | 1 | 11 |
| P6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PI | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| RW | 534 | 142 | 2 | 2 | 0 | 0 | 20 | 122 | 0 |
| all | 796 | 413 | 15 | 15 | 0 | 0 | 56 | 227 | 130 |

### Only with the scalar clock: causes (a) no recorded edge and no chain joins the pair (no verdict record in cuRace alone); (b) cuRace alone certifies it by R1; (c) other. Only in cuRace alone: barrier clock ordered it in every recorded instance; derived by the closure (chain or rescue) and not a scalar-clock candidate; other.

- race / co_only / barrier: 3587 pairs; data: scalar clock: ORDERED, barrier-ordered in every instance x3587
  examples: P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x140/0x320 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x320/0x790 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x140/0x320 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x320/0x790 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x140/0x320 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x320/0x790 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x140/0x320 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0x320/0x790 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0xf0/0x910 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n cc_vertex_data(ECLgraph, int*, int*, int const*, i 0xf0/0x910
- race / co_only / derived: 5024 pairs; data: closure (chain), pair not a scalar-clock candidate x4695; closure (chain_rescue), pair not a scalar-clock candidate x329
  examples: P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_RaceBug_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_RaceBug_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_RaceBug_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_RaceBug_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x230 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x230 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x230 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xd0/0x230 | P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n bfs_vertex_data(ECLgraph, int*, int const*, int, i 0x90/0xbf0 | P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n bfs_vertex_data(ECLgraph, int*, int const*, int, i 0x90/0xbf0
- race / co_only / other: 124 pairs; data: scalar clock: ORDERED/None x79; recorded edge, pair not a scalar-clock candidate x45
  examples: P4-graph-connectivity-racy-large compressKernel(int*, int*, int*, int*, int*) 0x540/0x5c0 | P4-graph-connectivity-racy-large linkKernel(int*, int*, int*, int*, int*, int*, int 0x550/0x5d0 | P4-graph-connectivity-racy-small compressKernel(int*, int*, int*, int*, int*) 0x540/0x5c0 | P4-graph-connectivity-racy-small linkKernel(int*, int*, int*, int*, int*, int*, int 0x3f0/0x5d0 | P4-graph-connectivity-racy-small linkKernel(int*, int*, int*, int*, int*, int*, int 0x550/0x5d0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x1690/0x1f50 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x1690/0x2170 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x1690/0x21a0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x1f50/0x21a0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x1f50/0x33f0
- race / sc_only / a: 4108 pairs; data: no verdict record (no recorded edge, no chain joins the pair) x4108
  examples: P4-graph-coloring-racy-large assignColorsKernel(int*, int*, int*, int*, int*, i 0x500/0x6d0 | P4-graph-coloring-racy-large detectConflictsKernel(int*, int*, int*, int*, int* 0x490/0x660 | P4-graph-coloring-racy-large forbidColorsKernel(int*, int*, int*, int*, int*, i 0x570/0x740 | P4-graph-coloring-racy-small assignColorsKernel(int*, int*, int*, int*, int*, i 0x500/0x6d0 | P4-graph-coloring-racy-small detectConflictsKernel(int*, int*, int*, int*, int* 0x490/0x660 | P4-graph-coloring-racy-small forbidColorsKernel(int*, int*, int*, int*, int*, i 0x570/0x740 | P4-rule-110-racy-large rule110Kernel(int*, int volatile*, int*, int, int) 0x1120/0x1b70 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x21a0/0x21a0 | P5-race_interblock_blklock_waw kmain(unsigned int volatile*) 0x150/0x260 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x890/0x9c0
- race / sc_only / b: 3 pairs; data: ORDERED by R1 (strength block >= observed block) x2; ORDERED by R1 (strength block >= observed warp) x1
  examples: kokkos-5-buggy void Kokkos::Impl::cuda_parallel_launch_local_memo 0xbc0/0xc90 | raft-1-fixed void raft::matrix::detail::select::radix::impl::ra 0x1e20/0x60d0 | raft-1-fixed void raft::matrix::detail::select::radix::impl::ra 0x2df0/0x60d0
- race / sc_only / c: 29 pairs; data: edge skipped: intra_thread_only x28; edge skipped: rmw_pair_morally_strong x1
  examples: P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0xab0/0x1690 | P4-reduction-norace-small void reduceSinglePass<512u, true>(int const*, int  0xab0/0x1690 | P4-reduction-racy-large void reduceSinglePass<512u, true>(int const*, int  0xa80/0x1650 | P4-reduction-racy-small void reduceSinglePass<512u, true>(int const*, int  0xa80/0x1650 | P4-uts-racy-small parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x2290/0x2290 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x890/0x890 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x890/0xa60 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x9a0/0x9a0 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x9c0/0x9c0 | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed write_kernel(int*, int) 0x9e0/0x9e0
- sc / co_only / barrier: 56 pairs; data: scalar clock: ORDERED, barrier-ordered in every instance x56
  examples: P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x260/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x400/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x5a0/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x730/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x7d0/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x840/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x8b0/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x910/0xf20 | P4-reduction-norace-large void reduceSinglePass<512u, true>(int const*, int  0x960/0xf20 | P4-reduction-norace-small void reduceSinglePass<512u, true>(int const*, int  0x260/0xf20
- sc / co_only / derived: 227 pairs; data: closure (chain), pair not a scalar-clock candidate x221; closure (chain_rescue), pair not a scalar-clock candidate x6
  examples: P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xf0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xf0/0x1e0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x120/0x2f0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x120/0x2f0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-100n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x120/0x2f0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x120/0x2f0 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xf0/0x230 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, int*, int cons 0xf0/0x230 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x130/0x340 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n bfs_edge_data(ECLgraph, int const*, cuda::__4::ato 0x130/0x340
- sc / co_only / other: 130 pairs; data: scalar clock: ORDERED/None x130
  examples: P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0x590/0x5a0 | P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0x5a0/0x5a0 | P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0x960/0x980 | P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0x980/0x980 | P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0xb80/0xbb0 | P4-matrix-multiplication-norace-large matMultKernel(int*, int*, int volatile*, int, int, 0xbb0/0xbb0 | P4-matrix-multiplication-norace-small matMultKernel(int*, int*, int volatile*, int, int, 0x590/0x5a0 | P4-matrix-multiplication-norace-small matMultKernel(int*, int*, int volatile*, int, int, 0x5a0/0x5a0 | P4-matrix-multiplication-norace-small matMultKernel(int*, int*, int volatile*, int, int, 0x960/0x980 | P4-matrix-multiplication-norace-small matMultKernel(int*, int*, int volatile*, int, int, 0x980/0x980
- sc / sc_only / a: 15 pairs; data: no verdict record (no recorded edge, no chain joins the pair) x15
  examples: P4-uts-norace-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xcd0 | P4-uts-norace-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xdb0 | P4-uts-norace-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0x2a30 | P4-uts-norace-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0x2b10 | P4-uts-norace-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0x3090 | P4-uts-norace-small parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xcd0 | P4-uts-norace-small parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xdb0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xcd0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0xdb0 | P4-uts-racy-large parTreeSearch(StackStats*, Node*, StackStats*, Nod 0x300/0x2a30
## Part A: per kernel

Unit: (program id, kernel name), launches folded; a kernel counts if some analysed launch of it exists in the collector-only recording or in the vector-clock recording (kernel names read from the head of each kernel JSON; `names.json` present). Reported = at least one of its pairs is a data race in that configuration.

### Table 3: data races

| suite | kernels | cuRace alone | scalar clock | vector clock | cuRace not scalar | scalar not cuRace | scalar not vector | vector not scalar |
|---|---|---|---|---|---|---|---|---|
| P1 | 800 | 200 | 200 | 200 | 0 | 0 | 0 | 0 |
| P4 | 48 | 38 | 24 | 24 | 14 | 0 | 0 | 0 |
| P5 | 32 | 4 | 3 | 4 | 1 | 0 | 0 | 1 |
| P6 | 38 | 8 | 8 | 8 | 0 | 0 | 0 | 0 |
| P7 | 20 | 6 | 3 | 3 | 3 | 0 | 0 | 0 |
| P9 | 27 | 3 | 1 | 1 | 2 | 0 | 0 | 0 |
| PI | 4130 | 2668 | 2420 | 2420 | 248 | 0 | 0 | 0 |
| RW | 149 | 86 | 69 | 69 | 17 | 0 | 0 | 0 |
| all | 5244 | 3013 | 2728 | 2729 | 285 | 0 | 0 | 1 |

### Table 3 with strong conflicts counted as reports

| suite | kernels | cuRace alone | scalar clock | vector clock | cuRace not scalar | scalar not cuRace | scalar not vector | vector not scalar |
|---|---|---|---|---|---|---|---|---|
| P1 | 800 | 272 | 272 | 272 | 0 | 0 | 0 | 0 |
| P4 | 48 | 42 | 26 | 29 | 16 | 0 | 0 | 3 |
| P5 | 32 | 26 | 18 | 23 | 8 | 0 | 0 | 5 |
| P6 | 38 | 8 | 8 | 8 | 0 | 0 | 0 | 0 |
| P7 | 20 | 6 | 3 | 3 | 3 | 0 | 0 | 0 |
| P9 | 27 | 3 | 1 | 1 | 2 | 0 | 0 | 0 |
| PI | 4130 | 2668 | 2420 | 2420 | 248 | 0 | 0 | 0 |
| RW | 149 | 88 | 71 | 71 | 17 | 0 | 0 | 0 |
| all | 5244 | 3113 | 2819 | 2827 | 294 | 0 | 0 | 8 |

### Table 3 on X13's unit (kernel of one binary, folded over the runs of the binary: units (executable of the manifest row, kernel name)); data races, then with strong conflicts

| suite | kernels | cuRace alone | scalar clock | vector clock | cuRace not scalar | scalar not cuRace | scalar not vector | vector not scalar |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 100 | 100 | 100 | 0 | 0 | 0 | 0 |
| P4 | 24 | 19 | 12 | 12 | 7 | 0 | 0 | 0 |
| P5 | 32 | 4 | 3 | 4 | 1 | 0 | 0 | 1 |
| P6 | 38 | 8 | 8 | 8 | 0 | 0 | 0 | 0 |
| P7 | 20 | 6 | 3 | 3 | 3 | 0 | 0 | 0 |
| P9 | 27 | 3 | 1 | 1 | 2 | 0 | 0 | 0 |
| PI | 590 | 410 | 378 | 378 | 32 | 0 | 0 | 0 |
| RW | 149 | 86 | 69 | 69 | 17 | 0 | 0 | 0 |
| all | 1280 | 636 | 574 | 575 | 62 | 0 | 0 | 1 |

| suite | kernels | cuRace alone | scalar clock | vector clock | cuRace not scalar | scalar not cuRace | scalar not vector | vector not scalar |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 136 | 136 | 136 | 0 | 0 | 0 | 0 |
| P4 | 24 | 21 | 13 | 15 | 8 | 0 | 0 | 2 |
| P5 | 32 | 26 | 18 | 23 | 8 | 0 | 0 | 5 |
| P6 | 38 | 8 | 8 | 8 | 0 | 0 | 0 | 0 |
| P7 | 20 | 6 | 3 | 3 | 3 | 0 | 0 | 0 |
| P9 | 27 | 3 | 1 | 1 | 2 | 0 | 0 | 0 |
| PI | 590 | 410 | 378 | 378 | 32 | 0 | 0 | 0 |
| RW | 149 | 88 | 71 | 71 | 17 | 0 | 0 | 0 |
| all | 1280 | 698 | 628 | 635 | 70 | 0 | 0 | 7 |

### Kernels (data-race reports) where the scalar clock and the vector clock differ: 1

- P5-norace_interwarp-block_fence-atom_hrd-indirect / kmain(unsigned int*): 0x1d0/0x4a0 (cuRace -, scalar -, vector race); 0x2d0/0x3f0 (cuRace race, scalar -, vector race); 0x2d0/0x4a0 (cuRace -, scalar -, vector race)

### Kernels where cuRace alone and the scalar clock differ: 285 (first 20 listed)

- P4-graph-coloring-norace-large / assignColorsKernel(int*, int*, int*, int*, int*, int*, int*, int*): 0x160/0x4d0 (cuRace race, scalar -, vector -); 0x500/0x6b0 (cuRace race, scalar -, vector -)
- P4-graph-coloring-norace-large / detectConflictsKernel(int*, int*, int*, int*, int*, int*, int*, int*, : 0x160/0x4b0 (cuRace race, scalar -, vector -); 0x4b0/0x4b0 (cuRace race, scalar -, vector -); 0x4e0/0x690 (cuRace race, scalar -, vector -)
- P4-graph-coloring-norace-large / forbidColorsKernel(int*, int*, int*, int*, int*, int*, int*, int*, int: 0x160/0x550 (cuRace race, scalar -, vector -); 0x550/0x550 (cuRace race, scalar -, vector -); 0x580/0x730 (cuRace race, scalar -, vector -)
- P4-graph-coloring-norace-small / assignColorsKernel(int*, int*, int*, int*, int*, int*, int*, int*): 0x160/0x4d0 (cuRace race, scalar -, vector -); 0x500/0x6b0 (cuRace race, scalar -, vector -)
- P4-graph-coloring-norace-small / detectConflictsKernel(int*, int*, int*, int*, int*, int*, int*, int*, : 0x160/0x4b0 (cuRace race, scalar -, vector -); 0x4e0/0x690 (cuRace race, scalar -, vector -)
- P4-graph-coloring-norace-small / forbidColorsKernel(int*, int*, int*, int*, int*, int*, int*, int*, int: 0x160/0x550 (cuRace race, scalar -, vector -); 0x580/0x730 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-large / compressKernel(int*, int*, int*, int*, int*): 0x160/0x400 (cuRace race, scalar -, vector -); 0x430/0x5e0 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-large / initKernel(int*, int*, int*, int*, int*): 0x160/0x260 (cuRace race, scalar -, vector -); 0x290/0x440 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-large / linkKernel(int*, int*, int*, int*, int*, int*, int*): 0x160/0x410 (cuRace race, scalar -, vector -); 0x410/0x410 (cuRace race, scalar -, vector -); 0x440/0x5f0 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-small / compressKernel(int*, int*, int*, int*, int*): 0x160/0x400 (cuRace race, scalar -, vector -); 0x430/0x5e0 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-small / initKernel(int*, int*, int*, int*, int*): 0x160/0x260 (cuRace race, scalar -, vector -); 0x290/0x440 (cuRace race, scalar -, vector -)
- P4-graph-connectivity-norace-small / linkKernel(int*, int*, int*, int*, int*, int*, int*): 0x160/0x410 (cuRace race, scalar -, vector -); 0x440/0x5f0 (cuRace race, scalar -, vector -)
- P4-uts-norace-large / parTreeSearch(StackStats*, Node*, StackStats*, Node*, Config): 0x3b50/0x3b50 (cuRace race, scalar -, vector -); 0x3b50/0x3c90 (cuRace race, scalar -, vector -); 0x3b50/0x3d20 (cuRace race, scalar -, vector -); 0x3c90/0x3d20 (cuRace race, scalar -, vector -)
- P4-uts-norace-small / parTreeSearch(StackStats*, Node*, StackStats*, Node*, Config): 0x3b50/0x3b50 (cuRace race, scalar -, vector -); 0x3b50/0x3c90 (cuRace race, scalar -, vector -); 0x3b50/0x3d20 (cuRace race, scalar -, vector -); 0x3c90/0x3d20 (cuRace race, scalar -, vector -)
- P5-norace_interwarp-block_fence-atom_hrd-indirect / kmain(unsigned int*): 0x2d0/0x3f0 (cuRace race, scalar -, vector race)
- P7-hotspot-cuda / calc_temp(int, float const*, float const*, float*, int, int, int, int,: 0xa40/0xa40 (cuRace race, scalar -, vector -)
- P7-lavaMD-cuda / md(box_str const*, FOUR_VECTOR const*, float const*, FOUR_VECTOR*, flo: 0x740/0x740 (cuRace race, scalar -, vector -); 0x750/0x750 (cuRace race, scalar -, vector -)
- P7-srad-cuda / reduce(long, int, int, float*, float*): 0xa80/0xab0 (cuRace race, scalar -, vector -); 0xac0/0xae0 (cuRace race, scalar -, vector -)
- P9-crs-cuda / gcrs_m_1_w_4_coding_dotprod(int, int, long const*, long*, unsigned int: 0x3e0/0x810 (cuRace race, scalar -, vector -); 0x460/0x810 (cuRace race, scalar -, vector -); 0x550/0x810 (cuRace race, scalar -, vector -)
- P9-crs-cuda / gcrs_m_1_w_5_coding_dotprod(int, int, long const*, long*, unsigned int: 0x500/0x970 (cuRace race, scalar -, vector -); 0x570/0x970 (cuRace race, scalar -, vector -); 0x580/0x970 (cuRace race, scalar -, vector -); 0x5a0/0x970 (cuRace race, scalar -, vector -); 0x640/0x970 (cuRace race, scalar -, vector -); 0x690/0x970 (cuRace race, scalar -, vector -)

### Kernel unit against X13

X13 (`eval/baselines/per_kernel/kfold.py` and `eval/PER_KERNEL_TABLES.md` on origin/eval/per-kernel-tables 99e1c32d, read with `git show`, not in this checkout): a kernel is one `__global__` function (one template instantiation) of one *binary*; its verdict folds every launch of every run (manifest id) of that binary; a kernel no run launched is not counted. Table 3 above is per (program id, kernel); the folded variant (units (exe, kernel name)) is the same unit as X13 up to the kernel-name string (X13's key is its own inventory name; this one is the recording's `kernel_name`), and the `launched` rule differs: X13 counts kernels launched in a *finished* run in any tool/mode, this one counts kernels with a kernel JSON in the collector-only or vector-clock recording of the population. Not checked: that the two name strings agree kernel by kernel.

## Part B: pairs the vector clock reports and the scalar clock orders through R3

### Table 4: data races

| suite | pairs in population | F2-acq | F2-rel | of them both | F1 | other |
|---|---|---|---|---|---|---|
| P4 | 22 | 0 | 0 | 0 | 0 | 22 |
| P5 | 3 | 0 | 0 | 0 | 0 | 3 |
| PI | 2 | 2 | 0 | 0 | 0 | 0 |
| RW | 66 | 65 | 0 | 0 | 0 | 1 |
| all | 93 | 67 | 0 | 0 | 0 | 26 |

### Table 4: strong conflicts

| suite | pairs in population | F2-acq | F2-rel | of them both | F1 | other |
|---|---|---|---|---|---|---|
| P4 | 130 | 114 | 14 | 14 | 16 | 0 |
| P5 | 13 | 13 | 3 | 3 | 0 | 0 |
| all | 143 | 127 | 17 | 17 | 16 | 0 |

A pair that is both F2-acq and F2-rel is counted under each; `of them both` is the overlap. F1/other are counted once. The sum of the class columns is therefore at least the population.

### Per program

| program | kind | pairs | F2-acq | F2-rel | both | F1 | other |
|---|---|---|---|---|---|---|---|
| P5-norace_interwarp-block_fence-atom_hrd-indirect | race | 3 | 0 | 0 | 0 | 0 | 3 |
| cccl-3-buggy | race | 21 | 21 | 0 | 0 | 0 | 0 |
| cccl-3-fixed | race | 18 | 18 | 0 | 0 | 0 | 0 |
| hecbench-hungarian-1-buggy | race | 1 | 1 | 0 | 0 | 0 | 0 |
| hecbench-hungarian-1-fixed | race | 1 | 1 | 0 | 0 | 0 | 0 |
| raft-1-buggy | race | 12 | 12 | 0 | 0 | 0 | 0 |
| raft-1-fixed | race | 13 | 12 | 0 | 0 | 0 | 1 |

`other` reasons: release side rmw, acquire side rmw x25; release side rmw, acquire side ok x9

### norace_interwarp-block_fence-atom_hrd-indirect

program P5-norace_interwarp-block_fence-atom_hrd-indirect; pairs: 0x1d0/0x4a0 (race); 0x2d0/0x3f0 (race); 0x2d0/0x4a0 (race)

- pair 0x1d0/0x4a0: class ['other']; direction ['0x4a0', '0x1d0']; distance grid; release points None fenced None; acquire points None fenced None; chain ['0x4a0', '0x4c0', '0x380', '0x430', '0x260', '0x2f0', '0x160']; hb_races records [([0, 0, 0], [1, 1, 0], 'grid', 'DR')]
- pair 0x2d0/0x3f0: class ['other']; direction ['0x3f0', '0x2d0']; distance grid; release points None fenced None; acquire points None fenced None; chain ['0x3f0', '0x430', '0x260']; hb_races records [([0, 1, 0], [1, 0, 0], 'grid', 'DR')]
- pair 0x2d0/0x4a0: class ['other']; direction ['0x4a0', '0x2d0']; distance grid; release points None fenced None; acquire points None fenced None; chain ['0x4a0', '0x4c0', '0x380', '0x430', '0x260']; hb_races records [([0, 0, 0], [1, 0, 0], 'grid', 'DR')]

SASS around the pair pcs and the chain pcs (from /mnt/beegfs/fzheng4/cuvein_traces/final-2026-11/P5-norace_interwarp-block_fence-atom_hrd-indirect/dots/norace_interwarp-block_fence-atom_hrd-indirect.sm_89.dot):
```
0x200  IMAD.MOV.U32
0x210  IMAD.MOV.U32
0x220  YIELD
0x230  VOTEU.ANY
0x240  FLO.U32
0x250  ISETP.EQ.U32.AND
0x260  ATOMG.E.ADD.STRONG.GPU
0x270  SHFL.IDX
0x280  ISETP.NE.AND
0x290  BRA
0x2a0  MOV
0x2b0  IMAD.MOV.U32
0x2c0  IMAD.MOV.U32
0x2d0  ATOMG.E.EXCH.STRONG.SM
0x2e0  MEMBAR.SC.CTA
0x2f0  ATOMG.E.EXCH.STRONG.GPU
0x300  EXIT
0x310  S2R
0x320  IMAD.MOV.U32
0x330  MOV
0x390  SHFL.IDX
0x3a0  ISETP.NE.AND
0x3b0  BRA
0x3c0  IMAD.MOV.U32
0x3d0  IMAD.MOV.U32
0x3e0  IMAD.MOV.U32
0x3f0  ATOMG.E.EXCH.STRONG.GPU
0x400  MEMBAR.SC.GPU
0x410  ERRBAR;
0x420  CCTL.IVALL
0x430  ATOMG.E.EXCH.STRONG.GPU
0x440  EXIT
0x450  MOV
0x460  IMAD.MOV.U32
0x470  MOV
0x480  IMAD.MOV.U32
0x490  IMAD.MOV.U32
```

source `/home/fzheng4/AccelProf/ScoR/microbenchmarks/src/norace_interwarp-block_fence-atom_hrd-indirect.cu`:
```
#include <stdio.h>

#define NBLOCKS  2
#define TPERBLK  33

#define NTHREADS (NBLOCKS * TPERBLK)

void errCheck()
{
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("Error %d: %s\n", err, cudaGetErrorString(err));
        exit(1);
    }
}

__device__ int flag = 0;

__global__ void kmain(unsigned int *data) 
{
    if(blockIdx.x == 0 && threadIdx.x == 0)
    {
        atomicExch_block(&data[0], 1);
        __threadfence_block();
        atomicExch(&flag, 1);
    }
    else if(blockIdx.x == 0 && threadIdx.x == 32)
    {
        while(atomicAdd(&flag, 0) != 1);
        atomicExch(&data[0], 2);
        __threadfence();
        atomicExch(&flag, 2);
    }
    else if(blockIdx.x == 1 && threadIdx.x == 0)
    {
        while(atomicAdd(&flag, 0) != 2);
        atomicExch_block(&data[0], 3);
        __threadfence_block();
        atomicExch(&flag, 3);
    }
    else if(blockIdx.x == 1 && threadIdx.x == 32)
    {
        while(atomicAdd(&flag, 0) != 3);
        atomicExch(&data[0], 3);
    }
}

int main() 
{
    unsigned int *d_data;
    cudaMalloc(&d_data, sizeof(unsigned int));
    kmain<<<NBLOCKS,TPERBLK>>>(d_data);
    errCheck();
    return 0;
}

```

### What the classification used

`sync_dominance.analyze()` on the scalar-clock pass (vector-clock recording with `hb_races` and `hb_races_sync_only` removed, as mode_pairs.py pass 2), M3's after state; the captured `HBGraph`: `release_points` / `acquire_points` (filled from the recording's `hb_rmw_points` by `aggregated_rmw_points` via `trace_rmw_points`), `atom`, `chain(anc, cur)` then `chain(cur, anc)` to find the direction the rule used, `fenced(p, q, s, side)` with `s` = the distance `ordered()` was asked at (logged by shadowing `HBGraph.ordered`), `pc_opcode`; `fence_scope` (the fence inventory by opcode: MEMBAR.SC/ALL.<scope>, CCTL.IVALL acquire side, BAR.SYNC/RED) is what `fenced` consults. Release side: for the recorded next-RMW points of the release endpoint, `fenced(u, a, d, 'rel')`; acquire side: for the recorded previous-RMW points of the acquire endpoint, `fenced(a, v, d, 'acq')`. Recording fields read: `hb_rmw_points`, `hb_sync_pass` (via `use_aggregates`), `hb_races` (thread ids, only for the block/warp of the hrd-indirect pairs). No new fence predicate was written.


## The five M2 pairs (cuRace alone, S2, `realworld-2026-10-co`)

| id | pc | pc | cuRace alone S2 |
|---|---|---|---|
| cccl-3-buggy | 0x80 | 0xad90 | RACE/None/edge |
| raft-1-buggy | 0x2df0 | 0x60a0 | RACE/None/edge |
| raft-1-fixed | 0x2df0 | 0x60d0 | ORDERED/None/edge |
| kokkos-5-buggy | 0xbc0 | 0xc90 | ORDERED/None/edge |
| kokkos-5-fixed | 0xbd0 | 0xca0 | None/None/None |

## Left out

| suite | reason | programs |
|---|---|---|
| P3 | excluded (P3 / canary) | 60 |
| P5 | excluded (P3 / canary) | 1 |
| P7 | no collector-only recording in the stores used (P7-heartwall-cuda) | 1 |
| P9 | no vector-/scalar-clock result: not-analysable | 2 |
| P9 | no collector-only recording in the stores used (P9-knn-cuda, P9-tridiagonal-cuda) | 2 |
| RW | no collector-only result: analysis-timeout | 2 |

Real-world programs without a collector-only result in `realworld-2026-10-co` (X12 section 8.3 lists the known gaps: amrex-1 kept out, lightgbm-new-1/-2 and llamacpp-open-2 never recorded collector-only, colmap-new-1 buggy ERROR in the standard re-analysis) drop out of every column; so do the real-world programs whose clock-mode recording M3 could not use (`amrex-1`, `ginkgo-1`: unsaved / partial).
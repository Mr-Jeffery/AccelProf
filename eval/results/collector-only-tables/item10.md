## Item 10: repeatability of collector-only mode (the "Is one run enough?" measures)

Programs with kept reps: 64 (recordings per program: {6: 64}); recordings = kept rep directories of the two parity recordings A (c41-c43) and B (c40, c55, c62). Pairs of recordings: 960.

| scope | programs | pairs of recordings | same program verdict | same reported pair set (race type removed) | identical edge sets | edge Jaccard min / median / mean |
|---|---|---|---|---|---|---|
| all pairs | 64 | 960 | 960 | 906 (933) | 723 | 0.6566 / 1.0000 / 0.9847 |
| same recording set (same 3 nodes, different reps) | 64 | 384 | 384 | 384 (384) | 294 | 0.6566 / 1.0000 / 0.9859 |
| across the two sets (A against B) | 64 | 576 | 576 | 522 (549) | 429 | 0.6765 / 1.0000 / 0.9839 |
| recordings on different nodes | 64 | 576 | 576 | 522 (549) | 429 | 0.6765 / 1.0000 / 0.9839 |
| recordings on the same node | 64 | 384 | 384 | 384 (384) | 294 | 0.6566 / 1.0000 / 0.9859 |

By suite:

| scope | programs | pairs | same verdict | same reported set (untyped) | identical edge sets | edge J min / median / mean |
|---|---|---|---|---|---|---|
| P1 | 10 | 150 | 150 | 123 (150) | 102 | 0.9000 / 1.0000 / 0.9852 |
| P3 | 10 | 150 | 150 | 150 (150) | 98 | 0.7500 / 1.0000 / 0.9812 |
| P4 | 10 | 150 | 150 | 141 (141) | 67 | 0.9184 / 0.9895 / 0.9805 |
| P5 | 10 | 150 | 150 | 150 (150) | 150 | 1.0000 / 1.0000 / 1.0000 |
| P6 | 10 | 150 | 150 | 150 (150) | 150 | 1.0000 / 1.0000 / 1.0000 |
| P7 | 2 | 30 | 30 | 30 (30) | 30 | 1.0000 / 1.0000 / 1.0000 |
| P9 | 2 | 30 | 30 | 30 (30) | 30 | 1.0000 / 1.0000 / 1.0000 |
| PI | 10 | 150 | 150 | 132 (132) | 96 | 0.6566 / 1.0000 / 0.9552 |

Pairs of recordings with a different program verdict: 0

Pairs of recordings with a different reported pair set: 54; programs: `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n`, `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n`, `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n`, `P4-graph-coloring-racy-small`, `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e`, `PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e`
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P4-graph-coloring-racy-small` A1@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A1@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A1@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B1@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B2@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B3@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A2@c42 vs B1@c62: 47 vs 48 pairs; untyped sets equal: False

Lowest edge Jaccard:

| program | recording a | recording b | edges a | edges b | Jaccard | verdicts |
|---|---|---|---|---|---|---|
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B2@c62 | B3@c62 | 76 | 88 | 0.6566 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B2@c62 | 95 | 76 | 0.6765 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B1@c62 | B3@c62 | 87 | 88 | 0.6827 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B2@c62 | 89 | 76 | 0.6837 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B1@c62 | 89 | 87 | 0.7087 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B3@c62 | 85 | 88 | 0.7300 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B2@c62 | 85 | 76 | 0.7312 | RACE/RACE |
| `P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n` | B1@c55 | B2@c55 | 6 | 8 | 0.7500 | CLEAN/CLEAN |
| `P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n` | B1@c55 | B3@c55 | 6 | 8 | 0.7500 | CLEAN/CLEAN |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B1@c62 | 95 | 87 | 0.7500 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B3@c62 | 95 | 88 | 0.7596 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B1@c62 | 85 | 87 | 0.7732 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B3@c62 | 89 | 88 | 0.8061 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B1@c62 | B2@c62 | 87 | 76 | 0.8111 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | A3@c42 | 95 | 85 | 0.8182 | RACE/RACE |

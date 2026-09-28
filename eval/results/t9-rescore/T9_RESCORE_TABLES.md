## Race-set deltas (vector-clock dumps: recorded engine vs T9 oracle, pc pairs)

| pset | programs | old_pairs | new_dr_pairs | new_sc_pairs | dr_gained | lost | sync_pairs_gained | sync_pairs_lost | old_records | new_records | with_local_events | tv | error:oracle-died | no-vc-dump |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 361 | 1146 | 1158 | 121 | 12 | 0 | 1300 | 0 | 27720817 | 1659798047 | 0 | 0 | 4 | 23 |
| P2 | 58 | 42 | 42 | 0 | 0 | 0 | 0 | 0 | 2404 | 101936 | 0 | 0 | 0 | 0 |
| P3 | 56 | 14 | 14 | 79 | 0 | 0 | 662 | 0 | 5984 | 2167264 | 0 | 0 | 0 | 2 |
| P4 | 18 | 91 | 103 | 0 | 12 | 0 | 106 | 0 | 296635 | 521026 | 0 | 1 | 0 | 10 |
| P5 | 33 | 11 | 13 | 0 | 2 | 0 | 8 | 0 | 13 | 15 | 0 | 0 | 0 | 0 |
| P6 | 27 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 97 | 97 | 0 | 0 | 0 | 1 |
| P7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P9 | 1 | 155 | 155 | 0 | 0 | 0 | 0 | 0 | 44441164 | 44441164 | 0 | 1 | 0 | 3 |
| **all** | 554 | 1464 | 1490 | 200 | 26 | 0 | 2076 | 0 | 72467114 | 1707029549 | 0 | 2 | 4 | 40 |

Programs whose pc-pair sets moved (old = recorded engine pairs; DR/SC = the T9 oracle's classes; first four pairs shown):

| pset | program | old | new DR | new SC-only | DR gained | lost | sync+ | sync- |
|---|---|---|---|---|---|---|---|---|
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 22 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 22 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 2 |  |  | 22 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 22 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 2 |  |  | 22 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 16 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 2 |  |  | 19 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 19 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 2 |  |  | 21 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 2 |  |  | 18 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 4 |  |  | 42 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 4 |  |  | 46 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 4 |  |  | 46 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n | 0 | 0 | 4 |  |  | 42 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n | 0 | 0 | 4 |  |  | 38 | 0 |
| P1 | P1-BFS_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 0 | 0 | 4 |  |  | 42 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n | 0 | 0 | 1 |  |  | 12 | 0 |
| P1 | P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n | 22 | 23 | 0 | 0x4d0/0x6d0 |  | 0 | 0 |
| P1 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n | 8 | 8 | 0 |  |  | 2 | 0 |
| P1 | P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n | 8 | 8 | 0 |  |  | 1 | 0 |
| P1 | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | 28 | 30 | 0 | 0x210/0x880, 0x290/0x880 |  | 7 | 0 |
| P1 | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | 29 | 30 | 0 | 0x290/0x880 |  | 7 | 0 |
| P1 | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | 28 | 30 | 0 | 0x260/0x8d0, 0x2e0/0x8d0 |  | 7 | 0 |
| P1 | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | 28 | 30 | 0 | 0x260/0x8d0, 0x2e0/0x8d0 |  | 8 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | 30 | 31 | 0 | 0x220/0x380 |  | 5 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n | 31 | 31 | 0 |  |  | 2 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | 30 | 31 | 0 | 0x220/0x380 |  | 7 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | 30 | 31 | 0 | 0x250/0x3e0 |  | 8 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | 30 | 31 | 0 | 0x250/0x3e0 |  | 8 | 0 |
| P1 | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n | 31 | 31 | 0 |  |  | 1 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 1 |  |  | 9 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 3 |  |  | 31 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 3 |  |  | 32 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 3 |  |  | 31 | 0 |
| P3 | P3-CC_CUDA_E_Data_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NonDeterm_NoFieldBug_Init-100n | 0 | 0 | 3 |  |  | 32 | 0 |
| P3 | P3-CC_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 1 |  |  | 10 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 2 |  |  | 18 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 2 |  |  | 15 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadModifyWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 2 |  |  | 20 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 4 |  |  | 44 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_NonPersist_CudaAtomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 4 |  |  | 44 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_Atomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 4 |  |  | 44 | 0 |
| P3 | P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n | 0 | 0 | 4 |  |  | 44 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 16 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 16 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Thread_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 16 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Thread_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 16 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 8 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 4 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 8 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 32 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 4 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 8 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Thread_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 33 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 8 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 9 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Thread_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 0 | 0 | 4 |  |  | 32 | 0 |
| P3 | P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n | 1 | 1 | 1 |  |  | 8 | 0 |
| P4 | P4-graph-coloring-racy-small | 9 | 12 | 0 | 0x490/0x660, 0x500/0x6d0, 0x570/0x740 |  | 36 | 0 |
| P4 | P4-graph-connectivity-racy-small | 5 | 5 | 0 |  |  | 2 | 0 |
| P4 | P4-matrix-multiplication-norace-small | 0 | 4 | 0 | 0x590/0x5a0, 0x5a0/0x5a0, 0x960/0x980, 0x980/0x980 |  | 0 | 0 |
| P4 | P4-matrix-multiplication-racy-small | 2 | 6 | 0 | 0x580/0x590, 0x590/0x590, 0x930/0x950, 0x950/0x950 |  | 0 | 0 |
| P4 | P4-reduction-norace-large | 11 | 11 | 0 |  |  | 1 | 0 |
| P4 | P4-reduction-norace-small | 10 | 10 | 0 |  |  | 1 | 0 |
| P4 | P4-reduction-racy-large | 12 | 12 | 0 |  |  | 1 | 0 |
| P4 | P4-reduction-racy-small | 11 | 11 | 0 |  |  | 1 | 0 |
| P4 | P4-rule-110-racy-large | 15 | 16 | 0 | 0x1120/0x1b70 |  | 64 | 0 |
| P5 | P5-norace_interwarp-block_fence-atom_hrd-indirect | 0 | 0 | 0 |  |  | 2 | 0 |
| P5 | P5-norace_interwarp-block_fence_hrf-indirect | 0 | 0 | 0 |  |  | 5 | 0 |
| P5 | P5-race_interblock_blklock_waw | 3 | 4 | 0 | 0x150/0x260 |  | 1 | 0 |
| P5 | P5-race_interblock_fence_rtraw | 0 | 1 | 0 | 0x100/0x1f0 |  | 0 | 0 |

## Verdict deltas (parallel.py analyze: BEFORE = 1a3aea5 code on the recorded dumps, AFTER = T9 code on the re-scored dumps)

Not re-scored (the T9 oracle did not finish; their AFTER rows are the harness's no-trace-collected ERROR and are left out below): P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n (oracle-died(status=9), 2868.9 MB), P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n (oracle-died(status=9), 2867.4 MB), P1-CC_CUDA_V_Topo_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n (oracle-died(status=9), 2833.2 MB), P1-CC_CUDA_V_Topo_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n (oracle-died(status=9), 2833.1 MB)

| mode | before | after | programs |
|---|---|---|---|
|  | - | ERROR | 1 |
| scalar-clock | CLEAN | CLEAN | 312 |
| scalar-clock | RACE | RACE | 281 |
| vector-clock | CLEAN | CLEAN | 302 |
| vector-clock | ERROR | ERROR | 2 |
| vector-clock | RACE | RACE | 252 |
| vector-clock | TIMEOUT | TIMEOUT | 37 |

**True positives gained: 0**

**True positives lost: 0**

**New false positives: 0**

**False positives removed: 0**

Every program whose verdict or report set moved:

| mode | program | label | before | after | Race alone | #ids b/a | ids added | ids removed | classes |
|---|---|---|---|---|---|---|---|---|---|
| scalar-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 29/30 | global:0x290-0x880:WAW |  | {'race': 30} |
| vector-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 28/30 | global:0x210-0x880:WAR global:0x290-0x880:WAW |  | {'structural': 30} |
| scalar-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 29/30 | global:0x290-0x880:WAW |  | {'race': 30} |
| vector-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 29/30 | global:0x290-0x880:WAW |  | {'structural': 30} |
| scalar-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 29/30 | global:0x2e0-0x8d0:WAW |  | {'race': 30} |
| vector-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 28/30 | global:0x260-0x8d0:WAR global:0x2e0-0x8d0:WAW |  | {'structural': 30} |
| scalar-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 29/30 | global:0x2e0-0x8d0:WAW |  | {'race': 30} |
| vector-clock | P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 28/30 | global:0x260-0x8d0:WAR global:0x2e0-0x8d0:WAW |  | {'structural': 30} |
| scalar-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x220-0x380:WAW |  | {'race': 31} |
| vector-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x220-0x380:WAW |  | {'structural': 31} |
| scalar-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 29/31 | global:0x200-0x380:WAR global:0x220-0x380:WAW |  | {'race': 31} |
| vector-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x220-0x380:WAW |  | {'structural': 31} |
| scalar-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 29/31 | global:0x230-0x3e0:WAR global:0x250-0x3e0:WAW |  | {'race': 31} |
| vector-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x250-0x3e0:WAW |  | {'structural': 31} |
| scalar-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x250-0x3e0:WAW |  | {'race': 31} |
| vector-clock | P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n | RACE | RACE | RACE | RACE | 30/31 | global:0x250-0x3e0:WAW |  | {'structural': 31} |
| scalar-clock | P4-graph-coloring-racy-large | RACE | RACE | RACE | RACE | 11/14 | global:0x490-0x660:WAW global:0x500-0x6d0:WAW global:0x570-0x740:WAW |  | {'race': 14} |
| scalar-clock | P4-graph-coloring-racy-small | RACE | RACE | RACE | RACE | 10/13 | global:0x490-0x660:WAW global:0x500-0x6d0:WAW global:0x570-0x740:WAW |  | {'race': 13} |
| vector-clock | P4-graph-coloring-racy-small | RACE | RACE | RACE | RACE | 11/14 | global:0x490-0x660:WAW global:0x500-0x6d0:WAW global:0x570-0x740:WAW |  | {'structural': 14} |
| vector-clock | P4-matrix-multiplication-norace-small | CLEAN | RACE | RACE | RACE | 2/4 | global:0x5a0-0x5a0:WAW global:0x980-0x980:WAW |  | {'structural': 4} |
| vector-clock | P4-matrix-multiplication-racy-small | RACE | RACE | RACE | RACE | 5/7 | global:0x590-0x590:WAW global:0x950-0x950:WAW |  | {'structural': 7} |
| scalar-clock | P4-reduction-norace-large | CLEAN | RACE | RACE | RACE | 11/12 | global:0xab0-0x1690:WAW |  | {'race': 12} |
| vector-clock | P4-reduction-norace-large | CLEAN | RACE | RACE | RACE | 12/13 | global:0xab0-0x1690:WAW |  | {'latent': 2, 'structural': 11} |
| scalar-clock | P4-reduction-norace-small | CLEAN | RACE | RACE | RACE | 12/13 | global:0xab0-0x1690:WAW |  | {'race': 13} |
| vector-clock | P4-reduction-norace-small | CLEAN | RACE | RACE | RACE | 12/13 | global:0xab0-0x1690:WAW |  | {'latent': 3, 'structural': 10} |
| scalar-clock | P4-reduction-racy-large | RACE | RACE | RACE | RACE | 13/14 | global:0xa80-0x1650:WAW |  | {'race': 14} |
| vector-clock | P4-reduction-racy-large | RACE | RACE | RACE | RACE | 15/16 | global:0xa80-0x1650:WAW |  | {'latent': 4, 'structural': 12} |
| scalar-clock | P4-reduction-racy-small | RACE | RACE | RACE | RACE | 14/15 | global:0xa80-0x1650:WAW |  | {'race': 15} |
| vector-clock | P4-reduction-racy-small | RACE | RACE | RACE | RACE | 15/16 | global:0xa80-0x1650:WAW |  | {'latent': 5, 'structural': 11} |
| scalar-clock | P4-rule-110-racy-large | RACE | RACE | RACE | RACE | 19/20 | shared:0x1120-0x1b70:WAW |  | {'race': 20} |
| vector-clock | P4-rule-110-racy-large | RACE | RACE | RACE | RACE | 19/20 | shared:0x1120-0x1b70:WAW |  | {'latent': 4, 'structural': 16} |
| scalar-clock | P5-race_interblock_blklock_waw | RACE | RACE | RACE | RACE | 3/4 | shared:0x150-0x260:WAW |  | {'race': 4} |
| vector-clock | P5-race_interblock_blklock_waw | RACE | RACE | RACE | RACE | 3/4 | shared:0x150-0x260:WAW |  | {'structural': 4} |
|  | P9-crs-cuda | CLEAN | - | ERROR | ERROR | 0/0 |  |  | None |

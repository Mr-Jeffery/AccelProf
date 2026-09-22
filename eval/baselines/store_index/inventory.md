| store | kind | created | git head | modes | programs | with a loss | on disk | scanned on |
|---|---|---|---|---|---|---|---|---|
| `/mnt/beegfs/fzheng4/cuvein_traces/evcand` | beegfs | 2026-09-20 21:31:41 | `fe694b5b` | engine,trace-only | 613 | 55 | 149.4 GB | c39 |
| `/mnt/beegfs/fzheng4/cuvein_traces/evcand_smoke` | beegfs | 2026-09-20 21:28:45 | `fe694b5b` | engine,trace-only | 6 | 0 | 0.0 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep` | home | — | `—` | engine,trace-only | 248 | 81 | 3.2 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep.prefix_36a93d08` | home | — | `—` | engine,trace-only | 110 | 83 | 3.0 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep.prefix_fe694b5` | home | — | `—` | engine,trace-only | 208 | 67 | 3.9 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep_evcand` | home | — | `—` | engine,trace-only | 86 | 69 | 1.0 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep_fpfix` | home | — | `—` | engine,trace-only | 87 | 87 | 0.6 GB | c39 |
| `/home/fzheng4/AccelProf/eval/baselines/traces_keep_fpfix_tr` | home | — | `—` | engine,trace-only | 55 | 55 | 0.7 GB | c39 |

Per-store loss breakdown (count of programs per reason; a program can carry several):

| store | reason | programs |
|---|---|---|
| evcand | `engine:missing` | 16 |
| evcand | `engine:unsaved:all-reps-timed-out` | 39 |
| evcand | `error` | 16 |
| evcand | `trace-only:missing` | 16 |
| evcand | `trace-only:unsaved:all-reps-timed-out` | 4 |
| traces_keep | `engine:missing` | 16 |
| traces_keep | `engine:unsaved:all-reps-timed-out` | 56 |
| traces_keep | `engine:unsaved:no-kernel-json` | 2 |
| traces_keep | `engine:unsaved:not-saved` | 1 |
| traces_keep | `error` | 16 |
| traces_keep | `trace-only:missing` | 16 |
| traces_keep | `trace-only:unsaved:all-reps-timed-out` | 20 |
| traces_keep | `trace-only:unsaved:no-kernel-json` | 2 |
| traces_keep | `trace-too-large` | 25 |
| traces_keep.prefix_36a93d08 | `engine:missing` | 16 |
| traces_keep.prefix_36a93d08 | `engine:unsaved:all-reps-timed-out` | 57 |
| traces_keep.prefix_36a93d08 | `engine:unsaved:no-kernel-json` | 4 |
| traces_keep.prefix_36a93d08 | `error` | 16 |
| traces_keep.prefix_36a93d08 | `trace-only:missing` | 16 |
| traces_keep.prefix_36a93d08 | `trace-only:unsaved:all-reps-timed-out` | 16 |
| traces_keep.prefix_36a93d08 | `trace-only:unsaved:no-kernel-json` | 4 |
| traces_keep.prefix_36a93d08 | `trace-too-large` | 28 |
| traces_keep.prefix_fe694b5 | `engine:missing` | 16 |
| traces_keep.prefix_fe694b5 | `engine:unsaved:all-reps-timed-out` | 22 |
| traces_keep.prefix_fe694b5 | `engine:unsaved:no-kernel-json` | 5 |
| traces_keep.prefix_fe694b5 | `error` | 16 |
| traces_keep.prefix_fe694b5 | `trace-only:missing` | 16 |
| traces_keep.prefix_fe694b5 | `trace-only:unsaved:all-reps-timed-out` | 8 |
| traces_keep.prefix_fe694b5 | `trace-only:unsaved:no-kernel-json` | 6 |
| traces_keep.prefix_fe694b5 | `trace-too-large` | 35 |
| traces_keep_evcand | `engine:missing` | 16 |
| traces_keep_evcand | `engine:unsaved:all-reps-timed-out` | 39 |
| traces_keep_evcand | `error` | 16 |
| traces_keep_evcand | `trace-only:missing` | 16 |
| traces_keep_evcand | `trace-only:unsaved:all-reps-timed-out` | 4 |
| traces_keep_evcand | `trace-too-large` | 37 |
| traces_keep_fpfix | `engine:missing` | 16 |
| traces_keep_fpfix | `engine:unsaved:all-reps-timed-out` | 41 |
| traces_keep_fpfix | `error` | 16 |
| traces_keep_fpfix | `trace-only:missing` | 87 |
| traces_keep_fpfix | `trace-too-large` | 5 |
| traces_keep_fpfix_tr | `engine:missing` | 55 |
| traces_keep_fpfix_tr | `error` | 16 |
| traces_keep_fpfix_tr | `trace-only:missing` | 16 |
| traces_keep_fpfix_tr | `trace-only:unsaved:all-reps-timed-out` | 4 |
| traces_keep_fpfix_tr | `trace-too-large` | 7 |

Every program with a lost or partial trace:

| store | id | reasons | mode dumps on disk | largest raw dump seen (MB) | peak RSS (MB) |
|---|---|---|---|---|---|
| evcand | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.2 GB | 237 | 10340 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/1.7 GB | 1659 | 35018 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:16j/1.7 GB | 1665 | 34813 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 103 | 36899 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/1.6 GB | 1647 | 53530 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 100 | 35978 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/1.6 GB | 1681 | 55234 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 142 | 39800 |
| evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/0.1 GB | 142 | 42848 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:9j/1.0 GB | 1012 | 34767 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:9j/1.0 GB | 1020 | 34832 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 96 | 35458 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/1.0 GB | 1050 | 54572 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 96 | 35836 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:9j/1.0 GB | 1022 | 54252 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 132 | 40340 |
| evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:13j/0.1 GB | 130 | 42787 |
| evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:5j/0.4 GB | 377 | 119072 |
| evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 63 | 25548 |
| evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:5j/0.4 GB | 371 | 84082 |
| evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 62 | 24215 |
| evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:5j/0.4 GB | 369 | 93279 |
| evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 82532 |
| evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 78481 |
| evcand | `P4-graph-coloring-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:30j/0.1 GB | 124 | 1793 |
| evcand | `P4-graph-coloring-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:30j/0.2 GB | 167 | 1793 |
| evcand | `P4-graph-connectivity-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.0 GB | 61 | 3126 |
| evcand | `P4-graph-connectivity-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.1 GB | 69 | 3046 |
| evcand | `P4-matrix-multiplication-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/10.4 GB | 10441 | 11141 |
| evcand | `P4-matrix-multiplication-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/10.4 GB | 10444 | 11145 |
| evcand | `P4-uts-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/1.4 GB | 1574 | 13294 |
| evcand | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 79 | 11697 |
| evcand | `P4-uts-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/1.7 GB | 1676 | 13056 |
| evcand | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 61 | 11780 |
| evcand | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 33507 |
| evcand | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 28938 |
| evcand | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/11.6 GB | 11558 | 84462 |
| evcand | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| evcand | `P6-interkernel-global_writewrite_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11408 |
| evcand | `P6-interkernel-global_writewrite_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11403 |
| traces_keep | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.2 GB | 237 | 10182 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1663 | 33776 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1649 | 33660 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 100 | 33774 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1704 | 45069 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 101 | 35331 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1703 | 64954 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 142 | 38391 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/0.1 GB | 141 | 42306 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1012 | 34825 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1010 | 34916 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 97 | 33894 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:not-saved, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 64286 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 96 | 34768 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1023 | 66401 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 132 | 42974 |
| traces_keep | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 131 | 42479 |
| traces_keep | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 392 | 127494 |
| traces_keep | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 372 | 127215 |
| traces_keep | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 373 | 91720 |
| traces_keep | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 385 | 92257 |
| traces_keep | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 84190 |
| traces_keep | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 83346 |
| traces_keep | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 75 | 38707 |
| traces_keep | `P4-graph-coloring-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:30j/0.1 GB | 124 | 1790 |
| traces_keep | `P4-graph-coloring-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:33j/0.2 GB | 167 | 1796 |
| traces_keep | `P4-graph-connectivity-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.0 GB | 56 | 3138 |
| traces_keep | `P4-graph-connectivity-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.1 GB | 58 | 3074 |
| traces_keep | `P4-matrix-multiplication-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10442 | 11140 |
| traces_keep | `P4-matrix-multiplication-norace-small` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 325 | 1353 |
| traces_keep | `P4-matrix-multiplication-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10440 | 11146 |
| traces_keep | `P4-rule-110-norace-large` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1684 | 948 |
| traces_keep | `P4-uts-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1758 | 14333 |
| traces_keep | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 65 | 12425 |
| traces_keep | `P4-uts-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1710 | 14661 |
| traces_keep | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 68 | 12238 |
| traces_keep | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 40270 |
| traces_keep | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 122718 |
| traces_keep | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 85060 |
| traces_keep | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep | `P6-hostdevice-global_writeread_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3578 |
| traces_keep | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1529 |
| traces_keep | `P6-interkernel-global_readwrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2216 |
| traces_keep | `P6-interkernel-global_writewrite_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 10823 |
| traces_keep | `P6-interkernel-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 18247 | 11408 |
| traces_keep | `P7-bezier-surface-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 66015 |
| traces_keep | `P7-bitonic-sort-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 245954 | 19199 |
| traces_keep | `P7-haversine-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 277455 | 29412 |
| traces_keep | `P7-heartwall-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 252269 | 84929 |
| traces_keep | `P7-hotspot-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 26322 | 6659 |
| traces_keep | `P7-lavaMD-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 169845 |
| traces_keep | `P7-mandelbrot-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 291023 | 2734 |
| traces_keep | `P7-nbody-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 301367 | 117015 |
| traces_keep | `P7-particlefilter-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 6505 | 20877 |
| traces_keep | `P7-pathfinder-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 155282 | 95489 |
| traces_keep | `P7-srad-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 261693 | 3641 |
| traces_keep | `P7-stencil1d-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 320059 | 121866 |
| traces_keep | `P9-atomicCAS-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 120663 | 33156 |
| traces_keep | `P9-crs-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10215 | 2890 |
| traces_keep | `P9-dxtc2-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 248237 | 13451 |
| traces_keep | `P9-expdist-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 359250 | 61420 |
| traces_keep | `P9-fpc-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 32348 | 71310 |
| traces_keep | `P9-gpp-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 14142 | 23950 |
| traces_keep | `P9-knn-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 101284 | 98518 |
| traces_keep | `P9-mr-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 38931 | 1281 |
| traces_keep | `P9-tridiagonal-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 358474 | 51132 |
| traces_keep.prefix_36a93d08 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.2 GB | 237 | 10313 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1625 | 31670 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1662 | 33912 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 100 | 36963 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1663 | 53373 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 100 | 36329 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1658 | 64811 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/0.1 GB | 142 | 41978 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:15j/0.1 GB | 141 | 40357 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 989 | 33570 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1033 | 34841 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 96 | 34356 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1059 | 65602 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 98 | 37064 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1039 | 53566 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:13j/0.1 GB | 133 | 43091 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:14j/0.1 GB | 131 | 42829 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 375 | 127518 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 383 | 126920 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 368 | 92494 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:9j/0.1 GB | 70 | 24267 |
| traces_keep.prefix_36a93d08 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 364 | 91858 |
| traces_keep.prefix_36a93d08 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 83735 |
| traces_keep.prefix_36a93d08 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 79190 |
| traces_keep.prefix_36a93d08 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 79 | 37795 |
| traces_keep.prefix_36a93d08 | `P4-graph-coloring-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:30j/0.1 GB | 124 | 1792 |
| traces_keep.prefix_36a93d08 | `P4-graph-coloring-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:30j/0.2 GB | 153 | 1796 |
| traces_keep.prefix_36a93d08 | `P4-graph-connectivity-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.1 GB | 72 | 3126 |
| traces_keep.prefix_36a93d08 | `P4-graph-connectivity-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.1 GB | 64 | 3012 |
| traces_keep.prefix_36a93d08 | `P4-matrix-multiplication-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10442 | 11145 |
| traces_keep.prefix_36a93d08 | `P4-matrix-multiplication-norace-small` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 324 | 1357 |
| traces_keep.prefix_36a93d08 | `P4-matrix-multiplication-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10440 | 11142 |
| traces_keep.prefix_36a93d08 | `P4-rule-110-norace-large` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1684 | 948 |
| traces_keep.prefix_36a93d08 | `P4-uts-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1735 | 14879 |
| traces_keep.prefix_36a93d08 | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 61 | 12259 |
| traces_keep.prefix_36a93d08 | `P4-uts-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1725 | 14726 |
| traces_keep.prefix_36a93d08 | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 59 | 12299 |
| traces_keep.prefix_36a93d08 | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 122603 |
| traces_keep.prefix_36a93d08 | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 70266 |
| traces_keep.prefix_36a93d08 | `P6-asyncmemcpy-memcpy_htod_kernel_race-fixed` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 84460 |
| traces_keep.prefix_36a93d08 | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 83880 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_36a93d08 | `P6-hostdevice-global_writeread_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3580 |
| traces_keep.prefix_36a93d08 | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1530 |
| traces_keep.prefix_36a93d08 | `P6-interkernel-global_readwrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2216 |
| traces_keep.prefix_36a93d08 | `P6-interkernel-global_writewrite_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 10739 |
| traces_keep.prefix_36a93d08 | `P6-interkernel-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 18247 | 11407 |
| traces_keep.prefix_36a93d08 | `P7-backprop-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 764 | 11876 |
| traces_keep.prefix_36a93d08 | `P7-bezier-surface-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 70216 |
| traces_keep.prefix_36a93d08 | `P7-bitonic-sort-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 165214 | 19200 |
| traces_keep.prefix_36a93d08 | `P7-haversine-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 279276 | 29412 |
| traces_keep.prefix_36a93d08 | `P7-heartwall-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 252269 | 84931 |
| traces_keep.prefix_36a93d08 | `P7-hotspot-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 26322 | 6658 |
| traces_keep.prefix_36a93d08 | `P7-lavaMD-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 105447 |
| traces_keep.prefix_36a93d08 | `P7-mandelbrot-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 17559 | 2735 |
| traces_keep.prefix_36a93d08 | `P7-nbody-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 146367 | 117012 |
| traces_keep.prefix_36a93d08 | `P7-particlefilter-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 6505 | 33082 |
| traces_keep.prefix_36a93d08 | `P7-pathfinder-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 310563 | 122097 |
| traces_keep.prefix_36a93d08 | `P7-srad-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 378322 | 3645 |
| traces_keep.prefix_36a93d08 | `P7-stencil1d-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 223104 | 186346 |
| traces_keep.prefix_36a93d08 | `P9-atomicCAS-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 215827 | 27998 |
| traces_keep.prefix_36a93d08 | `P9-crs-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10215 | 2702 |
| traces_keep.prefix_36a93d08 | `P9-dxtc2-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 248929 | 13449 |
| traces_keep.prefix_36a93d08 | `P9-expdist-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 239902 | 61518 |
| traces_keep.prefix_36a93d08 | `P9-fpc-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 15608 | 43831 |
| traces_keep.prefix_36a93d08 | `P9-gpp-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 14142 | 17650 |
| traces_keep.prefix_36a93d08 | `P9-knn-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 202568 | 98518 |
| traces_keep.prefix_36a93d08 | `P9-tridiagonal-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 161420 | 51130 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 239 | 1007 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 239 | 1007 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 239 | 1007 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 238 | 954 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 237 | 10134 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 242 | 960 |
| traces_keep.prefix_fe694b5 | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 242 | 958 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1638 | 34787 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1640 | 31591 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1698 | 64247 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1724 | 64610 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1005 | 34678 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1009 | 34711 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1039 | 66214 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1035 | 65986 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 380 | 83369 |
| traces_keep.prefix_fe694b5 | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 376 | 120106 |
| traces_keep.prefix_fe694b5 | `P4-matrix-multiplication-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10446 | 11146 |
| traces_keep.prefix_fe694b5 | `P4-matrix-multiplication-norace-small` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 325 | 1353 |
| traces_keep.prefix_fe694b5 | `P4-matrix-multiplication-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10444 | 11145 |
| traces_keep.prefix_fe694b5 | `P4-rule-110-norace-large` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1684 | 938 |
| traces_keep.prefix_fe694b5 | `P4-uts-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1814 | 15196 |
| traces_keep.prefix_fe694b5 | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 60 | 12285 |
| traces_keep.prefix_fe694b5 | `P4-uts-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1723 | 14827 |
| traces_keep.prefix_fe694b5 | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 80 | 12564 |
| traces_keep.prefix_fe694b5 | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 185891 |
| traces_keep.prefix_fe694b5 | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 122286 |
| traces_keep.prefix_fe694b5 | `P6-asyncmemcpy-memcpy_htod_kernel_race-fixed` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 77139 |
| traces_keep.prefix_fe694b5 | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 77553 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep.prefix_fe694b5 | `P6-hostdevice-global_writeread_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3581 |
| traces_keep.prefix_fe694b5 | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1532 |
| traces_keep.prefix_fe694b5 | `P6-interkernel-global_readwrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2214 |
| traces_keep.prefix_fe694b5 | `P6-interkernel-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 18247 | 11408 |
| traces_keep.prefix_fe694b5 | `P7-bezier-surface-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 122116 |
| traces_keep.prefix_fe694b5 | `P7-bfs-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 247 |
| traces_keep.prefix_fe694b5 | `P7-haversine-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 187453 | 25469 |
| traces_keep.prefix_fe694b5 | `P7-heartwall-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 252269 | 92643 |
| traces_keep.prefix_fe694b5 | `P7-hotspot-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 26322 | 6495 |
| traces_keep.prefix_fe694b5 | `P7-lavaMD-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 186104 |
| traces_keep.prefix_fe694b5 | `P7-pathfinder-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 254097 | 118770 |
| traces_keep.prefix_fe694b5 | `P7-srad-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 379054 | 3586 |
| traces_keep.prefix_fe694b5 | `P9-atomicCAS-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 294701 | 28475 |
| traces_keep.prefix_fe694b5 | `P9-crs-cuda` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 16074 | 2822 |
| traces_keep.prefix_fe694b5 | `P9-dxtc2-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 24474 | 7817 |
| traces_keep.prefix_fe694b5 | `P9-expdist-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 359566 | 74832 |
| traces_keep.prefix_fe694b5 | `P9-fpc-cuda` | trace-too-large, engine:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 50045 | 105485 |
| traces_keep.prefix_fe694b5 | `P9-gpp-cuda` | trace-too-large, engine:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 14142 | 121814 |
| traces_keep.prefix_fe694b5 | `P9-knn-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 303852 | 103596 |
| traces_keep.prefix_fe694b5 | `P9-mr-cuda` | engine:unsaved:no-kernel-json, trace-only:unsaved:no-kernel-json | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 116 |
| traces_keep.prefix_fe694b5 | `P9-overlap-cuda` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 14488 | 5130 |
| traces_keep.prefix_fe694b5 | `P9-tridiagonal-cuda` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 358474 | 73777 |
| traces_keep_evcand | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 237 | 10340 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1659 | 35018 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1665 | 34813 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 103 | 36899 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1647 | 53530 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 100 | 35978 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1681 | 55234 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 142 | 39800 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 142 | 42848 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1012 | 34767 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1020 | 34832 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 96 | 35458 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1050 | 54572 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 96 | 35836 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1022 | 54252 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 132 | 40340 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 130 | 42787 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 390 | 117314 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 377 | 119072 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 63 | 25548 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 371 | 84082 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 62 | 24215 |
| traces_keep_evcand | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 369 | 93279 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 61 | 7285 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 68 | 11999 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 82532 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 78481 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 67 | 2019 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 74 | 2017 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 80 | 37985 |
| traces_keep_evcand | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 79 | 38278 |
| traces_keep_evcand | `P4-graph-coloring-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 124 | 1793 |
| traces_keep_evcand | `P4-graph-coloring-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 167 | 1793 |
| traces_keep_evcand | `P4-graph-connectivity-norace-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.0 GB | 61 | 3126 |
| traces_keep_evcand | `P4-graph-connectivity-racy-large` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:3j/0.1 GB | 69 | 3046 |
| traces_keep_evcand | `P4-matrix-multiplication-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10441 | 11141 |
| traces_keep_evcand | `P4-matrix-multiplication-norace-small` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 324 | 1355 |
| traces_keep_evcand | `P4-matrix-multiplication-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10444 | 11145 |
| traces_keep_evcand | `P4-reduction-norace-large` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 50 | 6595 |
| traces_keep_evcand | `P4-rule-110-norace-large` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1684 | 950 |
| traces_keep_evcand | `P4-rule-110-norace-small` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 64 | 870 |
| traces_keep_evcand | `P4-uts-norace-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1574 | 13294 |
| traces_keep_evcand | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 79 | 11697 |
| traces_keep_evcand | `P4-uts-racy-large` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1676 | 13056 |
| traces_keep_evcand | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:1j/0.1 GB | 61 | 11780 |
| traces_keep_evcand | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 33507 |
| traces_keep_evcand | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 28938 |
| traces_keep_evcand | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | trace-too-large, engine:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 84462 |
| traces_keep_evcand | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_evcand | `P6-hostdevice-global_writeread_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3582 |
| traces_keep_evcand | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1531 |
| traces_keep_evcand | `P6-interkernel-global_readwrite_race-racy` | trace-too-large | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2218 |
| traces_keep_evcand | `P6-interkernel-global_writewrite_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11408 |
| traces_keep_evcand | `P6-interkernel-global_writewrite_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11403 |
| traces_keep_fpfix | `P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 151 | 10064 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 261 | 34836 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 261 | 34877 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 101 | 35664 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 52718 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 102 | 34780 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 54612 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 40076 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 25 | 42476 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 260 | 34724 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 260 | 34867 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 82 | 35556 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 53490 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 84 | 34585 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 52056 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 40334 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 24 | 43038 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 124901 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 122628 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 47 | 24405 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 84233 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 46 | 24476 |
| traces_keep_fpfix | `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Block_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-1296n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 92949 |
| traces_keep_fpfix | `P2-conditional_edge_neighbor_boundsBug` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 848 |
| traces_keep_fpfix | `P2-conditional_edge_neighbor_boundsBug_cond` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 844 |
| traces_keep_fpfix | `P2-conditional_edge_neighbor_boundsBug_last` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 848 |
| traces_keep_fpfix | `P2-conditional_edge_neighbor_boundsBug_last_cond` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 848 |
| traces_keep_fpfix | `P2-conditional_edge_neighbor_persistent_boundsBug` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 848 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.1 GB; trace-only:0j/0.0 GB | 61 | 7089 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 6 | 905 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.1 GB; trace-only:0j/0.0 GB | 68 | 12173 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 6 | 917 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 14 | 81606 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 8 | 1221 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 78382 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 8 | 1256 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:10j/0.1 GB; trace-only:0j/0.0 GB | 67 | 2015 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 6 | 868 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:11j/0.1 GB; trace-only:0j/0.0 GB | 74 | 2028 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:12j/0.0 GB; trace-only:0j/0.0 GB | 6 | 862 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:11j/0.1 GB; trace-only:0j/0.0 GB | 82 | 39923 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:9j/0.0 GB; trace-only:0j/0.0 GB | 8 | 1096 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:10j/0.1 GB; trace-only:0j/0.0 GB | 78 | 33591 |
| traces_keep_fpfix | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | trace-only:missing | engine:11j/0.0 GB; trace-only:0j/0.0 GB | 8 | 1084 |
| traces_keep_fpfix | `P4-graph-coloring-norace-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 70 | 1788 |
| traces_keep_fpfix | `P4-graph-coloring-racy-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 72 | 1796 |
| traces_keep_fpfix | `P4-graph-connectivity-norace-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2 | 3131 |
| traces_keep_fpfix | `P4-graph-connectivity-racy-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2 | 3038 |
| traces_keep_fpfix | `P4-matrix-multiplication-norace-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 5107 |
| traces_keep_fpfix | `P4-matrix-multiplication-norace-small` | trace-too-large, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 324 | 1356 |
| traces_keep_fpfix | `P4-matrix-multiplication-racy-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 4061 |
| traces_keep_fpfix | `P4-reduction-norace-large` | trace-only:missing | engine:1j/0.1 GB; trace-only:0j/0.0 GB | 50 | 6595 |
| traces_keep_fpfix | `P4-reduction-norace-small` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 1 | 993 |
| traces_keep_fpfix | `P4-rule-110-norace-large` | trace-too-large, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1684 | 946 |
| traces_keep_fpfix | `P4-rule-110-norace-small` | trace-only:missing | engine:16j/0.1 GB; trace-only:0j/0.0 GB | 64 | 870 |
| traces_keep_fpfix | `P4-uts-norace-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 13082 |
| traces_keep_fpfix | `P4-uts-norace-small` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 11863 |
| traces_keep_fpfix | `P4-uts-racy-large` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 12636 |
| traces_keep_fpfix | `P4-uts-racy-small` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 11785 |
| traces_keep_fpfix | `P5-race_interblock_none-lock_rtraw` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 847 |
| traces_keep_fpfix | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 18787 |
| traces_keep_fpfix | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 17127 |
| traces_keep_fpfix | `P6-asyncmemcpy-memcpy_htod_kernel_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 63051 |
| traces_keep_fpfix | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 84633 |
| traces_keep_fpfix | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix | `P6-hostdevice-global_readwrite_race-racy` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 848 |
| traces_keep_fpfix | `P6-hostdevice-global_writeread_race-racy` | trace-too-large, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3580 |
| traces_keep_fpfix | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1530 |
| traces_keep_fpfix | `P6-interkernel-global_readwrite_race-racy` | trace-too-large, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2215 |
| traces_keep_fpfix | `P6-interkernel-global_writewrite_race-fixed` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11404 |
| traces_keep_fpfix | `P6-interkernel-global_writewrite_race-racy` | engine:unsaved:all-reps-timed-out, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11402 |
| traces_keep_fpfix | `P6-memcpy-shared_readwrite_race-racy` | trace-only:missing | engine:1j/0.0 GB; trace-only:0j/0.0 GB | 0 | 846 |
| traces_keep_fpfix_tr | `P2-conditional_edge_neighbor_boundsBug` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 846 |
| traces_keep_fpfix_tr | `P2-conditional_edge_neighbor_boundsBug_cond` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 848 |
| traces_keep_fpfix_tr | `P2-conditional_edge_neighbor_boundsBug_last` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 847 |
| traces_keep_fpfix_tr | `P2-conditional_edge_neighbor_boundsBug_last_cond` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 850 |
| traces_keep_fpfix_tr | `P2-conditional_edge_neighbor_persistent_boundsBug` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 848 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 60 | 860 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 6 | 849 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 66 | 863 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 6 | 850 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 864 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 8 | 851 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.1 GB | 72 | 864 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 8 | 850 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 65 | 856 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 6 | 851 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 72 | 862 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:12j/0.0 GB | 6 | 846 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:11j/0.1 GB | 79 | 862 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:10j/0.0 GB | 7 | 852 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:10j/0.1 GB | 79 | 861 |
| traces_keep_fpfix_tr | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | engine:missing | engine:0j/0.0 GB; trace-only:10j/0.0 GB | 8 | 849 |
| traces_keep_fpfix_tr | `P4-matrix-multiplication-norace-large` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 10443 | 11141 |
| traces_keep_fpfix_tr | `P4-matrix-multiplication-norace-small` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 256 | 1101 |
| traces_keep_fpfix_tr | `P4-reduction-norace-large` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 49 | 908 |
| traces_keep_fpfix_tr | `P4-reduction-norace-small` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 1 | 850 |
| traces_keep_fpfix_tr | `P4-rule-110-norace-large` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1577 | 875 |
| traces_keep_fpfix_tr | `P4-rule-110-norace-small` | engine:missing | engine:0j/0.0 GB; trace-only:16j/0.0 GB | 38 | 850 |
| traces_keep_fpfix_tr | `P5-canary` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 850 |
| traces_keep_fpfix_tr | `P5-race_interblock_none-lock_rtraw` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 849 |
| traces_keep_fpfix_tr | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | engine:missing, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 40276 |
| traces_keep_fpfix_tr | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy` | engine:missing, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 57653 |
| traces_keep_fpfix_tr | `P6-asyncmemcpy-memcpy_htod_kernel_race-racy` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 11558 | 16430 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_readwrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_readwrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-global_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_writeread_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_writeread_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_writewrite_race_g2s-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-bulkcpy-shared_writewrite_race_g2s-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-dsmem-shared_readwrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-dsmem-shared_readwrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-dsmem-shared_writewrite_race-fixed` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-dsmem-shared_writewrite_race-racy` | error:missing-exe, engine:missing, trace-only:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 0 | 0 |
| traces_keep_fpfix_tr | `P6-hostdevice-global_readwrite_race-racy` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 850 |
| traces_keep_fpfix_tr | `P6-hostdevice-global_writeread_race-racy` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 2757 | 3582 |
| traces_keep_fpfix_tr | `P6-hostdevice-global_writewrite_race-racy` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 689 | 1532 |
| traces_keep_fpfix_tr | `P6-interkernel-global_readwrite_race-racy` | trace-too-large, engine:missing | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 1378 | 2211 |
| traces_keep_fpfix_tr | `P6-interkernel-global_writewrite_race-fixed` | engine:missing, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11404 |
| traces_keep_fpfix_tr | `P6-interkernel-global_writewrite_race-racy` | engine:missing, trace-only:unsaved:all-reps-timed-out | engine:0j/0.0 GB; trace-only:0j/0.0 GB | 9123 | 11402 |
| traces_keep_fpfix_tr | `P6-memcpy-shared_readwrite_race-racy` | engine:missing | engine:0j/0.0 GB; trace-only:1j/0.0 GB | 0 | 848 |

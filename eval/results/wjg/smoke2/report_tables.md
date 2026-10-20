### A. Per store (rows = (program, mode) with at least one kernel JSON holding records)

| store | rows | kernel JSONs with records | records | syncwarp records full / partial | rows with a diverged instance | (1) diverged instances completed / open at end | (2) memory records of not-yet-arrived lanes | rows replayed | rows where a pair moves (races / sync-only) | rows missing |
|---|---|---|---|---|---|---|---|---|---|---|
| t16-certain | 2 | 24 | 21,176 | 2,124 / 2,124 | 2 | 1,062 / 0 | 1,624 | 2 | 0 / 0 | 0 |
| **total** | 2 | 24 | 21,176 | 2,124 / 2,124 | 2 | 1,062 / 0 | 1,624 | 2 | 0 / 0 | 0 |

### B. Every row with a diverged syncwarp instance

| store | program | mode | launches with records | (1) instances completed (2 / 3+ records) / open | (2) late memory records (shared / global) | lane accesses | races L1 recorded -> merged (+/-) | sync-only L1 recorded -> merged (+/-) | L2 +/- | launches with any count change | barrier-only pass: sync-only recorded -> merged (+/-); launches = oracle / differ | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| t16-certain | P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | scalar-clock | 12 | 531 (531 / 0) / 0 | 812 (281 / 531) | 2,860 | 1 -> 1 (+0/-0) | 1 -> 1 (+0/-0) | +0/-0 | 0 | 1 -> 1 (+0/-0); 11 / 0 | complete |
| t16-certain | P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n | vector-clock | 12 | 531 (531 / 0) / 0 | 812 (281 / 531) | 2,860 | 1 -> 1 (+0/-0) | 1 -> 1 (+0/-0) | +0/-0 | 0 | 1 -> 1 (+0/-0); 11 / 0 | complete |

Validation (scan vs parsed records): {'files': 22, 'recs equal': 22, 'sw_full equal': 22, 'sw_partial equal': 22, 'seq sorted in file': 22}


## Programs whose strength table differs between `generic` and `token`

43 of 598 selected programs (P4: 16, P5: 27); skipped (no t9-after dir): 4. The opcodes whose strength changes, with their pc count over those programs' dots: `LDG.E.STRONG.SYS` 1599, `STG.E.STRONG.SYS` 1225.

## Race-set deltas (vector-clock dumps, pc pairs: T9 oracle under `generic` vs T10 oracle under `token`)

| pset | program | pairs | DR before | DR after | SC before | SC after | DR -> SC | SC -> DR | lost | gained | sync pairs +/- |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P4 | P4-matrix-multiplication-norace-large | no vector-clock dump | | | | | | | | | |
| P4 | P4-matrix-multiplication-norace-small | 4 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-matrix-multiplication-racy-large | no vector-clock dump | | | | | | | | | |
| P4 | P4-matrix-multiplication-racy-small | 6 | 6 | 2 | 0 | 4 | 4 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-reduction-norace-large | 11 | 11 | 0 | 0 | 11 | 11 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-reduction-norace-small | 10 | 10 | 0 | 0 | 10 | 10 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-reduction-racy-large | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-reduction-racy-small | 11 | 11 | 0 | 0 | 11 | 11 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-rule-110-norace-large | 242 | 242 | 0 | 0 | 242 | 242 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-rule-110-norace-small | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-rule-110-racy-large | 934 | 934 | 128 | 0 | 806 | 806 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-rule-110-racy-small | 64 | 64 | 32 | 0 | 32 | 32 | 0 | 0 | 0 | +0/-0 |
| P4 | P4-uts-norace-large | no vector-clock dump | | | | | | | | | |
| P4 | P4-uts-norace-small | no vector-clock dump | | | | | | | | | |
| P4 | P4-uts-racy-large | no vector-clock dump | | | | | | | | | |
| P4 | P4-uts-racy-small | no vector-clock dump | | | | | | | | | |
| P5 | P5-norace_interblock_fence_raw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interblock_lock_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interwarp-block_fence_hrf-indirect | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interwarp_blkfence_raw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interwarp_blklock_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interwarp_dev-blklock_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_interwarp_fence_raw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_intrawarp_none-blkatom | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_intrawarp_none-blklock-no-tf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-norace_intrawarp_none-blklock_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_blkfence_raw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_blklock_waw | 4 | 4 | 3 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_fence_rtraw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_lock-blkfence_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_lock-no-stf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_lock-no-tf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_none-atom_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_none-lock_rtraw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interblock_none-lock_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_blklock-no-stf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_blklock-no-tf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_dev-blklock-no-stf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_dev-blklock-no-tf_waw | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_none-atom_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_none-blkatom_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_none-blklock_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| P5 | P5-race_interwarp_none-lock_waw | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | +0/-0 |
| **all** | | 1306 | 1306 | 165 | 0 | 1141 | 1141 | 0 | 0 | 0 | +0/-0 |

## Verdict deltas (BEFORE = T9's AFTER rows: the pre-T10 detector on t9-after; AFTER = this checkout on t10-after)

Left out: P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-default-1296n, P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n, P1-CC_CUDA_V_Topo_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-default-1296n, P1-CC_CUDA_V_Topo_Pull_Determ_IntType_Persist_RaceBug_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n, P6-asyncmemcpy-memcpy_htod_kernel_race-racy, P7-hotspot-cuda, P9-crs-cuda, P9-fpc-cuda, P9-gpp-cuda, P9-mr-cuda.

| mode | before | after | programs |
|---|---|---|---|
| scalar-clock | CLEAN | CLEAN | 308 |
| scalar-clock | RACE | CLEAN | 20 |
| scalar-clock | RACE | RACE | 260 |
| vector-clock | CLEAN | CLEAN | 302 |
| vector-clock | RACE | CLEAN | 19 |
| vector-clock | RACE | RACE | 232 |
| vector-clock | TIMEOUT | TIMEOUT | 35 |

### Per suite (labelled programs; TP / FN / FP / TN at Race u Latent and at Race alone; `sc` = programs with at least one SC report, informational, D2)

| pset | mode | programs | Race u Latent TP/FN/FP/TN | Race alone TP/FN/FP/TN | sc programs (labelled RACE / CLEAN) |
|---|---|---|---|---|---|
| P1 | scalar-clock | 384 -> 384 | 196/0/0/188 -> 196/0/0/188 | 196/0/0/188 -> 196/0/0/188 | 0/66 -> 0/66 |
| P1 | vector-clock | 384 -> 384 | 174/0/0/187 -> 174/0/0/187 | 174/0/0/187 -> 174/0/0/187 | 0/66 -> 0/66 |
| P2 | scalar-clock | 58 -> 58 | 25/5/0/28 -> 25/5/0/28 | 25/5/0/28 -> 25/5/0/28 | 0/0 -> 0/0 |
| P2 | vector-clock | 58 -> 58 | 25/5/0/28 -> 25/5/0/28 | 25/5/0/28 -> 25/5/0/28 | 0/0 -> 0/0 |
| P3 | scalar-clock | 58 -> 58 | 0/0/16/42 -> 0/0/16/42 | 0/0/16/42 -> 0/0/16/42 | 0/34 -> 0/34 |
| P3 | vector-clock | 58 -> 58 | 0/0/14/42 -> 0/0/14/42 | 0/0/14/42 -> 0/0/14/42 | 0/34 -> 0/34 |
| P4 | scalar-clock | 28 -> 28 | 14/0/6/8 -> 14/0/2/12 | 14/0/6/8 -> 14/0/2/12 | 0/0 -> 6/6 |
| P4 | vector-clock | 28 -> 28 | 9/0/5/4 -> 9/0/2/7 | 9/0/5/4 -> 7/2/0/9 | 0/0 -> 5/5 |
| P5 | scalar-clock | 33 -> 33 | 18/1/0/14 -> 2/17/0/14 | 18/1/0/14 -> 2/17/0/14 | 0/0 -> 17/0 |
| P5 | vector-clock | 33 -> 33 | 19/0/0/14 -> 3/16/0/14 | 10/9/0/14 -> 3/16/0/14 | 0/0 -> 17/0 |
| P6 | scalar-clock | 27 -> 27 | 5/5/0/17 -> 5/5/0/17 | 5/5/0/17 -> 5/5/0/17 | 0/0 -> 0/0 |
| P6 | vector-clock | 27 -> 27 | 5/5/0/17 -> 5/5/0/17 | 5/5/0/17 -> 5/5/0/17 | 0/0 -> 0/0 |

Rows present on one side only (not compared below): 0.


### Race u Latent (the harness verdict): TPs gained 0, TPs lost 32, new FPs 0, FPs removed 7

TPs lost: P5-race_interblock_blkfence_raw (scalar-clock), P5-race_interblock_blkfence_raw (vector-clock), P5-race_interblock_fence_rtraw (scalar-clock), P5-race_interblock_fence_rtraw (vector-clock), P5-race_interblock_lock-blkfence_waw (scalar-clock), P5-race_interblock_lock-blkfence_waw (vector-clock), P5-race_interblock_lock-no-stf_waw (scalar-clock), P5-race_interblock_lock-no-stf_waw (vector-clock), P5-race_interblock_lock-no-tf_waw (scalar-clock), P5-race_interblock_lock-no-tf_waw (vector-clock), P5-race_interblock_none-atom_waw (scalar-clock), P5-race_interblock_none-atom_waw (vector-clock), P5-race_interblock_none-lock_rtraw (scalar-clock), P5-race_interblock_none-lock_rtraw (vector-clock), P5-race_interblock_none-lock_waw (scalar-clock), P5-race_interblock_none-lock_waw (vector-clock), P5-race_interwarp_blklock-no-stf_waw (scalar-clock), P5-race_interwarp_blklock-no-stf_waw (vector-clock), P5-race_interwarp_blklock-no-tf_waw (scalar-clock), P5-race_interwarp_blklock-no-tf_waw (vector-clock), P5-race_interwarp_dev-blklock-no-stf_waw (scalar-clock), P5-race_interwarp_dev-blklock-no-stf_waw (vector-clock), P5-race_interwarp_dev-blklock-no-tf_waw (scalar-clock), P5-race_interwarp_dev-blklock-no-tf_waw (vector-clock), P5-race_interwarp_none-atom_waw (scalar-clock), P5-race_interwarp_none-atom_waw (vector-clock), P5-race_interwarp_none-blkatom_waw (scalar-clock), P5-race_interwarp_none-blkatom_waw (vector-clock), P5-race_interwarp_none-blklock_waw (scalar-clock), P5-race_interwarp_none-blklock_waw (vector-clock), P5-race_interwarp_none-lock_waw (scalar-clock), P5-race_interwarp_none-lock_waw (vector-clock)

FPs removed: P4-matrix-multiplication-norace-large (scalar-clock), P4-matrix-multiplication-norace-small (scalar-clock), P4-matrix-multiplication-norace-small (vector-clock), P4-rule-110-norace-large (scalar-clock), P4-rule-110-norace-large (vector-clock), P4-rule-110-norace-small (scalar-clock), P4-rule-110-norace-small (vector-clock)


### Race alone: TPs gained 0, TPs lost 25, new FPs 0, FPs removed 9

TPs lost: P4-reduction-racy-large (vector-clock), P4-reduction-racy-small (vector-clock), P5-race_interblock_blkfence_raw (scalar-clock), P5-race_interblock_fence_rtraw (scalar-clock), P5-race_interblock_fence_rtraw (vector-clock), P5-race_interblock_lock-blkfence_waw (scalar-clock), P5-race_interblock_lock-no-stf_waw (scalar-clock), P5-race_interblock_lock-no-tf_waw (scalar-clock), P5-race_interblock_none-atom_waw (scalar-clock), P5-race_interblock_none-atom_waw (vector-clock), P5-race_interblock_none-lock_rtraw (scalar-clock), P5-race_interblock_none-lock_waw (scalar-clock), P5-race_interblock_none-lock_waw (vector-clock), P5-race_interwarp_blklock-no-stf_waw (scalar-clock), P5-race_interwarp_blklock-no-tf_waw (scalar-clock), P5-race_interwarp_dev-blklock-no-stf_waw (scalar-clock), P5-race_interwarp_dev-blklock-no-tf_waw (scalar-clock), P5-race_interwarp_none-atom_waw (scalar-clock), P5-race_interwarp_none-atom_waw (vector-clock), P5-race_interwarp_none-blkatom_waw (scalar-clock), P5-race_interwarp_none-blkatom_waw (vector-clock), P5-race_interwarp_none-blklock_waw (scalar-clock), P5-race_interwarp_none-blklock_waw (vector-clock), P5-race_interwarp_none-lock_waw (scalar-clock), P5-race_interwarp_none-lock_waw (vector-clock)

FPs removed: P4-matrix-multiplication-norace-large (scalar-clock), P4-matrix-multiplication-norace-small (scalar-clock), P4-matrix-multiplication-norace-small (vector-clock), P4-reduction-norace-large (vector-clock), P4-reduction-norace-small (vector-clock), P4-rule-110-norace-large (scalar-clock), P4-rule-110-norace-large (vector-clock), P4-rule-110-norace-small (scalar-clock), P4-rule-110-norace-small (vector-clock)


Every (program, mode) whose verdict, report set or class counts moved (classes from the harness's `classes=` note, before -> after):

| mode | program | label | verdict | Race alone | #report ids | classes before | classes after | strength table differs |
|---|---|---|---|---|---|---|---|---|
| scalar-clock | P4-matrix-multiplication-norace-large | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 3 -> 0 | race=3 | sc=3 | yes |
| scalar-clock | P4-matrix-multiplication-norace-small | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 2 -> 0 | race=2 | sc=2 | yes |
| vector-clock | P4-matrix-multiplication-norace-small | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 4 -> 0 | structural=4 | sc=4 | yes |
| scalar-clock | P4-matrix-multiplication-racy-large | RACE | RACE -> RACE | RACE -> RACE | 6 -> 3 | race=6 | race=3 sc=3 | yes |
| scalar-clock | P4-matrix-multiplication-racy-small | RACE | RACE -> RACE | RACE -> RACE | 5 -> 3 | race=5 | race=3 sc=2 | yes |
| vector-clock | P4-matrix-multiplication-racy-small | RACE | RACE -> RACE | RACE -> RACE | 7 -> 3 | structural=7 | sc=4 structural=3 | yes |
| scalar-clock | P4-reduction-norace-large | CLEAN | RACE -> RACE | RACE -> RACE | 12 -> 1 | race=12 | race=1 sc=11 | yes |
| vector-clock | P4-reduction-norace-large | CLEAN | RACE -> RACE | RACE -> CLEAN | 13 -> 1 | latent=2 structural=11 | latent=1 latent-sc=1 sc=11 | yes |
| scalar-clock | P4-reduction-norace-small | CLEAN | RACE -> RACE | RACE -> RACE | 13 -> 1 | race=13 | race=1 sc=12 | yes |
| vector-clock | P4-reduction-norace-small | CLEAN | RACE -> RACE | RACE -> CLEAN | 13 -> 1 | latent=3 structural=10 | latent=1 latent-sc=2 sc=10 | yes |
| scalar-clock | P4-reduction-racy-large | RACE | RACE -> RACE | RACE -> RACE | 14 -> 1 | race=14 | race=1 sc=13 | yes |
| vector-clock | P4-reduction-racy-large | RACE | RACE -> RACE | RACE -> CLEAN | 16 -> 1 | latent=4 structural=12 | latent=1 latent-sc=3 sc=12 | yes |
| scalar-clock | P4-reduction-racy-small | RACE | RACE -> RACE | RACE -> RACE | 15 -> 1 | race=15 | race=1 sc=14 | yes |
| vector-clock | P4-reduction-racy-small | RACE | RACE -> RACE | RACE -> CLEAN | 16 -> 1 | latent=5 structural=11 | latent=1 latent-sc=4 sc=11 | yes |
| scalar-clock | P4-rule-110-norace-large | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 18 -> 0 | race=18 | sc=18 | yes |
| vector-clock | P4-rule-110-norace-large | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 18 -> 0 | latent=13 structural=5 | latent-sc=18 | yes |
| scalar-clock | P4-rule-110-norace-small | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 2 -> 0 | race=2 | sc=2 | yes |
| vector-clock | P4-rule-110-norace-small | CLEAN | RACE -> CLEAN | RACE -> CLEAN | 2 -> 0 | latent=1 structural=1 | latent-sc=2 | yes |
| scalar-clock | P4-rule-110-racy-large | RACE | RACE -> RACE | RACE -> RACE | 20 -> 2 | race=20 | race=2 sc=18 | yes |
| vector-clock | P4-rule-110-racy-large | RACE | RACE -> RACE | RACE -> RACE | 20 -> 2 | latent=4 structural=16 | latent-sc=5 sc=13 structural=2 | yes |
| scalar-clock | P4-rule-110-racy-small | RACE | RACE -> RACE | RACE -> RACE | 5 -> 3 | race=5 | race=3 sc=2 | yes |
| vector-clock | P4-rule-110-racy-small | RACE | RACE -> RACE | RACE -> RACE | 5 -> 3 | structural=5 | sc=2 structural=3 | yes |
| scalar-clock | P5-race_interblock_blkfence_raw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_blkfence_raw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interblock_blklock_waw | RACE | RACE -> RACE | RACE -> RACE | 4 -> 3 | race=4 | race=3 sc=1 | yes |
| vector-clock | P5-race_interblock_blklock_waw | RACE | RACE -> RACE | RACE -> RACE | 4 -> 3 | structural=4 | sc=1 structural=3 | yes |
| scalar-clock | P5-race_interblock_fence_rtraw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_fence_rtraw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interblock_lock-blkfence_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_lock-blkfence_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interblock_lock-no-stf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_lock-no-stf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interblock_lock-no-tf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_lock-no-tf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interblock_none-atom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_none-atom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interblock_none-lock_rtraw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_none-lock_rtraw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interblock_none-lock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interblock_none-lock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interwarp_blklock-no-stf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_blklock-no-stf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interwarp_blklock-no-tf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_blklock-no-tf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interwarp_dev-blklock-no-stf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_dev-blklock-no-stf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interwarp_dev-blklock-no-tf_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_dev-blklock-no-tf_waw | RACE | RACE -> CLEAN | CLEAN -> CLEAN | 1 -> 0 | latent=1 | latent-sc=1 | yes |
| scalar-clock | P5-race_interwarp_none-atom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_none-atom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interwarp_none-blkatom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_none-blkatom_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interwarp_none-blklock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_none-blklock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |
| scalar-clock | P5-race_interwarp_none-lock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | race=1 | sc=1 | yes |
| vector-clock | P5-race_interwarp_none-lock_waw | RACE | RACE -> CLEAN | RACE -> CLEAN | 1 -> 0 | structural=1 | sc=1 | yes |

Rows that moved on a program whose strength table does not differ: 0.


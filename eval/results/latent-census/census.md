## Headline (generated)

- Programs with a vector-clock verdict from a complete kept dump: 558 (scalar-clock: 597).
- Labelled-racy programs reported RACE by vector-clock: 236; of these caught **only** through `latent` (no structural/model_bug report): **10** — `P5-race_interblock_blkfence_raw`, `P5-race_interblock_fence_rtraw`, `P5-race_interblock_lock-blkfence_waw`, `P5-race_interblock_lock-no-stf_waw`, `P5-race_interblock_lock-no-tf_waw`, `P5-race_interblock_none-lock_rtraw`, `P5-race_interwarp_blklock-no-stf_waw`, `P5-race_interwarp_blklock-no-tf_waw`, `P5-race_interwarp_dev-blklock-no-stf_waw`, `P5-race_interwarp_dev-blklock-no-tf_waw`.
- `latent` reports (deduped pc pairs): **50** on 20 programs — on labelled-racy 25, on labelled race-free **25** (50.0% of all latent reports; 5 programs), unlabelled 0.
- Labelled race-free programs reported RACE by vector-clock: 20; of these RACE **only** through `latent`: 3 — `P4-matrix-multiplication-norace-small`, `P4-rule-110-norace-large`, `P4-rule-110-norace-small`.
- Hand-off fencing of the latent pairs (Definition "Gate" adjacency per observed hand-off RMW; `certified` = the hand-off lies in R3's dominance program order, `reach` = only CFG-reachable):
  - race-free, certified: acquire side ungated — 2
  - race-free, reach: acquire side ungated — 2
  - race-free, reach: gated hand-off present — 21
  - racy, certified: acquire side ungated — 4
  - racy, certified: both sides ungated — 3
  - racy, certified: gated hand-off present — 1
  - racy, certified: release side ungated — 7
  - racy, reach: acquire side ungated — 1
  - racy, reach: both sides ungated — 3
  - racy, reach: gated hand-off present — 6

## Vector-clock TP/FP with and without `latent` (recorded runs; no detector change)

`without latent` = the program's verdict if every `latent` report (and a `benign` report whose underlying class is latent) were ORDERED -- the "ordered in this execution" reading of D8 applied to the unchanged engine (I1/I2/I4 as they are).

| suite | labelled racy | TP | TP without latent | labelled race-free | FP | FP without latent |
|---|---|---|---|---|---|---|
| P1 | 178 | 178 | 178 | 187 | 0 | 0 |
| P2 | 30 | 25 | 25 | 28 | 0 | 0 |
| P3 | 0 | 0 | 0 | 56 | 14 | 14 |
| P4 | 9 | 9 | 9 | 9 | 5 | 2 |
| P5 | 19 | 19 | 9 | 14 | 0 | 0 |
| P6 | 10 | 5 | 5 | 17 | 0 | 0 |
| P9 | 0 | 0 | 0 | 1 | 1 | 1 |
| **all** | 246 | 236 | 226 | 312 | 20 | 17 |

## Census by suite and mode (deduped reports; recorded dumps)

| suite | mode | programs | analysed | RACE programs | structural | model_bug | latent | benign | race (sc) | barrier-ordered | ordered | event_candidate | event_candidate ∧ RACE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 365 | 365 | 178 | 1158 | 0 | 1 | 0 | 0 | 40 | 3791 | 214 | 214 |
| P2 | vector-clock | 58 | 58 | 25 | 34 | 0 | 0 | 8 | 0 | 6 | 95 | 0 | 0 |
| P3 | vector-clock | 56 | 56 | 14 | 14 | 0 | 0 | 0 | 0 | 18 | 756 | 0 | 0 |
| P4 | vector-clock | 18 | 18 | 14 | 90 | 0 | 39 | 0 | 0 | 66 | 293 | 22 | 22 |
| P5 | vector-clock | 33 | 33 | 19 | 11 | 0 | 10 | 0 | 0 | 0 | 61 | 3 | 1 |
| P6 | vector-clock | 27 | 27 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 13 | 142 | 0 | 0 | 0 | 2 | 8 | 127 | 127 |
| P1 | scalar-clock | 388 | 388 | 200 | 0 | 0 | 0 | 0 | 1286 | 52 | 4216 | 216 | 216 |
| P2 | scalar-clock | 58 | 58 | 25 | 0 | 0 | 0 | 8 | 34 | 6 | 95 | 0 | 0 |
| P3 | scalar-clock | 58 | 58 | 16 | 0 | 0 | 0 | 0 | 16 | 20 | 803 | 0 | 0 |
| P4 | scalar-clock | 28 | 28 | 20 | 0 | 0 | 0 | 0 | 165 | 83 | 1096 | 32 | 22 |
| P5 | scalar-clock | 33 | 33 | 18 | 0 | 0 | 0 | 0 | 20 | 0 | 62 | 3 | 1 |
| P6 | scalar-clock | 28 | 28 | 5 | 0 | 0 | 0 | 0 | 5 | 0 | 4 | 0 | 0 |
| P7 | scalar-clock | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 |
| P9 | scalar-clock | 3 | 3 | 1 | 0 | 0 | 0 | 0 | 7 | 2 | 117 | 65 | 2 |

## Latent-only true positives (compact)

| program | pc pair | type | dist | R3 declined | fence status | hand-off(s) |
|---|---|---|---|---|---|---|
| `P5-race_interblock_blkfence_raw` | 0x170↔0xf0 | RAW | grid | missing-hop | both sides ungated | 0x190→0x90 rel− acq− |
| `P5-race_interblock_fence_rtraw` | 0x1f0↔0x100 | WAR | grid | no-release-point | acquire side ungated | (reach) 0x1e0→0x90 rel+ acq− |
| `P5-race_interblock_lock-blkfence_waw` | 0x150↔0x280 | WAW | grid | cs-unfenced | acquire side ungated | 0x190→0x210 rel+ acq− |
| `P5-race_interblock_lock-no-stf_waw` | 0x150↔0x270 | WAW | grid | cs-unfenced | acquire side ungated | 0x190→0x210 rel+ acq− |
| `P5-race_interblock_lock-no-tf_waw` | 0x150↔0x270 | WAW | grid | no-release-fence | release side ungated | 0x160→0x1e0 rel− acq+ |
| `P5-race_interblock_none-lock_rtraw` | 0x140↔0x340 | WAR | grid | past-release | gated hand-off present | 0x1b0→0x230 rel+ acq+ |
| `P5-race_interwarp_blklock-no-stf_waw` | 0x150↔0x250 | WAW | block | cs-unfenced | acquire side ungated | 0x170→0x1f0 rel+ acq− |
| `P5-race_interwarp_blklock-no-tf_waw` | 0x150↔0x250 | WAW | block | no-release-fence | release side ungated | 0x160→0x1e0 rel− acq+ |
| `P5-race_interwarp_dev-blklock-no-stf_waw` | 0x150↔0x250 | WAW | block | cs-unfenced | acquire side ungated | 0x170→0x1f0 rel+ acq− |
| `P5-race_interwarp_dev-blklock-no-tf_waw` | 0x150↔0x270 | WAW | block | no-release-fence | release side ungated | 0x160→0x1e0 rel− acq+ |

## Latent pairs on labelled-racy programs

| program | label | kernel | pc pair (anc↔cur) | space | type | dist | event cand. | barrier-pass conflicts | R3 declined | observed hand-off(s), fence | scalar-clock (own run) | scalar-clock (same trace) | source | tag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | RACE | bfs_vertex_data(ECLgraph, int*, int cons | 0x6d0↔0x4d0 | global | WAW | block | no | 1 | no-release-fence | (reach) 0x2e0(ATOMG.E.MAX.S32.STRONG.GPU)→0x2e0(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x390(ATOMG.E.ADD.STRONG.GPU)→0x390(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x9b0(ATOMG.E.ADD.STRONG.GPU)→0x390(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x4e0(ATOMG.E.MAX.S32.STRONG.GPU)→0x4e0(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x6e0(ATOMG.E.MAX.S32.STRONG.GPU)→0x4e0(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x390(ATOMG.E.ADD.STRONG.GPU)→0x590(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x590(ATOMG.E.ADD.STRONG.GPU)→0x590(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x790(ATOMG.E.ADD.STRONG.GPU)→0x590(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x6e0(ATOMG.E.MAX.S32.STRONG.GPU)→0x6e0(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x900(ATOMG.E.MAX.S32.STRONG.GPU)→0x6e0(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x590(ATOMG.E.ADD.STRONG.GPU)→0x790(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x790(ATOMG.E.ADD.STRONG.GPU)→0x790(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x9b0(ATOMG.E.ADD.STRONG.GPU)→0x790(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x900(ATOMG.E.MAX.S32.STRONG.GPU)→0x900(ATOMG.E.MAX.S32.STRONG.GPU) block rel− acq−; 0x790(ATOMG.E.ADD.STRONG.GPU)→0x9b0(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0x9b0(ATOMG.E.ADD.STRONG.GPU)→0x9b0(ATOMG.E.ADD.STRONG.GPU) block rel− acq−; 0xe70(ATOMG.E.ADD.STRONG.GPU)→0x9b0(ATOMG.E.ADD.STRONG.GPU) block rel− acq− | race/RACE | race/RACE | BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug.cu:85 |  |
| `P4-matrix-multiplication-racy-small` | RACE | matMultKernel(int*, int*, int volatile*, | 0x590↔0x580 | global | RAW | block | no | 346240 | cs-unfenced | 0x5a0(ATOMG.E.EXCH.STRONG.SM)→0x540(ATOMG.E.CAS.STRONG.SM) block rel− acq− | race/RACE | race/RACE | mm_kernel.cu:104 |  |
| `P4-matrix-multiplication-racy-small` | RACE | matMultKernel(int*, int*, int volatile*, | 0x950↔0x930 | global | RAW | block | no | 126784 | cs-unfenced | 0x960(ATOMG.E.EXCH.STRONG.SM)→0x8f0(ATOMG.E.CAS.STRONG.SM) block rel− acq− | race/RACE | race/RACE | mm_kernel.cu:104 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0x5f0↔0x720 | global | RAW | block | no | 960 | no-release-fence | 0x600(ATOMG.E.EXCH.STRONG.SM)→0x6d0(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0xec0 | global | RAW | grid | no | 29 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0x12d0↔0x13e0 | global | RAW | block | no | 32 | no-release-fence | 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0x5f0↔0x720 | global | RAW | block | no | 128 | no-release-fence | 0x600(ATOMG.E.EXCH.STRONG.SM)→0x6d0(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0xec0 | global | RAW | grid | no | 3 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0x1640 | global | WAW | grid | yes | 1 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq−; 0x10a0(ATOMG.E.ADD.STRONG.SM)→0xfd0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0xfd0(ATOMG.E.EXCH.STRONG.SM)→0x10a0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1230(ATOMG.E.ADD.STRONG.SM)→0x1160(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1160(ATOMG.E.EXCH.STRONG.SM)→0x1230(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1390(ATOMG.E.ADD.STRONG.SM)→0x12e0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:207 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0x12d0↔0x13e0 | global | RAW | block | no | 32 | no-release-fence | 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xd90↔0x1630 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x16b0 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x1730 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x1950 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x1950 | global | RAW | grid | no | 4095 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P5-race_interblock_blkfence_raw` | RACE | kmain(unsigned int volatile*) | 0x170↔0xf0 | global | RAW | grid | no | 1 | missing-hop | 0x190(ATOMG.E.EXCH.STRONG.GPU)→0x90(ATOMG.E.EXCH.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | race_interblock_blkfence_raw.cu:25 ; race_interblock_blkfence_raw.cu:32 |  |
| `P5-race_interblock_fence_rtraw` | RACE | kmain(unsigned int volatile*) | 0x1f0↔0x100 | global | WAR | grid | no | 1 | no-release-point | (reach) 0x1e0(ATOMG.E.EXCH.STRONG.GPU)→0x90(ATOMG.E.EXCH.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | race_interblock_fence_rtraw.cu:30 ; race_interblock_fence_rtraw.cu:36 |  |
| `P5-race_interblock_lock-blkfence_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x280 | global | WAW | grid | no | 1 | cs-unfenced | 0x190(ATOMG.E.EXCH.STRONG.GPU)→0x210(ATOMG.E.CAS.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | race_interblock_lock-blkfence_waw.cu:25 ; race_interblock_lock-blkfence_waw.cu:33 |  |
| `P5-race_interblock_lock-no-stf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x270 | global | WAW | grid | no | 1 | cs-unfenced | 0x190(ATOMG.E.EXCH.STRONG.GPU)→0x210(ATOMG.E.CAS.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | race_interblock_lock-no-stf_waw.cu:25 ; race_interblock_lock-no-stf_waw.cu:33 |  |
| `P5-race_interblock_lock-no-tf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x270 | global | WAW | grid | no | 1 | no-release-fence | 0x160(ATOMG.E.EXCH.STRONG.GPU)→0x1e0(ATOMG.E.CAS.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | race_interblock_lock-no-tf_waw.cu:25 ; race_interblock_lock-no-tf_waw.cu:32 |  |
| `P5-race_interblock_none-lock_rtraw` | RACE | kmain(unsigned int volatile*) | 0x140↔0x340 | global | WAR | grid | yes | 1 | past-release | 0x1b0(ATOMG.E.EXCH.STRONG.GPU)→0x230(ATOMG.E.CAS.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | race_interblock_none-lock_rtraw.cu:31 ; race_interblock_none-lock_rtraw.cu:37 |  |
| `P5-race_interwarp_blklock-no-stf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x250 | global | WAW | block | no | 1 | cs-unfenced | 0x170(ATOMG.E.EXCH.STRONG.SM)→0x1f0(ATOMG.E.CAS.STRONG.SM) block rel+ acq− | race/RACE | race/RACE | race_interwarp_blklock-no-stf_waw.cu:25 ; race_interwarp_blklock-no-stf_waw.cu:33 |  |
| `P5-race_interwarp_blklock-no-tf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x250 | global | WAW | block | no | 1 | no-release-fence | 0x160(ATOMG.E.EXCH.STRONG.SM)→0x1e0(ATOMG.E.CAS.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | race_interwarp_blklock-no-tf_waw.cu:25 ; race_interwarp_blklock-no-tf_waw.cu:32 |  |
| `P5-race_interwarp_dev-blklock-no-stf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x250 | global | WAW | block | no | 1 | cs-unfenced | 0x170(ATOMG.E.EXCH.STRONG.SM)→0x1f0(ATOMG.E.CAS.STRONG.GPU) block rel+ acq− | race/RACE | race/RACE | race_interwarp_dev-blklock-no-stf_waw.cu:25 ; race_interwarp_dev-blklock-no-stf_waw.cu:33 |  |
| `P5-race_interwarp_dev-blklock-no-tf_waw` | RACE | kmain(unsigned int volatile*) | 0x150↔0x270 | global | WAW | block | no | 1 | no-release-fence | 0x160(ATOMG.E.EXCH.STRONG.SM)→0x1e0(ATOMG.E.CAS.STRONG.GPU) block rel− acq+ | race/RACE | race/RACE | race_interwarp_dev-blklock-no-tf_waw.cu:25 ; race_interwarp_dev-blklock-no-tf_waw.cu:32 |  |

## Latent pairs on labelled race-free programs (the tier's cost)

| program | label | kernel | pc pair (anc↔cur) | space | type | dist | event cand. | barrier-pass conflicts | R3 declined | observed hand-off(s), fence | scalar-clock (own run) | scalar-clock (same trace) | source | tag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `P4-matrix-multiplication-norace-small` | CLEAN | matMultKernel(int*, int*, int volatile*, | 0x5a0↔0x590 | global | RAW | block | no | 347328 | cs-unfenced | 0x5c0(ATOMG.E.EXCH.STRONG.SM)→0x540(ATOMG.E.CAS.STRONG.SM) block rel+ acq− | race/RACE | race/RACE | mm_kernel.cu:104 |  |
| `P4-matrix-multiplication-norace-small` | CLEAN | matMultKernel(int*, int*, int volatile*, | 0x980↔0x960 | global | RAW | block | no | 126464 | cs-unfenced | 0x9a0(ATOMG.E.EXCH.STRONG.SM)→0x910(ATOMG.E.CAS.STRONG.SM) block rel+ acq− | race/RACE | race/RACE | mm_kernel.cu:104 |  |
| `P4-reduction-norace-large` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0xef0 | global | RAW | grid | no | 29 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-norace-small` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0xef0 | global | RAW | grid | no | 3 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-norace-small` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0x1680 | global | WAW | grid | yes | 1 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq−; 0x10d0(ATOMG.E.ADD.STRONG.SM)→0x1000(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1000(ATOMG.E.EXCH.STRONG.SM)→0x10d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1260(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1260(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x13d0(ATOMG.E.ADD.STRONG.SM)→0x1320(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1320(ATOMG.E.EXCH.STRONG.SM)→0x13d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+ | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:207 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xd90↔0x15d0 | global | RAW | grid | no | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xd90↔0x1650 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xd90↔0x1e00 | global | RAW | grid | yes | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x1650 | global | RAW | grid | no | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x16d0 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x1e00 | global | RAW | grid | yes | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x1f80 | global | RAW | grid | yes | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x16d0 | global | RAW | grid | no | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x1750 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x1f80 | global | RAW | grid | yes | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x2100 | global | RAW | grid | yes | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x1750 | global | RAW | grid | no | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x1970 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x2100 | global | RAW | grid | yes | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x2270 | global | RAW | grid | yes | 15359 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x1970 | global | RAW | grid | no | 4095 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x2270 | global | RAW | grid | yes | 1 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-large` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x2510 | global | RAW | grid | yes | 4095 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-small` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x1970 | global | RAW | block | no | 1023 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1a90(ATOMG.E.ADD.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1b90(ATOMG.E.ADD.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-norace-small` | CLEAN | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x2510 | global | RAW | block | yes | 1023 | no-release-point | (reach) 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1a90(ATOMG.E.ADD.STRONG.SM)→0x1220(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1b90(ATOMG.E.ADD.STRONG.GPU)→0x1310(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1220(ATOMG.E.ADD.STRONG.SM)→0x1a90(ATOMG.E.ADD.STRONG.SM) block rel− acq+; 0x1140(ATOMG.E.EXCH.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel+ acq+; 0x1310(ATOMG.E.ADD.STRONG.GPU)→0x1b90(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:141 ; r110_kernel.cu:75 |  |

R3 decline reasons, race-free side: no-release-point 23, cs-unfenced 2; racy side: no-release-point 9, no-release-fence 8, cs-unfenced 6, missing-hop 1, past-release 1.

## Other tools on the programs with latent reports (merged baselines CSVs)

| program | label | latent-only? | racecheck | hirace | iguard | supercollider |
|---|---|---|---|---|---|---|
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | RACE | no | CLEAN | — | RACE | — |
| `P4-matrix-multiplication-norace-small` | CLEAN | no | CLEAN | — | CLEAN | — |
| `P4-matrix-multiplication-racy-small` | RACE | no | CLEAN | — | RACE | — |
| `P4-reduction-norace-large` | CLEAN | no | CLEAN | — | RACE | — |
| `P4-reduction-norace-small` | CLEAN | no | CLEAN | — | RACE | — |
| `P4-reduction-racy-large` | RACE | no | CLEAN | — | RACE | — |
| `P4-reduction-racy-small` | RACE | no | CLEAN | — | RACE | — |
| `P4-rule-110-norace-large` | CLEAN | no | CLEAN | — | CLEAN | — |
| `P4-rule-110-norace-small` | CLEAN | no | CLEAN | — | CLEAN | — |
| `P4-rule-110-racy-large` | RACE | no | CLEAN | — | RACE | — |
| `P5-race_interblock_blkfence_raw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interblock_fence_rtraw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interblock_lock-blkfence_waw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interblock_lock-no-stf_waw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interblock_lock-no-tf_waw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interblock_none-lock_rtraw` | RACE | yes | CLEAN | — | CLEAN | — |
| `P5-race_interwarp_blklock-no-stf_waw` | RACE | yes | CLEAN | — | CLEAN | — |
| `P5-race_interwarp_blklock-no-tf_waw` | RACE | yes | CLEAN | — | RACE | — |
| `P5-race_interwarp_dev-blklock-no-stf_waw` | RACE | yes | CLEAN | — | CLEAN | — |
| `P5-race_interwarp_dev-blklock-no-tf_waw` | RACE | yes | CLEAN | — | RACE | — |

## Sanity: scalar-clock Race set = vector-clock Race set minus the vetoes (hb_proof.tex §5 fact (i))

A veto = a vector-clock RACE on a pair a static certificate (R1/R2 strength or R3 chain) orders: `model_bug`, or `structural` with a chain. Vetoed report keys over all programs: 151.

**Same trace** (the vector-clock dump re-analysed with its engine keys removed, i.e. through the scalar-clock path): 558 programs checked, **1 mismatches**.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P9-crs-cuda` | same trace | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

**Own run** (the scalar-clock mode's separately recorded dump): 558 programs checked, 12 differ. Two recordings are two schedules (and, for the event-stream candidates, two event streams), so these differences are run-to-run, not model differences; the same-trace check above is the model comparison.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 2 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 0 | vetoes=0 |
| `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n` | own run | differs | 1 | 0 | vetoes=0 |
| `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` | own run | differs | 1 | 0 | vetoes=0 |
| `P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | own run | differs | 1 | 0 | vetoes=0 |
| `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-slower_atomic-100n` | own run | differs | 0 | 1 | vetoes=0 |
| `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` | own run | differs | 0 | 1 | vetoes=0 |
| `P4-graph-coloring-racy-small` | own run | differs | 0 | 1 | vetoes=0 |
| `P6-memcpy-global_readwrite_race-racy` | own run | differs | 1 | 1 | vetoes=0 |
| `P9-crs-cuda` | own run | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

Detail files by census_version: 27d637313f2e 1713.

## Coverage

Analysis failures (0): none.

Selected but without a finished detail file (not analysed / still running when the tables were generated) (1): `P9-mr-cuda|scalar-clock`.

No usable kept dump (per program × mode, by reason): unsaved 78, missing 32, partial 2.

Labels not from the current manifest (58 programs, e.g. P2 dropped when PI replaced it): taken from eval/baselines/setup/manifest.evcand.csv.


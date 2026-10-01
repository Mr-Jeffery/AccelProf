## Headline (generated)

- Programs with a vector-clock verdict from a complete kept dump: 554 (scalar-clock: 593).
- Labelled-racy programs reported RACE by vector-clock: 232; of these caught **only** through `latent` (no structural/model_bug report): **9** — `P5-race_interblock_blkfence_raw`, `P5-race_interblock_lock-blkfence_waw`, `P5-race_interblock_lock-no-stf_waw`, `P5-race_interblock_lock-no-tf_waw`, `P5-race_interblock_none-lock_rtraw`, `P5-race_interwarp_blklock-no-stf_waw`, `P5-race_interwarp_blklock-no-tf_waw`, `P5-race_interwarp_dev-blklock-no-stf_waw`, `P5-race_interwarp_dev-blklock-no-tf_waw`.
- `latent` reports (deduped pc pairs): **48** on 16 programs — on labelled-racy 23, on labelled race-free **25** (52.1% of all latent reports; 4 programs), unlabelled 0.
- Labelled race-free programs reported RACE by vector-clock: 20; of these RACE **only** through `latent`: 2 — `P4-rule-110-norace-large`, `P4-rule-110-norace-small`.
- Hand-off fencing of the latent pairs (Definition "Gate" adjacency per observed hand-off RMW; `certified` = the hand-off lies in R3's dominance program order, `reach` = only CFG-reachable):
  - race-free, reach: acquire side ungated — 2
  - race-free, reach: gated hand-off present — 23
  - racy, certified: acquire side ungated — 4
  - racy, certified: both sides ungated — 1
  - racy, certified: gated hand-off present — 1
  - racy, certified: release side ungated — 7
  - racy, reach: both sides ungated — 2
  - racy, reach: gated hand-off present — 8

## Vector-clock TP/FP with and without `latent` (recorded runs; no detector change)

`without latent` = the program's verdict if every `latent` report (and a `benign` report whose underlying class is latent) were ORDERED -- the "ordered in this execution" reading of D8 applied to the unchanged engine (I1/I2/I4 as they are).

| suite | labelled racy | TP | TP without latent | labelled race-free | FP | FP without latent |
|---|---|---|---|---|---|---|
| P1 | 174 | 174 | 174 | 187 | 0 | 0 |
| P2 | 30 | 25 | 25 | 28 | 0 | 0 |
| P3 | 0 | 0 | 0 | 56 | 14 | 14 |
| P4 | 9 | 9 | 9 | 9 | 5 | 3 |
| P5 | 19 | 19 | 10 | 14 | 0 | 0 |
| P6 | 10 | 5 | 5 | 17 | 0 | 0 |
| P9 | 0 | 0 | 0 | 1 | 1 | 1 |
| **all** | 242 | 232 | 223 | 312 | 20 | 18 |

## Census by suite and mode (deduped reports; recorded dumps)

| suite | mode | programs | analysed | RACE programs | structural | model_bug | latent | benign | race (sc) | barrier-ordered | ordered | event_candidate | event_candidate ∧ RACE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 361 | 361 | 174 | 1158 | 0 | 0 | 0 | 0 | 40 | 22 | 236 | 225 |
| P2 | vector-clock | 58 | 58 | 25 | 34 | 0 | 0 | 8 | 0 | 6 | 6 | 0 | 0 |
| P3 | vector-clock | 56 | 56 | 14 | 14 | 0 | 0 | 0 | 0 | 20 | 18 | 5 | 0 |
| P4 | vector-clock | 18 | 18 | 14 | 102 | 0 | 39 | 0 | 0 | 66 | 83 | 36 | 34 |
| P5 | vector-clock | 33 | 33 | 19 | 13 | 0 | 9 | 0 | 0 | 0 | 20 | 11 | 2 |
| P6 | vector-clock | 27 | 27 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 13 | 142 | 0 | 0 | 0 | 2 | 8 | 127 | 127 |
| P1 | scalar-clock | 384 | 384 | 196 | 0 | 0 | 0 | 0 | 1284 | 52 | 68 | 238 | 226 |
| P2 | scalar-clock | 58 | 58 | 25 | 0 | 0 | 0 | 8 | 34 | 6 | 6 | 0 | 0 |
| P3 | scalar-clock | 58 | 58 | 16 | 0 | 0 | 0 | 0 | 16 | 22 | 22 | 6 | 0 |
| P4 | scalar-clock | 28 | 28 | 20 | 0 | 0 | 0 | 0 | 176 | 83 | 212 | 52 | 29 |
| P5 | scalar-clock | 33 | 33 | 18 | 0 | 0 | 0 | 0 | 21 | 0 | 21 | 11 | 2 |
| P6 | scalar-clock | 28 | 28 | 5 | 0 | 0 | 0 | 0 | 5 | 0 | 4 | 0 | 0 |
| P7 | scalar-clock | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 |
| P9 | scalar-clock | 3 | 3 | 1 | 0 | 0 | 0 | 0 | 7 | 2 | 107 | 65 | 2 |

## Latent-only true positives (compact)

| program | pc pair | type | dist | R3 declined | fence status | hand-off(s) |
|---|---|---|---|---|---|---|
| `P5-race_interblock_blkfence_raw` | 0x170↔0xf0 | RAW | grid | missing-hop | both sides ungated | 0x190→0x90 rel− acq− |
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
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0x5f0↔0x720 | global | RAW | block | no | 960 | no-release-fence | 0x600(ATOMG.E.EXCH.STRONG.SM)→0x6d0(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0xec0 | global | RAW | grid | no | 29 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0xa80↔0x1650 | global | WAW | grid | yes | 29 | dominance | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq−; 0x10a0(ATOMG.E.ADD.STRONG.SM)→0xfd0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0xfd0(ATOMG.E.EXCH.STRONG.SM)→0x10a0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1230(ATOMG.E.ADD.STRONG.SM)→0x1160(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1160(ATOMG.E.EXCH.STRONG.SM)→0x1230(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1390(ATOMG.E.ADD.STRONG.SM)→0x12e0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | device_atomic_functions.hpp:162 ; red_kernel.cu:210 |  |
| `P4-reduction-racy-large` | RACE | void reduceSinglePass<512u, true>(int co | 0x12d0↔0x13e0 | global | RAW | block | no | 32 | no-release-fence | 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0x5f0↔0x720 | global | RAW | block | no | 128 | no-release-fence | 0x600(ATOMG.E.EXCH.STRONG.SM)→0x6d0(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0xec0 | global | RAW | grid | no | 3 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0xa10↔0x1640 | global | WAW | grid | yes | 1 | no-release-point | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq−; 0x10a0(ATOMG.E.ADD.STRONG.SM)→0xfd0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0xfd0(ATOMG.E.EXCH.STRONG.SM)→0x10a0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1230(ATOMG.E.ADD.STRONG.SM)→0x1160(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1160(ATOMG.E.EXCH.STRONG.SM)→0x1230(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1390(ATOMG.E.ADD.STRONG.SM)→0x12e0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:207 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0xa80↔0x1650 | global | WAW | grid | yes | 3 | dominance | (reach) 0xa80(ATOMG.E.INC.STRONG.GPU)→0xa80(ATOMG.E.INC.STRONG.GPU) grid rel− acq−; 0x10a0(ATOMG.E.ADD.STRONG.SM)→0xfd0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0xfd0(ATOMG.E.EXCH.STRONG.SM)→0x10a0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1230(ATOMG.E.ADD.STRONG.SM)→0x1160(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1160(ATOMG.E.EXCH.STRONG.SM)→0x1230(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1390(ATOMG.E.ADD.STRONG.SM)→0x12e0(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | device_atomic_functions.hpp:162 ; red_kernel.cu:210 |  |
| `P4-reduction-racy-small` | RACE | void reduceSinglePass<512u, true>(int co | 0x12d0↔0x13e0 | global | RAW | block | no | 32 | no-release-fence | 0x12e0(ATOMG.E.EXCH.STRONG.SM)→0x1390(ATOMG.E.ADD.STRONG.SM) block rel− acq+ | race/RACE | race/RACE | red_kernel.cu:77 ; red_kernel.cu:95 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xd90↔0x1630 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xdf0↔0x16b0 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xe20↔0x1730 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0xed0↔0x1950 | global | RAW | grid | no | 1 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P4-rule-110-racy-large` | RACE | rule110Kernel(int*, int volatile*, int*, | 0x1050↔0x1950 | global | RAW | grid | no | 4095 | no-release-point | (reach) 0x1200(ATOMG.E.ADD.STRONG.SM)→0x1170(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1170(ATOMG.E.EXCH.STRONG.SM)→0x1200(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1120(ATOMG.E.EXCH.STRONG.GPU)→0x12f0(ATOMG.E.ADD.STRONG.GPU) grid rel− acq+ | race/RACE | race/RACE | r110_kernel.cu:109 ; r110_kernel.cu:75 |  |
| `P5-race_interblock_blkfence_raw` | RACE | kmain(unsigned int volatile*) | 0x170↔0xf0 | global | RAW | grid | no | 1 | missing-hop | 0x190(ATOMG.E.EXCH.STRONG.GPU)→0x90(ATOMG.E.EXCH.STRONG.GPU) grid rel− acq− | race/RACE | race/RACE | race_interblock_blkfence_raw.cu:25 ; race_interblock_blkfence_raw.cu:32 |  |
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
| `P4-reduction-norace-large` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0xef0 | global | RAW | grid | no | 29 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-norace-large` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xab0↔0x1690 | global | WAW | grid | yes | 29 | dominance | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq−; 0x10d0(ATOMG.E.ADD.STRONG.SM)→0x1000(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1000(ATOMG.E.EXCH.STRONG.SM)→0x10d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1260(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1260(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x13d0(ATOMG.E.ADD.STRONG.SM)→0x1320(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1320(ATOMG.E.EXCH.STRONG.SM)→0x13d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+ | race/RACE | race/RACE | device_atomic_functions.hpp:162 ; red_kernel.cu:210 |  |
| `P4-reduction-norace-small` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0xef0 | global | RAW | grid | no | 3 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq− | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:200 |  |
| `P4-reduction-norace-small` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xa20↔0x1680 | global | WAW | grid | yes | 1 | no-release-point | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq−; 0x10d0(ATOMG.E.ADD.STRONG.SM)→0x1000(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1000(ATOMG.E.EXCH.STRONG.SM)→0x10d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1260(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1260(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x13d0(ATOMG.E.ADD.STRONG.SM)→0x1320(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1320(ATOMG.E.EXCH.STRONG.SM)→0x13d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+ | race/RACE | race/RACE | red_kernel.cu:147 ; red_kernel.cu:207 |  |
| `P4-reduction-norace-small` | CLEAN | void reduceSinglePass<512u, true>(int co | 0xab0↔0x1690 | global | WAW | grid | yes | 3 | dominance | (reach) 0xab0(ATOMG.E.INC.STRONG.GPU)→0xab0(ATOMG.E.INC.STRONG.GPU) grid rel+ acq−; 0x10d0(ATOMG.E.ADD.STRONG.SM)→0x1000(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1000(ATOMG.E.EXCH.STRONG.SM)→0x10d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x1260(ATOMG.E.ADD.STRONG.SM)→0x1190(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1190(ATOMG.E.EXCH.STRONG.SM)→0x1260(ATOMG.E.ADD.STRONG.SM) block rel+ acq+; 0x13d0(ATOMG.E.ADD.STRONG.SM)→0x1320(ATOMG.E.EXCH.STRONG.SM) block rel− acq−; 0x1320(ATOMG.E.EXCH.STRONG.SM)→0x13d0(ATOMG.E.ADD.STRONG.SM) block rel+ acq+ | race/RACE | race/RACE | device_atomic_functions.hpp:162 ; red_kernel.cu:210 |  |
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

R3 decline reasons, race-free side: no-release-point 23, dominance 2; racy side: no-release-point 8, no-release-fence 7, cs-unfenced 4, dominance 2, missing-hop 1, past-release 1.

## Other tools on the programs with latent reports (merged baselines CSVs)

| program | label | latent-only? | racecheck | hirace | iguard | supercollider |
|---|---|---|---|---|---|---|
| `P4-reduction-norace-large` | CLEAN | no | CLEAN | — | RACE | — |
| `P4-reduction-norace-small` | CLEAN | no | CLEAN | — | RACE | — |
| `P4-reduction-racy-large` | RACE | no | CLEAN | — | RACE | — |
| `P4-reduction-racy-small` | RACE | no | CLEAN | — | RACE | — |
| `P4-rule-110-norace-large` | CLEAN | no | CLEAN | — | CLEAN | — |
| `P4-rule-110-norace-small` | CLEAN | no | CLEAN | — | CLEAN | — |
| `P4-rule-110-racy-large` | RACE | no | CLEAN | — | RACE | — |
| `P5-race_interblock_blkfence_raw` | RACE | yes | CLEAN | — | RACE | — |
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

**Same trace** (the vector-clock dump re-analysed with its engine keys removed, i.e. through the scalar-clock path): 554 programs checked, **3 mismatches**.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P4-matrix-multiplication-norace-small` | same trace | differs | 0 | 2 | barrier-pass cutoff on 1 kernel(s); vetoes=0 |
| `P4-matrix-multiplication-racy-small` | same trace | differs | 0 | 2 | barrier-pass cutoff on 1 kernel(s); vetoes=0 |
| `P9-crs-cuda` | same trace | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

**Own run** (the scalar-clock mode's separately recorded dump): 554 programs checked, 9 differ. Two recordings are two schedules (and, for the event-stream candidates, two event streams), so these differences are run-to-run, not model differences; the same-trace check above is the model comparison.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 2 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 0 | vetoes=0 |
| `P4-graph-coloring-racy-small` | own run | differs | 0 | 1 | vetoes=0 |
| `P4-matrix-multiplication-norace-small` | own run | differs | 0 | 2 | barrier-pass cutoff on 1 kernel(s); vetoes=0 |
| `P4-matrix-multiplication-racy-small` | own run | differs | 0 | 2 | barrier-pass cutoff on 1 kernel(s); vetoes=0 |
| `P6-memcpy-global_readwrite_race-racy` | own run | differs | 1 | 1 | vetoes=0 |
| `P9-crs-cuda` | own run | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

Detail files by census_version: bb72d09310b5 1701.

## Coverage

Analysis failures (0): none.

Selected but without a finished detail file (not analysed / still running when the tables were generated) (1): `P9-mr-cuda|scalar-clock`.

No usable kept dump (per program × mode, by reason): unsaved 40.

Labels not from the current manifest (58 programs, e.g. P2 dropped when PI replaced it): taken from eval/baselines/setup/manifest.evcand.csv.


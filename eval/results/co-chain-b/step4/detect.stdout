Programs with a confirm JSON: C6 4709, S1 4709, S2 4709
Programs whose CSV report_ids hold fewer pairs than reports_dedup (pair sets cut by the CSV): scalar-clock 0, C1 0, C6 0, S1 0, S2 0
Check C6: programs Race with a confirm JSON 2927; race-class raw pair set differs from the CSV report_ids in 0.
Check S1: programs Race with a confirm JSON 2928; race-class raw pair set differs from the CSV report_ids in 0.
Check S2: programs Race with a confirm JSON 2931; race-class raw pair set differs from the CSV report_ids in 0.

## False reports: the split by how the verdict step found them

Definitions (record = one entry of the confirm JSON's `raw`; pair = deduped (space, pc, pc)):
- **derived**: `chain_src` = `chain`: no recorded edge joins the pair, only a chain of reads (the closure's own pair).
- **rescued**: `chain_src` = `chain_rescue`: an edge whose own distance is thread-local (or narrower than the chain's) judged at the chain's widest bound.
- **async**: `async` = true: the cp.async cross-agent rule (`--co-async`): an edge with a same-thread instance whose earlier access is a `LDGSTS` copy and whose later access is not, unless an unguarded `DEPBAR.LE SB0, 0x0` lies on every CFG path between them; judged at no narrower than warp, with no R1/R3 credit.
- **atomic-chain-off**: `atomic_chain_off` = true: the region-dominance certificate (R3, the PC-level atomic hand-off chain) that `--co-r3 cfg` grants was withheld (S1 strict: R3 must also find a chain with scalar-clock's CFG-decidable declines; S2 off: no R3 certificate), so the pair is reported where cfg orders it.
- **other**: none of the four: an ordinary edge or event record.
Precedence for a record: atomic-chain-off, async, derived, rescued, other. A pair has the least special class among its records (a pair that an ordinary record also reports is `other`). C6's confirm JSONs predate the async / atomic_chain_off tags (they count as false), so for C6 only derived / rescued / other occur.


### C6: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in C6 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 46 | 0 | 0 | 1148 | 374 | 328 | 46 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8680 | 1764 | 204 | 0 | 0 | 6712 | 1968 | 1764 | 204 | 0 | 0 | 0 | 843 | 149 | 14 | 0 | 0 | 680 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5193 | 2051 | 181 | 0 | 0 | 2961 | 2232 | 2051 | 181 | 0 | 0 | 0 | 404 | 279 | 102 | 0 | 0 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 111 | 25 | 4 | 0 | 0 | 82 | 29 | 25 | 4 | 0 | 0 | 0 | 47 | 25 | 4 | 0 | 0 | 18 |
| ScoR apps (P4) | race-free | 8 | 37 | 3 | 4 | 0 | 0 | 30 | 7 | 3 | 4 | 0 | 0 | 0 | 37 | 3 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 6 | 93 | 79 | 0 | 0 | 0 | 14 | 79 | 79 | 0 | 0 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 72 | 5 | 1 | 0 | 0 | 66 | 6 | 5 | 1 | 0 | 0 | 0 | 7 | 5 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 118 | 67 | 6 | 0 | 0 | 45 | 73 | 67 | 6 | 0 | 0 | 0 | 73 | 63 | 0 | 0 | 0 | 10 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1963 | 10527 | 2263 | 260 | 0 | 0 | 8004 | 2523 | 2263 | 260 | 0 | 0 | 0 | 1271 | 469 | 34 | 0 | 0 | 768 |
| **all** | **race-free** | 251 | 343 | 25 | 12 | 0 | 0 | 306 | 37 | 25 | 12 | 0 | 0 | 0 | 318 | 25 | 12 | 0 | 0 | 281 |
| **all** | **unlabelled** | 713 | 5265 | 2056 | 182 | 0 | 0 | 3027 | 2238 | 2056 | 182 | 0 | 0 | 0 | 411 | 284 | 102 | 0 | 0 | 25 |
| **all** | **ALL** | 2927 | 16135 | 4344 | 454 | 0 | 0 | 11337 | 4798 | 4344 | 454 | 0 | 0 | 0 | 2000 | 778 | 148 | 0 | 0 | 1074 |

Race-free-labelled programs, C6: all reports: 343 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 306); not in C1: 37 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 0); not in scalar-clock: 318 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 281)

Record-level tag counts for C6 (not exclusive; pairs with the tag on their chosen record): pairs 16135, chain_src=chain 4344, chain_src=chain_rescue 454, async 0, atomic_chain_off 0.
Strong-conflict-class pairs (raw_sc) of the Race programs, C6: 197 (derived 81, rescued 6, async 0, atomic_chain_off 0, other 110)

### S1: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in S1 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in C6: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 97 | 0 | 0 | 1097 | 374 | 328 | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8723 | 1799 | 331 | 0 | 0 | 6593 | 2011 | 1799 | 212 | 0 | 0 | 0 | 43 | 35 | 8 | 0 | 0 | 0 | 864 | 162 | 25 | 0 | 0 | 677 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5202 | 2060 | 253 | 0 | 0 | 2889 | 2241 | 2060 | 181 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 405 | 280 | 102 | 0 | 0 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 131 | 29 | 4 | 0 | 16 | 82 | 49 | 29 | 4 | 0 | 16 | 0 | 20 | 4 | 0 | 0 | 16 | 0 | 67 | 29 | 4 | 0 | 16 | 18 |
| ScoR apps (P4) | race-free | 8 | 41 | 7 | 4 | 0 | 0 | 30 | 11 | 7 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 41 | 7 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 7 | 94 | 79 | 0 | 1 | 0 | 14 | 80 | 79 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 73 | 6 | 1 | 0 | 0 | 66 | 7 | 6 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 6 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 127 | 76 | 10 | 0 | 0 | 41 | 82 | 76 | 6 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 78 | 68 | 4 | 0 | 0 | 6 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1964 | 10600 | 2311 | 442 | 1 | 16 | 7830 | 2596 | 2311 | 268 | 1 | 16 | 0 | 73 | 48 | 8 | 1 | 16 | 0 | 1317 | 491 | 49 | 0 | 16 | 761 |
| **all** | **race-free** | 251 | 347 | 29 | 12 | 0 | 0 | 306 | 41 | 29 | 12 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 322 | 29 | 12 | 0 | 0 | 281 |
| **all** | **unlabelled** | 713 | 5275 | 2066 | 254 | 0 | 0 | 2955 | 2248 | 2066 | 182 | 0 | 0 | 0 | 10 | 10 | 0 | 0 | 0 | 0 | 413 | 286 | 102 | 0 | 0 | 25 |
| **all** | **ALL** | 2928 | 16222 | 4406 | 708 | 1 | 16 | 11091 | 4885 | 4406 | 462 | 1 | 16 | 0 | 87 | 62 | 8 | 1 | 16 | 0 | 2052 | 806 | 163 | 0 | 16 | 1067 |

Race-free-labelled programs, S1: all reports: 347 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 306); not in C1: 41 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 0); not in C6: 4 (derived 4, rescued 0, async 0, atomic_chain_off 0, other 0); not in scalar-clock: 322 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 281)

Record-level tag counts for S1 (not exclusive; pairs with the tag on their chosen record): pairs 16222, chain_src=chain 4406, chain_src=chain_rescue 708, async 1, atomic_chain_off 16.
Strong-conflict-class pairs (raw_sc) of the Race programs, S1: 305 (derived 79, rescued 10, async 0, atomic_chain_off 108, other 108)

### S2: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in S2 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in C6: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 97 | 0 | 0 | 1097 | 374 | 328 | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8723 | 1799 | 331 | 0 | 0 | 6593 | 2011 | 1799 | 212 | 0 | 0 | 0 | 43 | 35 | 8 | 0 | 0 | 0 | 864 | 162 | 25 | 0 | 0 | 677 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5203 | 2060 | 253 | 0 | 1 | 2889 | 2242 | 2060 | 181 | 0 | 1 | 0 | 10 | 9 | 0 | 0 | 1 | 0 | 406 | 280 | 102 | 0 | 1 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 131 | 29 | 4 | 0 | 16 | 82 | 49 | 29 | 4 | 0 | 16 | 0 | 20 | 4 | 0 | 0 | 16 | 0 | 67 | 29 | 4 | 0 | 16 | 18 |
| ScoR apps (P4) | race-free | 8 | 41 | 7 | 4 | 0 | 0 | 30 | 11 | 7 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 41 | 7 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 4 | 5 | 0 | 0 | 0 | 2 | 3 | 2 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| ScoR litmus (P5) | race-free | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| cuHadron (P6) | racy | 7 | 94 | 79 | 0 | 1 | 0 | 14 | 80 | 79 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 73 | 6 | 1 | 0 | 0 | 66 | 7 | 6 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 6 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 127 | 76 | 10 | 0 | 0 | 41 | 82 | 76 | 6 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 78 | 68 | 4 | 0 | 0 | 6 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1966 | 10602 | 2311 | 442 | 1 | 18 | 7830 | 2598 | 2311 | 268 | 1 | 18 | 0 | 75 | 48 | 8 | 1 | 18 | 0 | 1318 | 491 | 49 | 0 | 17 | 761 |
| **all** | **race-free** | 252 | 348 | 29 | 12 | 0 | 1 | 306 | 42 | 29 | 12 | 0 | 1 | 0 | 5 | 4 | 0 | 0 | 1 | 0 | 323 | 29 | 12 | 0 | 1 | 281 |
| **all** | **unlabelled** | 713 | 5276 | 2066 | 254 | 0 | 1 | 2955 | 2249 | 2066 | 182 | 0 | 1 | 0 | 11 | 10 | 0 | 0 | 1 | 0 | 414 | 286 | 102 | 0 | 1 | 25 |
| **all** | **ALL** | 2931 | 16226 | 4406 | 708 | 1 | 20 | 11091 | 4889 | 4406 | 462 | 1 | 20 | 0 | 91 | 62 | 8 | 1 | 20 | 0 | 2055 | 806 | 163 | 0 | 19 | 1067 |

Race-free-labelled programs, S2: all reports: 348 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 306); not in C1: 42 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 0); not in C6: 5 (derived 4, rescued 0, async 0, atomic_chain_off 1, other 0); not in scalar-clock: 323 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 281)

Record-level tag counts for S2 (not exclusive; pairs with the tag on their chosen record): pairs 16226, chain_src=chain 4407, chain_src=chain_rescue 708, async 1, atomic_chain_off 20.
Strong-conflict-class pairs (raw_sc) of the Race programs, S2: 326 (derived 80, rescued 10, async 0, atomic_chain_off 128, other 108)

## What moved against C6

### Verdict changes against C6 (races alone), with the tags of the records that cause them

| setting | suite | program | label | C6 | S | reports C6 -> S | pairs of S not in C6 (class) | pairs of C6 not in S |
|---|---|---|---|---|---|---|---|---|
| S1 | P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | CLEAN | RACE | 0 -> 1 | shared:0x70-0x90 (async) |  |
| S2 | P5 | `P5-canary` | racy | CLEAN | RACE | 0 -> 1 | global:0x160-0x1f0 (atomic_chain_off) |  |
| S2 | P5 | `P5-norace_interwarp-block_fence-atom_hrd-indirect` | race-free | CLEAN | RACE | 0 -> 1 | shared:0x2d0-0x3f0 (atomic_chain_off) |  |
| S2 | P5 | `P5-race_interblock_none-lock_rtraw` | racy | CLEAN | RACE | 0 -> 1 | global:0x170-0x2f0 (atomic_chain_off) |  |
| S2 | P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | CLEAN | RACE | 0 -> 1 | shared:0x70-0x90 (async) |  |

Programs whose verdict changed against C6, per suite: S1: P6 1 (total 1); S2: P5 3, P6 1 (total 4)

### Pair-level moves against C6 (RACE-class pc pairs, programs Race in either)

Per suite: pairs only in S (gained), by the class of the gained pair in S; pairs only in C6 (lost), by C6's class (derived / rescued / other); programs with any move; programs whose verdict is the same in both but whose pair set moved.


**S1 against C6**

| suite | programs compared | programs with a pair move | of them, same verdict | pairs in both | gained | gained: derived | rescued | async | atomic-chain-off | other | lost | lost: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 | 0 | 1522 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 4130 | 40 | 40 | 14113 | 52 | 44 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 0 | 0 | 44 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 6 | 6 | 148 | 24 | 8 | 0 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 33 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 0 | 102 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 1 | 1 | 72 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 10 | 1 | 1 | 131 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 49 | 48 | 16135 | 87 | 62 | 8 | 1 | 16 | 0 | 0 | 0 | 0 | 0 |

**S2 against C6**

| suite | programs compared | programs with a pair move | of them, same verdict | pairs in both | gained | gained: derived | rescued | async | atomic-chain-off | other | lost | lost: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 | 0 | 1522 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 4130 | 41 | 41 | 14113 | 53 | 44 | 8 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 0 | 0 | 44 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 6 | 6 | 148 | 24 | 8 | 0 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 33 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 0 | 102 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 1 | 1 | 72 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 10 | 1 | 1 | 131 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 53 | 49 | 16135 | 91 | 62 | 8 | 1 | 20 | 0 | 0 | 0 | 0 | 0 |

### Derived and rescued counts, narrowest bound (C6) against widest bound (S1, S2)

Programs with chain_derived > 0 / chain_rescued > 0 and the sums of the per-program counts (notes `chain_derived`, `chain_rescued`, one row per program: rep 1), per suite. A derived pair is a pair no edge joins; a rescued one is an edge judged at its chain's bound (C6: edges whose own distance was thread-local; C6b: every edge whose chain bound is wider than its own distance).

| suite | programs | C6 derived>0 | S1 | S2 | C6 rescued>0 | S1 | S2 | C6 sum derived | S1 | S2 | C6 sum rescued | S1 | S2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 172 | 172 | 172 | 138 | 173 | 173 | 6656 | 6671 | 6671 | 877 | 2292 | 2292 |
| Indigo 1.3 (PI) | 4130 | 861 | 861 | 861 | 359 | 472 | 472 | 5532 | 5604 | 5604 | 550 | 818 | 818 |
| ECL (P3) | 60 | 20 | 20 | 20 | 15 | 22 | 22 | 148 | 148 | 148 | 147 | 213 | 213 |
| ScoR apps (P4) | 28 | 24 | 24 | 24 | 10 | 10 | 10 | 5576 | 5590 | 5590 | 244 | 316 | 316 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 1 | 1 | 2 | 2 | 2 | 159 | 159 | 159 | 2 | 2 | 2 |
| HeCBench other 14 (P7) | 14 | 7 | 7 | 7 | 5 | 5 | 5 | 56089 | 56098 | 56098 | 2080 | 9383 | 9383 |
| HeCBench SC 10 (P9) | 10 | 5 | 5 | 5 | 3 | 3 | 3 | 58358 | 68191 | 68191 | 7893 | 12173 | 12173 |
| **all** | 4709 | 1093 | 1093 | 1093 | 532 | 687 | 687 | 132522 | 142465 | 142465 | 11793 | 25197 | 25197 |

Programs by change of the per-program count against C6: S1 derived same 4632; S1 derived up 77; S1 rescued same 4393; S1 rescued up 316; S2 derived same 4632; S2 derived up 77; S2 rescued same 4393; S2 rescued up 316

### lock_rtraw and matrix-multiplication-norace in every setting

Cells: races-alone verdict; reports (Race-class pairs); `classes=` of the notes; the RACE-class and strong-class pairs of the confirm JSON with their tags (src = chain_src; A = async, O = atomic_chain_off).

| program | label | mode | verdict | reports | classes | RACE-class pairs (src, tags) | strong-class pairs (src, tags) |
|---|---|---|---|---|---|---|---|
| `P4-matrix-multiplication-norace-large` | race-free | scalar-clock | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | C1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | C6 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | S1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | S2 | CLEAN | 0 | sc:6 |  | global:0x590-0x5a0 (RAW, edge, O), global:0x5a0-0x5a0 (WAW, chain, O), global:0x960-0x980 (RAW, edge, O), global:0x980-0x980 (WAW, chain, O), global:0xb80-0xbb0 (RAW, edge, O), global:0xbb0-0xbb0 (WAW, chain, O) |
| `P4-matrix-multiplication-norace-small` | race-free | scalar-clock | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | C1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | C6 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | S1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | S2 | CLEAN | 0 | sc:4 |  | global:0x590-0x5a0 (RAW, edge, O), global:0x5a0-0x5a0 (WAW, chain, O), global:0x960-0x980 (RAW, edge, O), global:0x980-0x980 (WAW, chain, O) |
| `P5-race_interblock_none-lock_rtraw` | racy | scalar-clock | RACE | 1 | race:1,sc:1 | global:0x170-0x2f0 |  |
| `P5-race_interblock_none-lock_rtraw` | racy | C1 | CLEAN | 0 |  |  |  |
| `P5-race_interblock_none-lock_rtraw` | racy | C6 | CLEAN | 0 | sc:1 |  | global:0x140-0x340 (WAR, chain) |
| `P5-race_interblock_none-lock_rtraw` | racy | S1 | CLEAN | 0 | sc:1 |  | global:0x140-0x340 (WAR, chain) |
| `P5-race_interblock_none-lock_rtraw` | racy | S2 | RACE | 1 | race:1,sc:1 | global:0x170-0x2f0 (WAW, edge, O) | global:0x140-0x340 (WAR, chain) |

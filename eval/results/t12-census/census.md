## Headline (generated)

- Programs with a vector-clock verdict from a complete kept dump: 554 (scalar-clock: 593).
- Labelled-racy programs reported RACE by vector-clock: 216; of these caught **only** through `latent` (no structural/model_bug report): **0** — none.
- `latent` reports (deduped pc pairs): **0** on 0 programs — on labelled-racy 0, on labelled race-free **0** (0.0% of all latent reports; 0 programs), unlabelled 0.
- Labelled race-free programs reported RACE by vector-clock: 18; of these RACE **only** through `latent`: 0.
- Hand-off fencing of the latent pairs (Definition "Gate" adjacency per observed hand-off RMW; `certified` = the hand-off lies in R3's dominance program order, `reach` = only CFG-reachable):

## Vector-clock TP/FP with and without `latent` (recorded runs; no detector change)

`without latent` = the program's verdict if every `latent` report (and a `benign` report whose underlying class is latent) were ORDERED -- the "ordered in this execution" reading of D8 applied to the unchanged engine (I1/I2/I4 as they are).

| suite | labelled racy | TP | TP without latent | labelled race-free | FP | FP without latent |
|---|---|---|---|---|---|---|
| P1 | 174 | 174 | 174 | 187 | 0 | 0 |
| P2 | 30 | 25 | 25 | 28 | 0 | 0 |
| P3 | 0 | 0 | 0 | 56 | 14 | 14 |
| P4 | 9 | 9 | 9 | 9 | 2 | 2 |
| P5 | 19 | 3 | 3 | 14 | 1 | 1 |
| P6 | 10 | 5 | 5 | 17 | 0 | 0 |
| P9 | 0 | 0 | 0 | 1 | 1 | 1 |
| **all** | 242 | 216 | 216 | 312 | 18 | 18 |

## Census by suite and mode (deduped reports; recorded dumps)

| suite | mode | programs | analysed | RACE programs | structural | model_bug | latent | benign | race (sc) | barrier-ordered | ordered | event_candidate | event_candidate ∧ RACE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 361 | 361 | 174 | 1158 | 0 | 0 | 0 | 0 | 40 | 22 | 236 | 225 |
| P2 | vector-clock | 58 | 58 | 25 | 34 | 0 | 0 | 8 | 0 | 6 | 6 | 0 | 0 |
| P3 | vector-clock | 56 | 56 | 14 | 14 | 0 | 0 | 0 | 0 | 20 | 18 | 5 | 0 |
| P4 | vector-clock | 18 | 18 | 11 | 41 | 0 | 0 | 0 | 0 | 66 | 101 | 32 | 6 |
| P5 | vector-clock | 33 | 33 | 4 | 8 | 0 | 0 | 0 | 0 | 0 | 4 | 11 | 3 |
| P6 | vector-clock | 27 | 27 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 13 | 142 | 0 | 0 | 0 | 2 | 8 | 127 | 127 |
| P1 | scalar-clock | 384 | 384 | 196 | 0 | 0 | 0 | 0 | 1284 | 52 | 68 | 238 | 226 |
| P2 | scalar-clock | 58 | 58 | 25 | 0 | 0 | 0 | 8 | 34 | 6 | 6 | 0 | 0 |
| P3 | scalar-clock | 58 | 58 | 16 | 0 | 0 | 0 | 0 | 16 | 22 | 38 | 6 | 0 |
| P4 | scalar-clock | 28 | 28 | 16 | 0 | 0 | 0 | 0 | 76 | 83 | 223 | 52 | 7 |
| P5 | scalar-clock | 33 | 33 | 2 | 0 | 0 | 0 | 0 | 4 | 0 | 21 | 11 | 1 |
| P6 | scalar-clock | 28 | 28 | 5 | 0 | 0 | 0 | 0 | 5 | 0 | 4 | 0 | 0 |
| P7 | scalar-clock | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 |
| P9 | scalar-clock | 3 | 3 | 1 | 0 | 0 | 0 | 0 | 7 | 2 | 107 | 65 | 2 |

## Latent-only true positives (compact)

| program | pc pair | type | dist | R3 declined | fence status | hand-off(s) |
|---|---|---|---|---|---|---|

## Latent pairs on labelled-racy programs

none

## Latent pairs on labelled race-free programs (the tier's cost)

none

R3 decline reasons, race-free side: none; racy side: none.

## Other tools on the programs with latent reports (merged baselines CSVs)

| program | label | latent-only? | racecheck | hirace | iguard | supercollider |
|---|---|---|---|---|---|---|

## Sanity: scalar-clock Race set = vector-clock Race set minus the vetoes (hb_proof.tex §5 fact (i))

A veto = a vector-clock RACE on a pair a static certificate (R1/R2 strength or R3 chain) orders: `model_bug`, or `structural` with a chain. Vetoed report keys over all programs: 152.

**Same trace** (the vector-clock dump re-analysed with its engine keys removed, i.e. through the scalar-clock path): 554 programs checked, **1 mismatches**.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P9-crs-cuda` | same trace | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

**Own run** (the scalar-clock mode's separately recorded dump): 554 programs checked, 7 differ. Two recordings are two schedules (and, for the event-stream candidates, two event streams), so these differences are run-to-run, not model differences; the same-trace check above is the model comparison.

| program | comparison | result | sc-only | vc-only | cause / note |
|---|---|---|---|---|---|
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 2 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-default-1296n` | own run | differs | 1 | 1 | vetoes=0 |
| `P1-BFS_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-1296n` | own run | differs | 1 | 0 | vetoes=0 |
| `P4-graph-coloring-racy-small` | own run | differs | 0 | 1 | vetoes=0 |
| `P6-memcpy-global_readwrite_race-racy` | own run | differs | 1 | 1 | vetoes=0 |
| `P9-crs-cuda` | own run | differs | 0 | 6 | barrier-pass cutoff on 26 kernel(s); vetoes=142 |

Detail files by census_version: bb72d09310b5 1701.

## Coverage

Analysis failures (0): none.

Selected but without a finished detail file (not analysed / still running when the tables were generated) (1): `P9-mr-cuda|scalar-clock`.

No usable kept dump (per program × mode, by reason): unsaved 40.

Labels not from the current manifest (58 programs, e.g. P2 dropped when PI replaced it): taken from eval/baselines/setup/manifest.evcand.csv.


## Item 9: pairs collector-only mode reports that scalar-clock mode does not (orders), by control-flow shape, next to X5's derived 1,021

Programs with a verdict in both runs: 4707. Pairs collector-only reports that scalar-clock does not: **1074** in 926 programs; reported by both: 10263. (Pairs scalar-clock reports that collector-only does not: 7875, by suite {'P1': 205, 'P4': 13, 'P5': 2, 'P6': 72, 'P7': 1, 'P9': 14, 'PI': 7568}; not part of the brief's comparison, listed in `item9_sc_only_by_suite`.)

**Collector-only pairs the scalar-clock run does not report** (shapes of the existing table, same order; last column = pairs that are not among X5's 1,021, so no shape is recorded for them):

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other | not among the 1,021 |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 32 | 59 | 4 | 0 | 0 | 0 | 48 | 7 |
| Indigo 1.3 | 867 | 927 | 560 | 140 | 140 | 0 | 0 | 87 |
| ECL graph codes | 12 | 20 | 4 | 0 | 0 | 0 | 16 | 0 |
| ScoR applications | 11 | 48 | 23 | 24 | 0 | 0 | 0 | 1 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| HeCBench, other applications | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| **All** | 926 | 1074 | 593 | 164 | 140 | 17 | 64 | 96 |

**X5's derived 1,021 pairs** (barrier clock orders them, no certificate covers them; separate X1 recordings, the same in both modes):

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other |
|---|---|---|---|---|---|---|---|
| Indigo3 | 32 | 56 | 8 | 0 | 0 | 0 | 48 |
| Indigo 1.3 | 840 | 840 | 560 | 140 | 140 | 0 | 0 |
| ECL graph codes | 12 | 22 | 6 | 0 | 0 | 0 | 16 |
| ScoR applications | 10 | 83 | 23 | 60 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| HeCBench, other applications | 1 | 2 | 2 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 2 | 17 | 0 | 0 | 0 | 17 | 0 |
| **All** | 898 | 1021 | 599 | 200 | 140 | 17 | 65 |

**Pairs in one set and not the other**, by reason (every pair: `item9_pair_differences.csv`):

| set | reason | pairs |
|---|---|---|
| CO reports, not among the 1,021 | other | 2 |
| CO reports, not among the 1,021 | schedule-dependent edge | 94 |
| among the 1,021, not reported by CO | other | 39 |
| among the 1,021, reported by both | reported by scalar-clock too (X5 | 4 |

By suite:

| suite | set | reason | pairs |
|---|---|---|---|
| P1 | CO reports, not among the 1,021 | schedule-dependent edge: the scalar-clock recording has no edge between the two pcs | 7 |
| P1 | among the 1,021, reported by both | reported by scalar-clock too (X5: barrier-ordered in one launch, another class in another launch) | 4 |
| P3 | among the 1,021, not reported by CO | other: C1's recording has the edge and collector-only does not report the pair | 2 |
| P4 | CO reports, not among the 1,021 | other: both recordings have the edge; scalar-clock does not report the pair and X5 does not list it as barrier-ordered | 1 |
| P4 | among the 1,021, not reported by CO | other: C1's recording has the edge and collector-only does not report the pair | 36 |
| P6 | CO reports, not among the 1,021 | other: both recordings have the edge; scalar-clock does not report the pair and X5 does not list it as barrier-ordered | 1 |
| P6 | among the 1,021, not reported by CO | other: C1's recording has the edge and collector-only does not report the pair | 1 |
| PI | CO reports, not among the 1,021 | schedule-dependent edge: the scalar-clock recording has no edge between the two pcs | 87 |

Pairs that fit none of the three reasons: **41** (each is a finding):
  - P4 `P4-graph-coloring-racy-small` shared 0x500-0x650 [CO reports, not among the 1,021]: other: both recordings have the edge; scalar-clock does not report the pair and X5 does not list it as barrier-ordered
  - P6 `P6-memcpy-global_readwrite_race-racy` shared 0xf0-0x190 [CO reports, not among the 1,021]: other: both recordings have the edge; scalar-clock does not report the pair and X5 does not list it as barrier-ordered
  - P3 `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` global 0xf0-0x11f0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P3 `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` global 0xf0-0xb40 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x260-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x400-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x5a0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x730-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x7d0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x840-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x8b0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x910-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-large` global 0x960-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x260-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x400-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x5a0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x730-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x7d0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x840-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x8b0-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x910-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-norace-small` global 0x960-0xf20 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x260-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x400-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x5a0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x720-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x7c0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x830-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x8a0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x900-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-large` global 0x950-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x260-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x400-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x5a0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x720-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x7c0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x830-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x8a0-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x900-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P4 `P4-reduction-racy-small` global 0x950-0xef0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair
  - P6 `P6-memcpy-shared_writewrite_race-racy` shared 0x70-0xb0 [among the 1,021, not reported by CO]: other: C1's recording has the edge and collector-only does not report the pair

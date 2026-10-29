## Item 9: pairs collector-only mode reports that scalar-clock mode orders, by control-flow shape, next to X5's derived 1,021

Programs analysed in both recordings: 4707 of 4725; not analysed: {'no recording: SC': 18}. Reported by both modes: 10531 pairs. Reported by scalar-clock only: 7950 pairs (by suite {'P1': 212, 'P3': 4, 'P4': 76, 'P5': 3, 'P6': 72, 'P7': 1, 'P9': 14, 'PI': 7568}; not part of the comparison).

Collector-only reports, scalar-clock does not, and scalar-clock's record of the pair is: 
ORDERED by the barrier clock (1016 pairs, S1); SC has no record of the pair: 96; SC orders it by a certificate (hb_class none): 26. Total CO-only reports: 1138.

**S1: collector-only reports that scalar-clock orders (barrier-only clock, no certificate)**; the last column = pairs in S1 that are not among X5's pairs (no shape recorded):

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other | not among X5's |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 28 | 52 | 4 | 0 | 0 | 0 | 48 | 0 |
| Indigo 1.3 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| ECL graph codes | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| ScoR applications | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, other applications | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| **All** | 893 | 1016 | 595 | 200 | 140 | 17 | 64 | 0 |

**S2: X5's derived 1,021 pairs** (tab:eval-shapes; separate X1 recordings, same pairs in both modes):

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

S1 and S2 share 1016 pairs; 0 pairs are in S1 only and 5 in S2 only.

**Pairs in one set and not the other**, by reason (every pair, with its evidence: `item9_pair_differences.csv`):

| set | reason | pairs |
|---|---|---|
| in X5, not in S1 | scalar-clock reports it too | 4 |
| in X5, not in S1 | schedule-dependent edge | 1 |

By suite:

| suite | set | reason | pairs |
|---|---|---|---|
| P1 | in X5, not in S1 | scalar-clock reports it too | 4 |
| P6 | in X5, not in S1 | schedule-dependent edge | 1 |

Pairs that fit none of the three reasons (schedule-dependent edge, candidate mechanism off, scalar-clock reports it too): **0**.

**Collector-only reports outside S1** (122 pairs: scalar-clock does not report them, and does not order them by the barrier clock either; `item9_CO_only_outside_S1.csv`):

| suite | scalar-clock's record of the pair | edge in X1b's scalar-clock recording | pairs |
|---|---|---|---|
| P1 | no record | False | 7 |
| P3 | ORDERED:None | True | 16 |
| P4 | ORDERED:None | True | 10 |
| P4 | no record | True | 1 |
| P6 | no record | True | 1 |
| PI | no record | False | 87 |

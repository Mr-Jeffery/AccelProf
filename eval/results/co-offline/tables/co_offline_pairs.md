## Pair level: pairs CO-R reports and scalar-clock orders

Scalar-clock recordings analysed with the rule on and off: 4707 of 4725 programs; not analysed: {'no scalar-clock recording': 18}.

CO-R reports, scalar-clock does not: **1016 pairs** in 893 programs. Their scalar-clock record is ORDERED by the barrier clock in every launch: yes, all of them.

(a) pairs with a cuVein edge: **1016**; (b) extended edges and rescued edges: **0** (candidate with no edge: 0, rescued edge: 0).

**All pairs CO-R reports that scalar-clock orders, by control-flow shape (X5's bins, same order as tab:eval-shapes)**

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

**(a) pairs with a cuVein edge**

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

**(b) extended and rescued edges**

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other | not among X5's |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL graph codes | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR applications | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, other applications | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **All** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**(a) against C3's S1 (1016 pairs)**: (a) has 1016 pairs; common 1016; in (a) only 0; in S1 only 0.

| set | reason | pairs |
|---|---|---|

Every pair of the two lists, with its reason: `pairs_a_vs_S1.csv`.

## CO-R against the collector-only run of C1 (separate recordings)

reported pairs of CO-R (scalar-clock recording, rule off) against reported pairs of C1 (collector-only recording). Programs analysed in both: 
4707 of 4725.

| suite | pairs in both | CO-R only: extended edge | CO-R only: rescue | CO-R only: other | C1 only: RMW points | C1 only: other | programs with a CO-R-only pair | programs with a C1-only pair |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 1266 | 181 | 30 | 1 | 0 | 7 | 58 | 4 |
| Indigo 1.3 | 9810 | 6889 | 248 | 431 | 0 | 87 | 866 | 32 |
| ECL graph codes | 102 | 4 | 0 | 0 | 16 | 0 | 4 | 4 |
| ScoR applications | 210 | 45 | 10 | 21 | 10 | 1 | 14 | 3 |
| ScoR litmus kernels | 19 | 2 | 0 | 1 | 0 | 0 | 2 | 0 |
| cuHadron | 22 | 68 | 3 | 1 | 0 | 1 | 4 | 1 |
| HeCBench, other applications | 66 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| HeCBench, SuperCollider's 10 | 52 | 8 | 6 | 0 | 0 | 0 | 1 | 0 |
| **All** | 11547 | 7197 | 298 | 455 | 26 | 96 | 950 | 44 |

Pairs in "other": **551** (each is a finding; `pairs_cor_vs_c1.csv`, kind column).
  - C1 only: CO-R has no record of the pair — 96
  - CO-R only: C1 — 20
  - CO-R only: C1 has no record of the pair — 435

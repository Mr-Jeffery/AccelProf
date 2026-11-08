### 4.1 Per-suite tables (step 3's own, unchanged)

Source: `results/co-chain-b/step3/step3_summary.md`. Violation = scalar-clock Race and collector-only not Race, on the same programs (scalar-clock recordings with every `hb_*` key deleted, run through the unmodified `parallel.py analyze` in collector-only mode). Reverse = collector-only Race and scalar-clock not Race.

#### Setting s1 (`--chain-closure --co-async --co-r3 strict`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1778, NONE 16, RACE 2929, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2929 | 2670 | 0 | 0 | 0 | 0 | 0 | 259 | 259 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |

#### Setting s2 (`--chain-closure --co-async --co-r3 off`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1776, NONE 16, RACE 2931, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2931 | 2670 | 0 | 0 | 0 | 0 | 0 | 261 | 261 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |

#### Setting cfg (`--chain-closure --co-async --co-r3 cfg`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1778, NONE 16, RACE 2929, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2929 | 2670 | 0 | 0 | 0 | 0 | 0 | 259 | 259 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |


### 4.2 Program-level violations

| setting | programs scalar-clock Race | collector-only Race | both Race | violations (scalar-clock Race, collector-only not Race) | reverse (collector-only Race, scalar-clock not) | of which scalar-clock Clean |
|---|---|---|---|---|---|---|
| S1 (strict) | 2670 | 2929 | 2670 | **0** | 259 | 259 |
| S2 (off) | 2670 | 2931 | 2670 | **0** | 261 | 261 |
| cfg (C6's R3, with the widest bound and async) | 2670 | 2929 | 2670 | **0** | 259 | 259 |

### 4.3 Per-program causes of the missing pairs (programs where scalar-clock Race and a pair of scalar-clock is not in collector-only's reports)

Per program the cause class is: certificate granted if any missing pair is of that class, else candidate missing if any, else other; lane drop only if every missing pair is a lane drop (step 3's rule). Candidate missing = the collector-only recording has no candidate pair for the scalar-clock pair (the pair's pcs are not joined by an edge or chain of reads, or are joined only thread-locally, or only through a non-read hop; sub-causes are in `pairs_*_by_program.tsv`). Certificate granted = the pair is a candidate and the verdict step orders it by a certificate (R2 coherence, morally strong RMW pair). Lane drop = the pair's pc has a dropped-word deficit (first-lane allocation lookup / words past an allocation end; static check (b) of C6).


**S1**: programs with at least one missing pair, by suite and program cause class

| suite | programs | missing pairs | certificate granted | candidate missing | lane drop only | other |
|---|---|---|---|---|---|---|
| P4 | 9 | 14 | 2 | 7 | 0 | 0 |
| P5 | 1 | 1 | 0 | 1 | 0 | 0 |
| P6 | 2 | 70 | 0 | 2 | 0 | 0 |
| PI | 337 | 3617 | 0 | 309 | 28 | 0 |
| **all** | 349 | 3702 | 2 | 319 | 28 | 0 |

**S2**: programs with at least one missing pair, by suite and program cause class

| suite | programs | missing pairs | certificate granted | candidate missing | lane drop only | other |
|---|---|---|---|---|---|---|
| P4 | 9 | 14 | 2 | 7 | 0 | 0 |
| P5 | 1 | 1 | 0 | 1 | 0 | 0 |
| P6 | 2 | 70 | 0 | 2 | 0 | 0 |
| PI | 337 | 3617 | 0 | 309 | 28 | 0 |
| **all** | 349 | 3702 | 2 | 319 | 28 | 0 |

Programs whose pair counts differ between S1 and S2: 0.

### 4.4 The programs with a granted certificate and the programs with a lane drop (S1; S2 identical where the line above says 0 differ)

| program | suite | scalar-clock pairs | found in collector-only | missing | certificate granted | lane drop | sub-causes (step 3) |
|---|---|---|---|---|---|---|---|
| `P4-rule-110-racy-large` | P4 | 2 | 1 | 1 | 1 | 0 | R2 coherence (morally strong RMW pair) x1 |
| `P4-uts-racy-small` | P4 | 11 | 9 | 2 | 2 | 0 | R2 coherence (morally strong RMW pair) x2 |
| `PI-conditional_edge_neighbors_boundsBug-DAG_5n_5e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug-power_law_200n_1000e` | PI | 10 | 1 | 9 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x4 |
| `PI-conditional_edge_neighbors_boundsBug-DAG_100n_100e` | PI | 10 | 1 | 9 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x4 |
| `PI-conditional_edge_neighbors_boundsBug_atomicBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond-DAG_100n_100e` | PI | 8 | 1 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-conditional_edge_neighbors_boundsBug_cond_atomicBug-DAG_100n_100e` | PI | 33 | 20 | 13 | 0 | 4 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug-DAG_100n_100e` | PI | 6 | 5 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_100n_200e` | PI | 45 | 37 | 8 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x3 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-counterDAG_200n_1000e` | PI | 49 | 42 | 7 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x2 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_100n_100e` | PI | 7 | 6 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_200n_400e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-counterDAG_200n_1000e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_100n_100e` | PI | 8 | 6 | 2 | 0 | 2 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x2 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-counterDAG_200n_1000e` | PI | 30 | 19 | 11 | 0 | 5 | reachable only through a non-read hop x6; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-counterDAG_5n_5e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-DAG_100n_100e` | PI | 30 | 17 | 13 | 0 | 5 | reachable only through a non-read hop x8; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug_break-counterDAG_200n_1000e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-counterDAG_200n_1000e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-counterDAG_5n_5e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_atomicBug_break-DAG_100n_200e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug-DAG_100n_100e` | PI | 8 | 1 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-conditional_vertex_neighbors_boundsBug_atomicBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_atomicBug-DAG_100n_100e` | PI | 32 | 17 | 15 | 0 | 4 | reachable only through a non-read hop x11; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_atomicBug_break-DAG_200n_400e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug-DAG_100n_100e` | PI | 16 | 9 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-populate_worklist_neighbors_boundsBug_atomicBug-DAG_200n_400e` | PI | 68 | 54 | 14 | 0 | 5 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-populate_worklist_neighbors_boundsBug_atomicBug-DAG_100n_100e` | PI | 46 | 33 | 13 | 0 | 4 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_atomicBug_break-DAG_100n_100e` | PI | 7 | 6 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_break-DAG_200n_400e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |

Programs with a lane drop: 41, all Indigo 1.3 (`boundsBug` variants: an access past the allocation end): True; each of them is Race in collector-only (0 violations), so the lane drop removes pairs, not programs.

### 4.5 The deviation: probes of absent `hb_*` keys

From `assert_no_hb.txt` section 2 (the guarded loader over the three runs), verbatim:

```
## 2. Guarded loader, dynamic result over the three runs
Every kernel JSON is parsed with an object_hook that raises HbGuardError on a dict holding an hb_* key, and into a dict subclass whose
__getitem__/get/__contains__/pop/setdefault raise on an hb_* key that is PRESENT. A probe of an ABSENT hb_* key is counted per call site (the
unmodified verdict layer probes such keys on every dump, collector-only recordings included; the answer is the key-absent default).

run s1: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636
run s2: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636
run cfg: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636

Strict demonstration (S3_STRICT=1, P5-canary, one worker): the unmodified analysis raises at its first probe of an absent key -> strict mode cannot be run through to a verdict without changing sync_dominance.py:
    HbGuardError:STRICT: probe of hb key 'hb_async' at sync_dominance.py:321;chain=1
```

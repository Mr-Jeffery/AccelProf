# C6b step 3: collector-only verdict layer on the hb-stripped scalar-clock recordings of final-b

Counts are programs of the manifest (`eval/baselines/manifest.csv`, psets P1 P3 P4 P5 P6 P7 P9 PI). Verdicts: Race alone (`make_tables.race_alone_verdict`, union of reps). Violation = scalar-clock Race and collector-only not Race. Reverse = collector-only Race and scalar-clock not Race.

scalar-clock verdicts over 4725 programs: CLEAN 2037, NONE 16, RACE 2670, TIMEOUT 2


## Setting s1 (`--chain-closure --co-async --co-r3 strict`)

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

Cause per violation program: certificate granted > candidate missing > other if any pair is of that class; lane drop only if every missing pair is a lane drop (so lane drop is the sole explanation).

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


## Setting s2 (`--chain-closure --co-async --co-r3 off`)

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

Cause per violation program: certificate granted > candidate missing > other if any pair is of that class; lane drop only if every missing pair is a lane drop (so lane drop is the sole explanation).

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


## Setting cfg (`--chain-closure --co-async --co-r3 cfg`)

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

Cause per violation program: certificate granted > candidate missing > other if any pair is of that class; lane drop only if every missing pair is a lane drop (so lane drop is the sole explanation).

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


## Method and notes

- Source: the scalar-clock recordings of X1b's `final-2026-11-view` (4,725 ids, 21,636 kernel JSONs; 18 ids have no scalar-clock kernel JSONs: 16 P6 missing-exe, P7-stencil1d, P9-atomicCAS). Scalar-clock verdict and report ids: the scalar-clock rows of `eval/results/final-b/merged/baselines-cuvein.csv` (all reps, union of report ids).
- `c6b_s3_strip.py` writes the stripped copy under `/mnt/beegfs/fzheng4/c6b-step3/store` (dots symlinked, `meta.json` modes = the scalar-clock entry renamed collector-only): every `hb_*` key deleted (top level: hb_aggregates, hb_async, hb_events_count, hb_exits, hb_lanes_count, hb_rmw_points, hb_stats, hb_sync_pass; no nested one outside those subtrees), each file re-walked and asserted free of `hb_`.
- `c6b_s3_harness.py` runs the unmodified `parallel.py analyze` (collector-only mode, 16 shards x 16 workers) with sync_dominance's JSON loader guarded (see `assert_no_hb.txt`). `python/`, runtime, collector, hb_oracle.py untouched.
- The first run used the view's `meta.json`, which for 8 ids (P7-bitonic-sort, -haversine, -heartwall, -mandelbrot, -pathfinder, P9-expdist, -knn, -tridiagonal) belongs to the 1,200 s pass while the scalar-clock directory comes from a long / 24 h pass: 4 of them came out TIMEOUT (the first-pass rep metadata) and were listed as violations. Corrected: the strip now takes the meta next to the real scalar-clock directory, and those 8 ids were re-run at all three settings (`run-*/ov/`, `ov_ids.txt`); their rows replace the base rows in `merged-*`. The superseded base rows stay in `run-*/baselines-*shard*.csv`.
- Program verdict = Race alone, union of reps, as `make_tables.race_alone_verdict`. Sets: 4,725 programs; scalar-clock RACE 2,670, CLEAN 2,037, TIMEOUT 2, 16 without a row (missing-exe).
- Not committed (size): `run-*/confirm/*.json`, `run-*/probes/`, `.state-*.pkl`.

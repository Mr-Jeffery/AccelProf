# X7 Part B: the cap=84,600 s rows, merged

Branch `eval/cap-84600` (from `eval/collector-only-tables`), unmerged, no change to cuRacePaper. Nothing here edits a detector, a rule or an old CSV: the merged CSVs are new files under `eval/results/cap-84600/`.

## Summary

- 11 GPU rows were submitted at a fixed tool cap of 84,600 s (`eval/x_logs/cap84600_jobs.txt`). 9 reached a verdict (RACE or CLEAN), 1 is TIMEOUT at 84,600 s (racecheck `P4-graph-coloring-racy-large`), 1 is TIMEOUT without being run (cuRace vector-clock `P7-particlefilter`, Jeffery's 2026-10-30 rule).
- Besides the 9: cuRace collector-only `P9-atomicCAS` was re-analysed from the stored kernel JSONs (CLEAN, 0 reports, `analysis_s` 6.147 s; its reference was an analysis-cap ERROR), and the 4 iGUARD P7 long-pass rows (heartwall, mandelbrot, particlefilter, stencil1d; 5,400 s) replace their 120 s TIMEOUT rows. 16 (id, tool, mode) keys changed in all; no new row was an ERROR, so `dropped.txt` is empty.
- Table 4 changes in 4 cells, the union table in 4, the countings table in 3, the memory table in 3, Figure 6 in 8 (section 2).

## Inputs, rule, conventions

| item | value |
|---|---|
| merge rule | X1b's, `FINAL_SWEEP_B.md` 1 (i): a new row that reached RACE, CLEAN or TIMEOUT replaces all rows of its (id, tool, mode); an ERROR leaves the old rows and goes to `eval/results/cap-84600/dropped.txt` (empty) |
| base | cuRace vector/scalar-clock: `eval/results/final-b/merged/baselines-cuvein.csv` (X1b); collector-only: `eval/results/collector-only/merged/baselines-cuvein.csv` (C1); racecheck: `baselines-sanitizer.csv`; iGUARD: `baselines-iguard.csv` plus the P7 rows of job 321654 (branch `eval/iguard-p7` 146526e: `baselines-iguard-shardp7_{0..3}_4.csv`) |
| "old" in every comparison below | the base above, i.e. the state before this merge, **including** the iGUARD P7 rows with their five 120 s TIMEOUT rows (the paper's Figure 6 holds iGUARD's P7 bar, 6.6x over 9 apps; `eval/results/cap-84600/old-inputs/baselines-iguard.csv`). C3's own tables (`eval/COLLECTOR_ONLY_TABLES.md`) did not contain iGUARD on P7 |
| new rows | `eval/results/cap84600/` (racecheck, iGUARD, collector-only atomicCAS re-analysis, vector-clock haversine re-analysis), `eval/results/final-b-24h-vc/baselines-cuvein-shardcap84600-vc-haversine0_1.csv`, `eval/results/iguard-p7long/` |
| merged CSVs | `eval/results/cap-84600/baselines-cuvein.csv` (vector+scalar-clock), `baselines-cuvein-co.csv` (collector-only), `baselines-iguard.csv`, `baselines-sanitizer.csv`, `newkeys.json`, `merge_log.txt`, `dropped.txt` |
| analysis_s | Part A (`perf/verdict-parallel`, ea98fef, N = 16): every RACE/CLEAN cuRace row carries `analysis_s`, `analysis_workers`, `analysis_kjsons` and `analysis_code=partA-ea98fef` in its notes, from the A5 merged CSVs (`~/wt-x7a/eval/results/verdict-timing/{final-b-merged,collector-only-merged}`). Every RACE/CLEAN row has it (checked: 0 finished rows without); the TIMEOUT/ERROR rows do not. Two rows were not in A5: the new vector-clock haversine recording (1.530 s, re-analysed from `final-2026-11-24h-vc` with Part A's code, `eval/results/cap84600/vc-haversine-analysis/`, same CLEAN verdict) and the collector-only atomicCAS rows (6.147 s) |
| tables | `eval/baselines/make_tables.py --collector-only` on sandboxes of the old and the new CSVs (`cap_tables.sh`), C3's `co_tables1.py` for the cuRace columns, `cap_cells.py` for every tool; outputs in `eval/results/cap-84600/tables/{old,new}/` (`BASELINES.md`, `co/*.csv`, `cells.json`) |
| labels | `P9-atomicCAS` and `P9-knn` are scored race-free, as `evaluation.tex` says; the manifest labels atomicCAS racy. C3's `co_tables1.py` only overrides knn, so its collector-only cell was run with both overrides for old and new (a copy, `co_tables1_cap.py`; the vector/scalar-clock cells are the same under either label). The old cells reproduce the paper's racecheck and iGUARD cells of Table 4 and the union table for P4, P6, P9 |
| slowdown | tool wall / native wall. A re-run row divides by the native wall of its own job; a row that stayed divides by the same id-level native as before the merge (`make_tables._ratios`: the minimum over the runners), so a replaced row's native wall does not move another tool's number |
| union table | racecheck over shared memory and iGUARD over global memory use the manifest's `shared_mem` column; it reproduces the paper for P4, P6 and P9 and does not for Indigo (not affected by any row here) |


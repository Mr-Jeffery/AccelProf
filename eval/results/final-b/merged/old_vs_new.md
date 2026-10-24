Old: `eval/results/baselines-cuvein.csv` (X1). New: `eval/results/final-b/merged/baselines-cuvein.csv` (X1b).

| suite | mode | X1 RACE / CLEAN / TIMEOUT / ERROR | X1b RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |
|---|---|---|---|---|
| P1 | vector-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P1 | scalar-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P3 | vector-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P3 | scalar-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P4 | vector-clock | 16 / 12 / 0 / 0 | 16 / 12 / 0 / 0 | 0 |
| P4 | scalar-clock | 16 / 12 / 0 / 0 | 16 / 12 / 0 / 0 | 0 |
| P5 | vector-clock | 4 / 29 / 0 / 0 | 5 / 28 / 0 / 0 | 1 |
| P5 | scalar-clock | 2 / 31 / 0 / 0 | 3 / 30 / 0 / 0 | 1 |
| P6 | vector-clock | 8 / 26 / 0 / 16 | 8 / 26 / 0 / 16 | 0 |
| P6 | scalar-clock | 8 / 26 / 0 / 16 | 8 / 26 / 0 / 16 | 0 |
| P7 | vector-clock | 4 / 9 / 1 / 0 | 3 / 8 / 3 / 0 | 2 |
| P7 | scalar-clock | 4 / 9 / 1 / 0 | 4 / 9 / 1 / 0 | 0 |
| P9 | vector-clock | 2 / 6 / 2 / 0 | 2 / 6 / 2 / 0 | 0 |
| P9 | scalar-clock | 2 / 6 / 2 / 0 | 3 / 6 / 1 / 0 | 1 |
| PI | vector-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |
| PI | scalar-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |

| suite | mode | X1 → X1b | (id, mode) |
|---|---|---|---|
| P5 | scalar-clock | CLEAN → RACE | 1 |
| P5 | vector-clock | CLEAN → RACE | 1 |
| P7 | vector-clock | CLEAN → TIMEOUT | 1 |
| P7 | vector-clock | RACE → TIMEOUT | 1 |
| P9 | scalar-clock | TIMEOUT → RACE | 1 |

Every (id, mode) whose verdict changed (reports = distinct deduplicated reports of a RACE row, max over reps):

| id | mode | X1 verdict | X1 cap (s) | X1b verdict | X1b cap (s) | direction |
|---|---|---|---|---|---|---|
| P5-race_interblock_none-lock_rtraw | vector-clock | CLEAN | 1200 | RACE (1) | 1200 | CLEAN → RACE |
| P5-race_interblock_none-lock_rtraw | scalar-clock | CLEAN | 1200 | RACE (1) | 1200 | CLEAN → RACE |
| P7-haversine-cuda | vector-clock | CLEAN | 5400 | TIMEOUT | 5400 | CLEAN → TIMEOUT |
| P7-particlefilter-cuda | vector-clock | RACE (31) | 5400 | TIMEOUT | 5400 | RACE → TIMEOUT |
| P9-expdist-cuda | scalar-clock | TIMEOUT | 86400 | RACE (22) | 84600 | TIMEOUT → RACE |

Same verdict, different cap (s):

| id | mode | verdict | X1 cap | X1b cap |
|---|---|---|---|---|
| P4-matrix-multiplication-norace-large | vector-clock | CLEAN | 1200 | 5400 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | RACE | 86400 | 84600 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | RACE | 86400 | 84600 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | scalar-clock | RACE | 5400 | 1200 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | scalar-clock | RACE | 5400 | 1200 |
| P7-bfs-cuda | vector-clock | RACE | 86400 | 84600 |
| P7-heartwall-cuda | vector-clock | RACE | 86400 | 84600 |
| P7-nbody-cuda | vector-clock | CLEAN | 86400 | 84600 |
| P7-pathfinder-cuda | vector-clock | RACE | 86400 | 84600 |
| P7-stencil1d-cuda | vector-clock | TIMEOUT | 86400 | 84600 |
| P7-bfs-cuda | scalar-clock | RACE | 5400 | 1200 |
| P7-haversine-cuda | scalar-clock | CLEAN | 86400 | 84600 |
| P7-heartwall-cuda | scalar-clock | RACE | 86400 | 84600 |
| P7-lavaMD-cuda | scalar-clock | CLEAN | 5400 | 1200 |
| P7-nbody-cuda | scalar-clock | CLEAN | 86400 | 1200 |
| P7-particlefilter-cuda | scalar-clock | RACE | 86400 | 1200 |
| P7-pathfinder-cuda | scalar-clock | RACE | 86400 | 84600 |
| P7-srad-cuda | scalar-clock | CLEAN | 5400 | 1200 |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT | 86400 | 84600 |
| P9-atomicCAS-cuda | vector-clock | TIMEOUT | 5400 | 1200 |
| P9-expdist-cuda | vector-clock | TIMEOUT | 86400 | 1200 |
| P9-knn-cuda | vector-clock | CLEAN | 86400 | 84600 |
| P9-tridiagonal-cuda | vector-clock | RACE | 86400 | 84600 |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT | 86400 | 84600 |
| P9-dxtc2-cuda | scalar-clock | RACE | 5400 | 1200 |
| P9-knn-cuda | scalar-clock | CLEAN | 86400 | 84600 |
| P9-tridiagonal-cuda | scalar-clock | RACE | 86400 | 84600 |

RACE in both with a different report set, per suite|mode: {'P1|scalar-clock': 27, 'P1|vector-clock': 31, 'P4|scalar-clock': 1, 'P4|vector-clock': 3, 'P6|scalar-clock': 1, 'PI|scalar-clock': 382, 'PI|vector-clock': 396}

DIRECTION CHECK (RACE in X1, CLEAN in X1b): 0

(id, mode) keys: X1 9450, X1b 9450; changed 5

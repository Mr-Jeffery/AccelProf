Coverage: 4725 manifest ids x 2 modes; missing (id, mode): 0; ids in the CSV not in the manifest: 0; CSV rows 28236.

| suite | programs | rows | mode | CLEAN | RACE | TIMEOUT | ERROR | cap (s) |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 2400 | vector-clock | 200 | 200 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 200 | 200 | 0 | 0 | 1200 |
| P3 | 60 | 360 | vector-clock | 44 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 44 | 16 | 0 | 0 | 1200 |
| P4 | 28 | 168 | vector-clock | 12 | 16 | 0 | 0 | 1200/5400 |
|  |  |  | scalar-clock | 12 | 16 | 0 | 0 | 1200 |
| P5 | 33 | 198 | vector-clock | 28 | 5 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 30 | 3 | 0 | 0 | 1200 |
| P6 | 50 | 216 | vector-clock | 26 | 8 | 0 | 16 | 1200/84600 |
|  |  |  | scalar-clock | 26 | 8 | 0 | 16 | 1200 |
| P7 | 14 | 66 | vector-clock | 8 | 3 | 3 | 0 | 1200/5400/84600 |
|  |  |  | scalar-clock | 9 | 4 | 1 | 0 | 1200/5400/84600 |
| P9 | 10 | 48 | vector-clock | 6 | 2 | 2 | 0 | 1200/5400/84600 |
|  |  |  | scalar-clock | 6 | 3 | 1 | 0 | 1200/84600 |
| PI | 4130 | 24780 | vector-clock | 1710 | 2420 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 1710 | 2420 | 0 | 0 | 1200 |
| all | 4725 | 28236 | vector-clock | 2034 | 2670 | 5 | 16 | |
|  |  |  | scalar-clock | 2037 | 2670 | 2 | 16 | |

| suite | mode | verdict | reason class | (id, mode) |
|---|---|---|---|---|
| P6 | scalar-clock | ERROR | needs-sm90 | 16 |
| P6 | vector-clock | ERROR | needs-sm90 | 16 |
| P7 | scalar-clock | TIMEOUT | hb-state-memory | 1 |
| P7 | vector-clock | TIMEOUT | hb-clock-hang | 1 |
| P7 | vector-clock | TIMEOUT | hb-state-memory | 2 |
| P9 | scalar-clock | TIMEOUT | time-cap | 1 |
| P9 | vector-clock | TIMEOUT | hb-clock-hang | 1 |
| P9 | vector-clock | TIMEOUT | hb-state-memory | 1 |

| id | mode | first pass (1,200 s): verdict, rep walls (s) | long pass (5,400 s): verdict | rep walls (s) | median wall (s) | peak MB | node |
|---|---|---|---|---|---|---|---|
| P4-matrix-multiplication-norace-large | vector-clock | CLEAN: 1200.006, 1190.48, 1200.005 | CLEAN | 999.635, 938.776, 945.394 | 945.394 | 5,296 | c76 |
| P7-bitonic-sort-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | CLEAN | 4718.987, 4463.97, 4473.419 | 4473.419 | 8,910 | c76 |
| P7-haversine-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.004 | TIMEOUT | 5400.006, 5400.006, 5400.006 | 5400.006 | 9,499 | — |
| P7-lavaMD-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2267.895, 2227.138, 2226.8 | 2227.138 | 23,015 | c43 |
| P7-mandelbrot-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | CLEAN | 4749.016, 4860.454, 5035.371 | 4860.454 | 1,430 | c40 |
| P7-particlefilter-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | TIMEOUT | 5400.009, 5400.167, 5400.058 | 5400.058 | 125,397 | — |
| P7-srad-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2332.638, 2352.08, 2297.766 | 2332.638 | 1,072 | c76 |
| P9-dxtc2-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE | 3499.559, 3384.328, 3361.742 | 3384.328 | 2,893 | c40 |
| P9-fpc-cuda | vector-clock | TIMEOUT: 1200.037, 1200.039, 1200.039 | CLEAN | 1776.08, 1740.153, 1785.064 | 1776.08 | 2,852 | c42 |
| P7-bitonic-sort-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.004, 1200.014 | CLEAN | 2224.487, 2219.591, 2204.554 | 2219.591 | 17,746 | c40 |
| P7-mandelbrot-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.007, 1200.007 | CLEAN | 2175.979, 2112.824, 2122.107 | 2122.107 | 2,336 | c40 |

Long pass, vector-clock: 9 ids; RACE 1, CLEAN 6, TIMEOUT 2

Long pass, scalar-clock: 2 ids; CLEAN 2

| id | mode | 5,400 s verdict | 24 h verdict | wall (s) | peak MB | rc | node | in the merged CSV |
|---|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | — | RACE | 13156.552 | 71,955 | 0 | c64 | 24 h row |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | — | RACE | 13323.263 | 71,956 | 0 | c61 | 24 h row |
| P7-bfs-cuda | vector-clock | — | RACE | 11500.605 | 1,813 | 0 | c44 | 24 h row |
| P7-heartwall-cuda | vector-clock | — | RACE | 61435.923 | 6,194 | 0 | c75 | 24 h row |
| P7-nbody-cuda | vector-clock | — | CLEAN | 11252.449 | 29,009 | 0 | c24 | 24 h row |
| P7-pathfinder-cuda | vector-clock | — | RACE | 35024.582 | 17,596 | 0 | c42 | 24 h row |
| P7-stencil1d-cuda | vector-clock | — | TIMEOUT | 84600.019 | 98,492 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | vector-clock | — | ERROR | 15229.649 | 189,581 | 1 | — | 5,400 s rows kept (24 h run: ERROR) |
| P9-knn-cuda | vector-clock | — | CLEAN | 58674.223 | 22,187 | 0 | c64 | 24 h row |
| P9-tridiagonal-cuda | vector-clock | — | RACE | 51436.282 | 10,810 | 0 | c78 | 24 h row |
| P7-haversine-cuda | scalar-clock | — | CLEAN | 4131.136 | 13,999 | 0 | c24 | 24 h row |
| P7-heartwall-cuda | scalar-clock | — | RACE | 5728.658 | 6,367 | 0 | c24 | 24 h row |
| P7-pathfinder-cuda | scalar-clock | — | RACE | 20855.057 | 68,874 | 0 | c63 | 24 h row |
| P7-stencil1d-cuda | scalar-clock | — | TIMEOUT | 84600.017 | 168,102 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | scalar-clock | — | TIMEOUT | 84600.023 | 1,104 | 124 | — | 24 h row |
| P9-expdist-cuda | scalar-clock | — | RACE | 2696.849 | 13,774 | 0 | c24 | 24 h row |
| P9-knn-cuda | scalar-clock | — | CLEAN | 9680.41 | 30,386 | 0 | c74 | 24 h row |
| P9-tridiagonal-cuda | scalar-clock | — | RACE | 9227.804 | 12,340 | 0 | c74 | 24 h row |

24 h pass, vector-clock: 10 keys; RACE 6, CLEAN 2, TIMEOUT 1, ERROR 1

24 h pass, scalar-clock: 8 keys; RACE 4, CLEAN 2, TIMEOUT 2

| job name | node-hours | nodes | first start | last end |
|---|---|---|---|---|
| x1b-dryrun | 0.0 | 1 | 2026-10-22T02:12:52 | 2026-10-22T02:13:15 |
| x1b-final | 51.8 | 16 | 2026-10-22T03:23:12 | 2026-10-22T19:02:42 |
| x1b-final-24h | 186.5 | 11 | 2026-10-22T16:53:35 | 2026-10-23T22:26:01 |
| x1b-final-long | 32.3 | 5 | 2026-10-22T22:01:19 | 2026-10-23T09:56:44 |
| x1b-final-pi | 15.2 | 12 | 2026-10-22T15:00:10 | 2026-10-22T19:57:49 |
| x1b-final-r1 | 0.1 | 1 | 2026-10-22T04:37:19 | 2026-10-22T04:41:06 |
| x1b-final-r2 | 0.1 | 2 | 2026-10-22T04:41:06 | 2026-10-22T04:44:23 |
| all | 285.8 | 21 | 2026-10-22T02:12:52 | 2026-10-23T22:26:01 |

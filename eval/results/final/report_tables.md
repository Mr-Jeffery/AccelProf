Coverage: 4725 manifest ids x 2 modes; missing (id, mode): 0; ids in the CSV not in the manifest: 0; CSV rows 28230.

| suite | programs | rows | mode | CLEAN | RACE | TIMEOUT | ERROR | cap (s) |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 2400 | vector-clock | 200 | 200 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 200 | 200 | 0 | 0 | 1200 |
| P3 | 60 | 360 | vector-clock | 44 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 44 | 16 | 0 | 0 | 1200 |
| P4 | 28 | 168 | vector-clock | 12 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 12 | 16 | 0 | 0 | 1200 |
| P5 | 33 | 198 | vector-clock | 29 | 4 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 31 | 2 | 0 | 0 | 1200 |
| P6 | 50 | 216 | vector-clock | 26 | 8 | 0 | 16 | 1200/86400 |
|  |  |  | scalar-clock | 26 | 8 | 0 | 16 | 1200/5400 |
| P7 | 14 | 62 | vector-clock | 9 | 4 | 1 | 0 | 1200/5400/86400 |
|  |  |  | scalar-clock | 9 | 4 | 1 | 0 | 1200/5400/86400 |
| P9 | 10 | 46 | vector-clock | 6 | 2 | 2 | 0 | 1200/5400/86400 |
|  |  |  | scalar-clock | 6 | 2 | 2 | 0 | 1200/5400/86400 |
| PI | 4130 | 24780 | vector-clock | 1710 | 2420 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 1710 | 2420 | 0 | 0 | 1200 |
| all | 4725 | 28230 | vector-clock | 2036 | 2670 | 3 | 16 | |
|  |  |  | scalar-clock | 2038 | 2668 | 3 | 16 | |

| suite | mode | verdict | reason class | (id, mode) |
|---|---|---|---|---|
| P6 | scalar-clock | ERROR | needs-sm90 | 16 |
| P6 | vector-clock | ERROR | needs-sm90 | 16 |
| P7 | scalar-clock | TIMEOUT | hb-state-memory | 1 |
| P7 | vector-clock | TIMEOUT | hb-state-memory | 1 |
| P9 | scalar-clock | TIMEOUT | time-cap | 2 |
| P9 | vector-clock | TIMEOUT | hb-state-memory | 1 |
| P9 | vector-clock | TIMEOUT | no-kernel-in-cap | 1 |

| id | mode | first pass (1,200 s): verdict, rep walls (s) | long pass (5,400 s): verdict | rep walls (s) | median wall (s) | peak MB | node |
|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | TIMEOUT | 5400.005, 5400.016, 5400.005 | 5400.005 | 37,332 | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT: 1200.027, 1200.025, 1200.031 | TIMEOUT | 5400.005, 5400.005, 5400.016 | 5400.005 | 37,743 | — |
| P7-bfs-cuda | vector-clock | TIMEOUT: 1200.006, 1200.007, 1200.006 | TIMEOUT | 5400.006, 5400.006, 5400.019 | 5400.006 | 1,552 | — |
| P7-bitonic-sort-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | CLEAN | 3689.219, 3644.214, 3726.762 | 3689.219 | 9,191 | c58 |
| P7-haversine-cuda | vector-clock | TIMEOUT: 1200.004, 1200.003, 1200.004 | CLEAN | 4952.726, 5101.543, 4984.198 | 4984.198 | 9,565 | c52 |
| P7-heartwall-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.004 | TIMEOUT | 5400.006, 5400.006, 5400.006 | 5400.006 | 6,181 | — |
| P7-lavaMD-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | CLEAN | 1867.433, 1868.013, 1859.917 | 1867.433 | 23,009 | c62 |
| P7-mandelbrot-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.005 | CLEAN | 3892.739, 3691.401, 3576.969 | 3691.401 | 1,455 | c66 |
| P7-nbody-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.005, 5400.006, 5400.005 | 5400.005 | 29,001 | — |
| P7-particlefilter-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | RACE | 5330.785, 5312.891, 5320.796 | 5320.796 | 185,441 | c64 |
| P7-pathfinder-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.005, 5400.018, 5400.005 | 5400.005 | 16,639 | — |
| P7-srad-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2199.151, 2160.416, 2151.169 | 2160.416 | 1,073 | c61 |
| P7-stencil1d-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.016, 5400.005 | 5400.005 | 98,199 | — |
| P9-atomicCAS-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 99,522 | — |
| P9-dxtc2-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE | 3248.307, 3138.202, 3295.73 | 3248.307 | 2,874 | c79 |
| P9-expdist-cuda | vector-clock | TIMEOUT: 1200.025, 1200.024, 1200.025 | TIMEOUT | 5400.006, 5400.023, 5400.014 | 5400.014 | 12,981 | — |
| P9-fpc-cuda | vector-clock | CLEAN: 1200.032, 1162.282, 1200.03 | CLEAN | 1341.634, 1263.988, 1294.81 | 1294.81 | 2,822 | c74 |
| P9-knn-cuda | vector-clock | TIMEOUT: 1200.006, 1200.007, 1200.007 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 21,785 | — |
| P9-tridiagonal-cuda | vector-clock | TIMEOUT: 1200.006, 1200.006, 1200.005 | TIMEOUT | 5400.02, 5400.007, 5400.007 | 5400.007 | 8,744 | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | scalar-clock | TIMEOUT: 1200.005, 1200.005, 1200.006 | RACE | 4595.972, 4598.517, 4601.344 | 4598.517 | 65,897 | c64 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | scalar-clock | TIMEOUT: 1200.026, 1200.026, 1200.026 | RACE | 4594.326, 4577.193, 4607.817 | 4594.326 | 65,894 | c62 |
| P7-bfs-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.007, 1200.006 | RACE | 1506.546, 1503.232, 1506.976 | 1506.546 | 1,718 | c74 |
| P7-bitonic-sort-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 3706.864, 3721.513, 3635.393 | 3706.864 | 5,582 | c51 |
| P7-haversine-cuda | scalar-clock | TIMEOUT: 1200.002, 1200.003, 1200.004 | TIMEOUT | 5400.006, 5400.006, 5400.006 | 5400.006 | 8,328 | — |
| P7-heartwall-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.004, 5400.004, 5400.004 | 5400.004 | 6,190 | — |
| P7-lavaMD-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | CLEAN | 1501.705, 1511.127, 1506.689 | 1506.689 | 22,652 | c60 |
| P7-mandelbrot-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.004, 1200.006 | CLEAN | 2421.822, 2327.284, 2339.662 | 2339.662 | 1,269 | c52 |
| P7-nbody-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.006 | TIMEOUT | 5400.005, 5400.005, 5400.004 | 5400.005 | 28,987 | — |
| P7-particlefilter-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.005, 1200.003 | TIMEOUT | 5401.364, 5401.813, 5401.937 | 5401.813 | 185,961 | — |
| P7-pathfinder-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.006, 5400.007, 5400.006 | 5400.006 | 5,918 | — |
| P7-srad-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2536.637, 2522.389, 2555.668 | 2536.637 | 1,041 | c73 |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.005, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.018 | 5400.005 | 83,745 | — |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 899 | — |
| P9-dxtc2-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE | 1546.341, 1494.032, 1498.336 | 1498.336 | 2,650 | c52 |
| P9-expdist-cuda | scalar-clock | TIMEOUT: 1200.025, 1200.026, 1200.025 | TIMEOUT | 5400.011, 5400.006, 5400.019 | 5400.011 | 6,703 | — |
| P9-knn-cuda | scalar-clock | TIMEOUT: 1200.006, 1200.007, 1200.006 | TIMEOUT | 5400.005, 5400.005, 5400.019 | 5400.005 | 20,086 | — |
| P9-tridiagonal-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | TIMEOUT | 5400.007, 5400.026, 5400.008 | 5400.008 | 8,333 | — |

Long pass, vector-clock: 19 ids; RACE 2, CLEAN 6, TIMEOUT 11

Long pass, scalar-clock: 18 ids; RACE 4, CLEAN 4, TIMEOUT 10

| id | mode | 5,400 s verdict | 24 h verdict | wall (s) | peak MB | rc | node | in the merged CSV |
|---|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT | RACE | 14534.817 | 71,937 | 0 | c61 | 24 h row |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT | RACE | 14550.27 | 71,942 | 0 | c60 | 24 h row |
| P7-bfs-cuda | vector-clock | TIMEOUT | RACE | 6289.863 | 1,808 | 0 | c51 | 24 h row |
| P7-heartwall-cuda | vector-clock | TIMEOUT | RACE | 35574.705 | 6,194 | 0 | c58 | 24 h row |
| P7-nbody-cuda | vector-clock | TIMEOUT | CLEAN | 8197.555 | 29,294 | 0 | c62 | 24 h row |
| P7-pathfinder-cuda | vector-clock | TIMEOUT | RACE | 28386.115 | 17,592 | 0 | c63 | 24 h row |
| P7-stencil1d-cuda | vector-clock | TIMEOUT | TIMEOUT | 86400.019 | 98,495 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | vector-clock | TIMEOUT | ERROR | 17624.601 | 186,308 | 1 | — | 5,400 s rows kept (24 h run: ERROR) |
| P9-expdist-cuda | vector-clock | TIMEOUT | TIMEOUT | 86400.015 | 20,364 | 124 | — | 24 h row |
| P9-knn-cuda | vector-clock | TIMEOUT | CLEAN | 57215.724 | 22,198 | 0 | c62 | 24 h row |
| P9-tridiagonal-cuda | vector-clock | TIMEOUT | RACE | 42483.9 | 10,810 | 0 | c61 | 24 h row |
| P7-haversine-cuda | scalar-clock | TIMEOUT | CLEAN | 6931.599 | 8,348 | 0 | c63 | 24 h row |
| P7-heartwall-cuda | scalar-clock | TIMEOUT | RACE | 32057.217 | 6,186 | 0 | c52 | 24 h row |
| P7-nbody-cuda | scalar-clock | TIMEOUT | CLEAN | 8014.964 | 29,226 | 0 | c66 | 24 h row |
| P7-particlefilter-cuda | scalar-clock | TIMEOUT | RACE | 5791.383 | 186,168 | 1 | c66 | 24 h row |
| P7-pathfinder-cuda | scalar-clock | TIMEOUT | RACE | 19225.434 | 6,779 | 0 | c77 | 24 h row |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.005 | 84,061 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.03 | 908 | 124 | — | 24 h row |
| P9-expdist-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.016 | 9,912 | 124 | — | 24 h row |
| P9-knn-cuda | scalar-clock | TIMEOUT | CLEAN | 44762.407 | 20,558 | 0 | c66 | 24 h row |
| P9-tridiagonal-cuda | scalar-clock | TIMEOUT | RACE | 36768.052 | 10,360 | 0 | c61 | 24 h row |

24 h pass, vector-clock: 11 keys; RACE 6, CLEAN 2, TIMEOUT 2, ERROR 1

24 h pass, scalar-clock: 10 keys; RACE 4, CLEAN 3, TIMEOUT 3

| job name | node-hours | nodes | first start | last end |
|---|---|---|---|---|
| x1-dryrun | 0.3 | 1 | 2026-10-13T17:13:13 | 2026-10-13T17:33:50 |
| x1-dryrun2 | 0.3 | 1 | 2026-10-13T17:31:11 | 2026-10-13T17:51:34 |
| x1-final | 48.6 | 12 | 2026-10-13T17:32:21 | 2026-10-14T00:06:22 |
| x1-final-24h | 233.3 | 11 | 2026-10-14T14:23:22 | 2026-10-16T08:39:26 |
| x1-final-long | 73.9 | 12 | 2026-10-13T21:35:08 | 2026-10-14T06:51:21 |
| x1-final-long-sc | 66.3 | 14 | 2026-10-14T02:02:40 | 2026-10-14T12:23:09 |
| x1-final-pi | 11.5 | 7 | 2026-10-13T20:20:26 | 2026-10-13T22:36:33 |
| x1-post | 0.1 | 1 | 2026-10-14T12:24:10 | 2026-10-14T12:27:42 |
| x1-sanity1 | 0.1 | 1 | 2026-10-14T00:07:31 | 2026-10-14T00:11:10 |
| all | 434.4 | 15 | 2026-10-13T17:13:13 | 2026-10-16T08:39:26 |

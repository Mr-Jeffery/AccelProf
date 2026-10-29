## Sanity
- manifest ids in the 8 psets: 4725; with a row: 4725; without: 0
- modes in the rows: {'collector-only': 14125, '': 16}
- TIMEOUT/ERROR rows without a reason in notes: 0
  - ERROR P6 `missing-exe`: 16 rows
  - ERROR P9 `analysis-timeout`: 3 rows

## Per-suite verdict counts (programs; RACE if any rep RACE)
| pset | programs | RACE | CLEAN | TIMEOUT | ERROR | no row | reps disagree |
|---|---|---|---|---|---|---|---|
| P1 | 400 | 200 | 200 | 0 | 0 | 0 | 0 |
| PI | 4130 | 2642 | 1488 | 0 | 0 | 0 | 0 |
| P3 | 60 | 16 | 44 | 0 | 0 | 0 | 0 |
| P4 | 28 | 20 | 8 | 0 | 0 | 0 | 0 |
| P5 | 33 | 2 | 31 | 0 | 0 | 0 | 0 |
| P6 | 50 | 7 | 27 | 0 | 16 | 0 | 0 |
| P7 | 14 | 5 | 9 | 0 | 0 | 0 | 0 |
| P9 | 10 | 4 | 5 | 0 | 1 | 0 | 0 |
| all | 4725 | 2896 | 1812 | 0 | 17 | 0 | 0 |

## Per-suite geometric-mean slowdown (median tool wall / native wall per program, RACE/CLEAN rows) and median peak RSS
| pset | programs measured | geomean slowdown | median peak RSS (MB) | max peak RSS (MB) |
|---|---|---|---|---|
| P1 | 400 | 6.38 | 847 | 850 |
| PI | 4130 | 5.03 | 835 | 947 |
| P3 | 60 | 5.95 | 847 | 850 |
| P4 | 28 | 6.62 | 848 | 875 |
| P5 | 33 | 5.55 | 847 | 849 |
| P6 | 34 | 6.67 | 847 | 4960 |
| P7 | 14 | 93.52 | 1077 | 4240 |
| P9 | 9 | 94.19 | 954 | 1428 |

## HeCBench rows (P7, P9)
| id | verdict | reports | tool wall (s, median) | native (s) | peak RSS (MB) | records drained | cap (s) |
|---|---|---|---|---|---|---|---|
| P7-backprop-cuda | CLEAN | 0 | 1.7 | 0.268 | 897 | 1232901 | 1200 |
| P7-bezier-surface-cuda | CLEAN | 0 | 45.4 | 24.463 | 3934 | 106955008 | 1200 |
| P7-bitonic-sort-cuda | CLEAN | 0 | 635.3 | 31.94 | 1379 | 1226469735 | 1200 |
| P7-heartwall-cuda | RACE | 2 | 2347.6 | 0.769 | 987 | 8071484636 | 5400 |
| P7-haversine-cuda | CLEAN | 0 | 227.4 | 3.123 | 2306 | 629145600 | 1200 |
| P7-nbody-cuda | CLEAN | 0 | 59.9 | 14.57 | 867 | 320355120 | 1200 |
| P7-mandelbrot-cuda | CLEAN | 0 | 162.4 | 3.825 | 876 | 327687360 | 1200 |
| P7-pathfinder-cuda | RACE | 1 | 702.4 | 1.47 | 2023 | 7058581010 | 1200 |
| P7-srad-cuda | RACE | 2 | 401.3 | 0.371 | 889 | 589889126 | 1200 |
| P7-lavaMD-cuda | CLEAN | 0 | 83.4 | 0.383 | 1217 | 398843648 | 1200 |
| P7-stencil1d-cuda | CLEAN | 0 | 36373.3 | 4.774 | 4240 | 85983231000 | 84600 |
| P7-particlefilter-cuda | RACE | 30 | 3200.2 | 1.171 | 1152 | 22515702514 | 5400 |
| P7-hotspot-cuda | CLEAN | 0 | 21.5 | 0.518 | 871 | 37410000 | 1200 |
| P7-bfs-cuda | RACE | 31 | 4.8 | 1.069 | 1002 | 7436165 | 1200 |
| P9-atomicCAS-cuda | ERROR |  | 1130.4 | 3.824 | 892 | missing | 1200 |
| P9-dxtc2-cuda | RACE | 3 | 186.6 | 0.318 | 882 | 634278100 | 1200 |
| P9-knn-cuda | CLEAN | 0 | 3739.8 | 13.092 | 1015 | 11144912500 | 5400 |
| P9-tridiagonal-cuda | RACE | 20 | 4551.3 | 0.719 | 1428 | 5598992570 | 5400 |
| P9-expdist-cuda | RACE | 22 | 374.6 | 2.021 | 878 | 1650594744 | 1200 |
| P9-overlap-cuda | CLEAN | 0 | 13.0 | 0.418 | 1237 | 13107200 | 1200 |
| P9-fpc-cuda | CLEAN | 0 | 49.0 | 1.57 | 1013 | 145620992 | 1200 |
| P9-gpp-cuda | CLEAN | 0 | 9.1 | 0.268 | 881 | 10368000 | 1200 |
| P9-crs-cuda | RACE | 7 | 5.1 | 1.521 | 954 | 9864919 | 1200 |
| P9-mr-cuda | CLEAN | 0 | 47.7 | 1.771 | 852 | 149519200 | 1200 |

## µs per recorded access against X1-follow's collector-only runs (`-n 1`, eval/x1_follow/table1.md)
| program | this run: wall (s) / records / µs per record / node | X1-follow µs per record | difference |
|---|---|---|---|
| P7-heartwall-cuda | 2347.6 / 8071484636 / 0.2908 / c61 | 0.2905 | +0.1 % |
| P9-knn-cuda | 3739.8 / 11144912500 / 0.3356 / c76 | 0.2965 | +13.2 % |
| P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrit | 1.1 / 1023 / 1045 / c62 | 1449.0 | -27.9 % (above 20 %: finding) |
| P7-bfs-cuda | 4.8 / 7436165 / 0.649 / c63 | missing | no X1-follow collector-only number |
| P7-nbody-cuda | 59.9 / 320355120 / 0.1868 / c74 | missing | no X1-follow collector-only number |

## Stores: meta.json and kernel JSON checks
- `final-2026-11-co`: 4725 meta.json; runtime hashes differing from the frozen four: 0; runtime_head {'f551ca00947e': 4725}; harness (head, dirty) {('fd034431215b', 0): 4725}; modes {'collector-only': 4709}; modes with hb_trace not false: 0; kernel JSONs 80423, of them with an hb_ key: 0; nodes {'c74': 491, 'c62': 173, 'c69': 555, 'c68': 607, 'c63': 135, 'c64': 73, 'c75': 541, 'c76': 601, 'c79': 452, 'c78': 516, 'c61': 581}
- `final-2026-11-co-long`: 5 meta.json; runtime hashes differing from the frozen four: 0; runtime_head {'f551ca00947e': 5}; harness (head, dirty) {('fd034431215b', 0): 5}; modes {'collector-only': 5}; modes with hb_trace not false: 0; kernel JSONs 1637, of them with an hb_ key: 0; nodes {'c75': 1, 'c61': 1, 'c76': 1, 'c40': 1, 'c74': 1}
- `final-2026-11-co-24h`: 1 meta.json; runtime hashes differing from the frozen four: 0; runtime_head {'f551ca00947e': 1}; harness (head, dirty) {('aa15012f851f', 0): 1}; modes {'collector-only': 1}; modes with hb_trace not false: 0; kernel JSONs 1000, of them with an hb_ key: 0; nodes {'c56': 1}
- `final-2026-11-co-parity-a`: 65 meta.json; runtime hashes differing from the frozen four: 0; runtime_head {'f551ca00947e': 65}; harness (head, dirty) {('aa15012f851f', 0): 65}; modes {'collector-only': 65}; modes with hb_trace not false: 0; kernel JSONs 2025, of them with an hb_ key: 0; nodes {'c41': 22, 'c42': 22, 'c43': 21}
- `final-2026-11-co-parity-b`: 65 meta.json; runtime hashes differing from the frozen four: 0; runtime_head {'f551ca00947e': 65}; harness (head, dirty) {('aa15012f851f', 0): 65}; modes {'collector-only': 65}; modes with hb_trace not false: 0; kernel JSONs 2040, of them with an hb_ key: 0; nodes {'c40': 22, 'c62': 22, 'c55': 21}

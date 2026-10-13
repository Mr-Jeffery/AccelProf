| program | T5b dump vector-clock | T4 no-dump vector-clock | T5b dump scalar-clock | T4 no-dump scalar-clock | buckets VC / SC | vc / vs | records |
|---|---|---|---|---|---|---|---|
| **barriers, no atomics** (10) | | | | | | | |
| P7-heartwall-cuda | TIMEOUT 1200 s, 98.0 GB | TIMEOUT 1200 s, 16.5 GB | TIMEOUT 1200 s, 82.9 GB | TIMEOUT 1200 s, 16.5 GB | — / — | — | — |
| P7-hotspot-cuda | CLEAN 522 s, 2.2 GB | CLEAN 481 s, 2.0 GB | CLEAN 135 s, 1.1 GB | CLEAN 430 s, 1.9 GB | 1.01 / 1.01 | 66 MB / 36 MB | 37,410,000 |
| P7-lavaMD-cuda | TIMEOUT 1200 s, 102.5 GB | TIMEOUT 1200 s, 13.2 GB | ERROR 671 s, 181.0 GB | TIMEOUT 1200 s, 14.9 GB | — / — | — | — |
| P7-particlefilter-cuda | TIMEOUT 1230 s, 121.6 GB | TIMEOUT 1203 s, 119.3 GB | TIMEOUT 1217 s, 121.6 GB | TIMEOUT 1202 s, 119.3 GB | — / — | — | — |
| P7-pathfinder-cuda | TIMEOUT 1200 s, 30.3 GB | TIMEOUT 1200 s, 22.3 GB | TIMEOUT 1200 s, 7.6 GB | TIMEOUT 1200 s, 8.9 GB | — / — | — | — |
| P7-srad-cuda | TIMEOUT 1200 s, 1.6 GB | TIMEOUT 1200 s, 1.5 GB | TIMEOUT 1200 s, 1.0 GB | TIMEOUT 1200 s, 1.4 GB | — / — | — | — |
| P7-stencil1d-cuda | ERROR 721 s, 115.8 GB | ERROR 434 s, 118.6 GB | TIMEOUT 1200 s, 82.4 GB | ERROR 1093 s, 118.8 GB | — / — | — | — |
| P9-dxtc2-cuda | TIMEOUT 1200 s, 11.1 GB | TIMEOUT 1200 s, 8.0 GB | TIMEOUT 1200 s, 4.4 GB | TIMEOUT 1200 s, 7.9 GB | — / — | — | — |
| P9-knn-cuda | TIMEOUT 1204 s, 119.3 GB | TIMEOUT 1200 s, 43.7 GB | TIMEOUT 1200 s, 96.3 GB | TIMEOUT 1200 s, 50.8 GB | — / — | — | — |
| P9-tridiagonal-cuda | TIMEOUT 1200 s, 39.8 GB | TIMEOUT 1200 s, 27.3 GB | TIMEOUT 1200 s, 14.6 GB | TIMEOUT 1200 s, 26.8 GB | — / — | — | — |
| **atomics + barriers** (30) | | | | | | | |
| P1-CC_V_Data_Pull_…1296n | RACE 8 157 s, 20.7 GB | RACE 8 39 s, 1.3 GB | RACE 8 12 s, 1.0 GB | RACE 8 17 s, 1.2 GB | 0.23 / 0.23 | 91 MB / 48 MB | 1,949,121 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 74 s, 22.0 GB | RACE 8 43 s, 1.3 GB | RACE 8 8 s, 1.0 GB | RACE 8 17 s, 1.2 GB | 0.23 / 0.23 | 91 MB / 48 MB | 2,009,133 |
| P1-CC_V_Data_Pull_…100n | RACE 8 2 s, 1.0 GB | RACE 8 2 s, 0.9 GB | RACE 8 1 s, 0.8 GB | RACE 8 1 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 171,884 |
| P1-CC_V_Data_Pull_…1296n | RACE 9 215 s, 6.1 GB | RACE 9 52 s, 1.0 GB | RACE 9 12 s, 1.0 GB | RACE 9 26 s, 1.0 GB | 0.19 / 0.19 | 7 MB / 4 MB | 2,106,553 |
| P1-CC_V_Data_Pull_…100n | RACE 8 4 s, 1.0 GB | RACE 8 2 s, 0.9 GB | RACE 8 2 s, 0.8 GB | RACE 8 2 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 174,119 |
| P1-CC_V_Data_Pull_…1296n | RACE 9 108 s, 6.2 GB | RACE 9 93 s, 1.0 GB | RACE 9 8 s, 1.0 GB | RACE 9 32 s, 1.0 GB | 0.19 / 0.19 | 7 MB / 4 MB | 2,101,088 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 39 s, 24.0 GB | RACE 4 11 s, 1.2 GB | RACE 4 5 s, 1.0 GB | RACE 4 8 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 1,199,405 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 39 s, 24.5 GB | RACE 4 11 s, 1.2 GB | RACE 4 5 s, 1.0 GB | RACE 4 8 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 1,236,204 |
| P1-CC_V_Data_Pull_…100n | RACE 4 2 s, 1.0 GB | RACE 4 1 s, 0.9 GB | RACE 4 1 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 15 MB / 15 MB | 7 MB / 4 MB | 157,163 |
| P1-CC_V_Data_Pull_…1296n | RACE 5 77 s, 6.1 GB | RACE 5 15 s, 1.0 GB | RACE 5 6 s, 1.0 GB | RACE 5 9 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 1,319,791 |
| P1-CC_V_Data_Pull_…100n | RACE 4 4 s, 1.0 GB | RACE 4 1 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 15 MB / 15 MB | 7 MB / 4 MB | 155,434 |
| P1-CC_V_Data_Pull_…1296n | RACE 5 79 s, 6.2 GB | RACE 5 10 s, 1.0 GB | RACE 5 6 s, 1.0 GB | RACE 5 6 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 1,317,011 |
| P1-CC_V_Data_Push_…1296n | RACE 4 19 s, 6.8 GB | RACE 4 6 s, 1.2 GB | RACE 4 4 s, 1.0 GB | RACE 4 4 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 525,336 |
| P1-CC_V_Data_Push_…1296n | RACE 4 10 s, 6.9 GB | RACE 4 6 s, 1.2 GB | RACE 4 2 s, 1.0 GB | RACE 4 4 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 501,616 |
| P1-CC_V_Data_Push_…1296n | RACE 4 19 s, 5.6 GB | RACE 4 4 s, 1.0 GB | RACE 4 2 s, 1.0 GB | RACE 4 3 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 488,760 |
| P1-CC_V_Data_Push_…1296n | RACE 4 35 s, 5.6 GB | RACE 4 6 s, 1.0 GB | RACE 4 4 s, 1.0 GB | RACE 4 4 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 501,852 |
| P3-CC_V_Data_Pull_…100n | RACE 1 7 s, 1.3 GB | RACE 1 2 s, 0.9 GB | RACE 1 1 s, 0.8 GB | RACE 1 2 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 141,173 |
| P3-CC_V_Data_Pull_…100n | RACE 1 6 s, 1.4 GB | RACE 1 9 s, 1.2 GB | RACE 1 1 s, 0.8 GB | RACE 1 2 s, 0.9 GB | 17 MB / 17 MB | 55 MB / 4 MB | 141,597 |
| P4-graph-coloring-norace-large | CLEAN 36 s, 1.9 GB | CLEAN 3 s, 0.8 GB | CLEAN 1 s, 0.8 GB | CLEAN 1 s, 0.8 GB | 13 MB / 13 MB | 1 MB / 0 MB | 147,006 |
| P4-graph-coloring-racy-large | RACE 14 51 s, 1.8 GB | RACE 14 3 s, 0.8 GB | RACE 14 2 s, 0.8 GB | RACE 14 2 s, 0.8 GB | 13 MB / 13 MB | 1 MB / 0 MB | 186,283 |
| P4-graph-connectivity-norace-large | CLEAN 268 s, 3.0 GB | CLEAN 4 s, 0.9 GB | CLEAN 2 s, 0.9 GB | CLEAN 2 s, 0.9 GB | 49 MB / 62 MB | 1 MB / 1 MB | 104,181 |
| P4-graph-connectivity-racy-large | RACE 9 427 s, 3.2 GB | RACE 10 4 s, 0.9 GB | RACE 4 2 s, 0.9 GB | RACE 4 2 s, 0.9 GB | 54 MB / 58 MB | 1 MB / 1 MB | 123,279 |
| P4-matrix-multiplication-norace-large | CLEAN 705 s, 15.5 GB | CLEAN 1154 s, 5.3 GB | CLEAN 42 s, 10.9 GB | CLEAN 73 s, 1.3 GB | 0.46 / 0.46 | 69 MB / 1 MB | 7,675,094 |
| P4-matrix-multiplication-racy-large | RACE 3 806 s, 16.6 GB | RACE 3 567 s, 4.5 GB | RACE 3 45 s, 10.9 GB | RACE 3 80 s, 1.3 GB | 0.46 / 0.46 | 2 MB / 1 MB | 7,678,810 |
| P4-uts-norace-large | CLEAN 805 s, 6.0 GB | CLEAN 54 s, 1.3 GB | CLEAN 7 s, 2.5 GB | CLEAN 11 s, 1.0 GB | 0.15 / 0.14 | 2 MB / 1 MB | 8,019,120 |
| P4-uts-norace-small | CLEAN 26 s, 1.8 GB | CLEAN 2 s, 0.9 GB | CLEAN 1 s, 0.9 GB | CLEAN 1 s, 0.8 GB | 11 MB / 11 MB | 2 MB / 1 MB | 356,350 |
| P4-uts-racy-large | RACE 23 802 s, 6.5 GB | RACE 28 103 s, 1.3 GB | RACE 11 7 s, 2.5 GB | RACE 12 16 s, 1.0 GB | 0.14 / 0.14 | 2 MB / 1 MB | 8,387,364 |
| P4-uts-racy-small | RACE 11 26 s, 1.8 GB | RACE 11 2 s, 0.9 GB | RACE 9 1 s, 0.9 GB | RACE 11 1 s, 0.8 GB | 11 MB / 11 MB | 2 MB / 1 MB | 310,694 |
| P9-expdist-cuda | TIMEOUT 1200 s, 5.7 GB | TIMEOUT 1200 s, 12.0 GB | TIMEOUT 1200 s, 59.8 GB | TIMEOUT 1200 s, 7.7 GB | — / — | — | — |
| P9-fpc-cuda | ERROR 1160 s, 118.3 GB | TIMEOUT 1200 s, 4.3 GB | CLEAN 258 s, 1.3 GB | TIMEOUT 1200 s, 3.1 GB | — / — | — | — |
| **atomics only** (8) | | | | | | | |
| P1-BFS_V_Data_Pull_…1296n | CLEAN 73 s, 5.2 GB | CLEAN 3 s, 0.9 GB | CLEAN 3 s, 0.9 GB | CLEAN 2 s, 0.9 GB | 56 MB / 56 MB | 7 MB / 3 MB | 217,790 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 17 s, 3.4 GB | RACE 8 3 s, 0.9 GB | RACE 8 2 s, 0.8 GB | RACE 8 2 s, 0.9 GB | 24 MB / 24 MB | 7 MB / 4 MB | 352,229 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 17 s, 3.6 GB | RACE 8 2 s, 0.9 GB | RACE 8 1 s, 0.8 GB | RACE 8 1 s, 0.9 GB | 24 MB / 24 MB | 7 MB / 4 MB | 353,427 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 23 s, 3.5 GB | RACE 4 2 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 21 MB / 21 MB | 7 MB / 4 MB | 315,129 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 24 s, 3.7 GB | RACE 4 3 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 2 s, 0.9 GB | 21 MB / 21 MB | 7 MB / 4 MB | 327,525 |
| P9-atomicCAS-cuda | TIMEOUT 1200 s, 73.1 GB | TIMEOUT 1200 s, 96.1 GB | TIMEOUT 1200 s, 0.8 GB | TIMEOUT 1200 s, 0.9 GB | — / — | — | — |
| P9-gpp-cuda | TIMEOUT 1200 s, 73.4 GB | CLEAN 115 s, 2.8 GB | CLEAN 61 s, 2.2 GB | CLEAN 89 s, 2.7 GB | 1.90 / 1.90 | 52 MB / 25 MB | 10,368,000 |
| P9-mr-cuda | ERROR 693 s, 1.0 GB | ERROR 317 s, 0.9 GB | ERROR 177 s, 0.9 GB | ERROR 237 s, 0.9 GB | 52 MB / 52 MB | 13 MB / 6 MB | 82,019,200 |
| **neither** (10) | | | | | | | |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | TIMEOUT 1200 s, 123.7 GB | TIMEOUT 1200 s, 47.3 GB | ERROR 598 s, 181.3 GB | TIMEOUT 1200 s, 51.3 GB | — / — | — | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | TIMEOUT 1200 s, 125.2 GB | TIMEOUT 1200 s, 40.5 GB | TIMEOUT 1201 s, 165.7 GB | TIMEOUT 1200 s, 43.9 GB | — / — | — | — |
| P6-asyncmemcpy-memcpy_htod_kernel_race-racy | CLEAN 231 s, 100.1 GB | CLEAN 128 s, 88.8 GB | CLEAN 77 s, 16.0 GB | CLEAN 127 s, 88.8 GB | 88.05 / 88.05 | 0 MB / 0 MB | 8,388,610 |
| P6-interkernel-global_writewrite_race-fixed | CLEAN 255 s, 11.7 GB | CLEAN 173 s, 0.8 GB | CLEAN 252 s, 11.7 GB | CLEAN 172 s, 0.8 GB | 0 MB / 0 MB | 0 MB / 0 MB | 109,375,002 |
| P6-interkernel-global_writewrite_race-racy | CLEAN 252 s, 11.1 GB | CLEAN 153 s, 0.8 GB | CLEAN 248 s, 11.1 GB | CLEAN 151 s, 0.8 GB | 0 MB / 0 MB | 0 MB / 0 MB | 106,250,002 |
| P7-bezier-surface-cuda | ERROR 713 s, 102.6 GB | CLEAN 766 s, 66.9 GB | ERROR 815 s, 102.7 GB | CLEAN 732 s, 66.9 GB | 66.06 / 66.06 | 1 MB / 0 MB | 106,955,008 |
| P7-bitonic-sort-cuda | TIMEOUT 1200 s, 21.2 GB | TIMEOUT 1200 s, 20.1 GB | TIMEOUT 1200 s, 4.3 GB | TIMEOUT 1200 s, 18.0 GB | — / — | — | — |
| P7-haversine-cuda | TIMEOUT 1200 s, 28.3 GB | TIMEOUT 1200 s, 22.3 GB | TIMEOUT 1200 s, 10.1 GB | TIMEOUT 1200 s, 20.8 GB | — / — | — | — |
| P7-mandelbrot-cuda | TIMEOUT 1200 s, 2.6 GB | TIMEOUT 1200 s, 2.4 GB | TIMEOUT 1200 s, 1.2 GB | TIMEOUT 1200 s, 2.2 GB | — / — | — | — |
| P7-nbody-cuda | TIMEOUT 1200 s, 99.0 GB | TIMEOUT 1200 s, 56.6 GB | TIMEOUT 1200 s, 43.3 GB | TIMEOUT 1200 s, 56.6 GB | — / — | — | — |
| **P7/P9 not in the timeout set** (4) | | | | | | | |
| P7-backprop-cuda | — | CLEAN 15 s, 2.5 GB | — | CLEAN 13 s, 2.4 GB | 1.33 / 1.33 | — | — |
| P7-bfs-cuda | — | TIMEOUT 1200 s, 2.5 GB | — | TIMEOUT 1200 s, 2.4 GB | — / — | — | — |
| P9-crs-cuda | — | CLEAN 161 s, 1.6 GB | — | CLEAN 137 s, 1.6 GB | 0.67 / 0.67 | — | — |
| P9-overlap-cuda | — | CLEAN 245 s, 5.9 GB | — | CLEAN 204 s, 5.4 GB | 3.66 / 3.66 | — | — |

vector-clock: 39 of 58 finish (RACE/CLEAN), 32 under 120 s
  barrier-only programs: P7-heartwall-cuda TIMEOUT 1200.003s, P7-hotspot-cuda CLEAN 480.947s, P7-lavaMD-cuda TIMEOUT 1200.01s, P7-particlefilter-cuda TIMEOUT 1202.99s, P7-pathfinder-cuda TIMEOUT 1200.004s, P7-srad-cuda TIMEOUT 1200.005s, P7-stencil1d-cuda ERROR 434.459s, P9-dxtc2-cuda TIMEOUT 1200.005s, P9-knn-cuda TIMEOUT 1200.032s, P9-tridiagonal-cuda TIMEOUT 1200.025s
scalar-clock: 39 of 58 finish (RACE/CLEAN), 34 under 120 s
  barrier-only programs: P7-heartwall-cuda TIMEOUT 1200.002s, P7-hotspot-cuda CLEAN 429.647s, P7-lavaMD-cuda TIMEOUT 1200.005s, P7-particlefilter-cuda TIMEOUT 1201.592s, P7-pathfinder-cuda TIMEOUT 1200.003s, P7-srad-cuda TIMEOUT 1200.005s, P7-stencil1d-cuda ERROR 1092.955s, P9-dxtc2-cuda TIMEOUT 1200.005s, P9-knn-cuda TIMEOUT 1200.034s, P9-tridiagonal-cuda TIMEOUT 1200.023s

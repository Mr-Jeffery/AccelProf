| program | verdict (old → new) | native s (old → new) | collector slowdown (old → new) | new runs: verdict / wall s |
|---|---|---|---|---|
| atomicCAS | CLEAN → RACE | 3.824 → 3.772 | 295.6x → 437.5x | co: ERROR/1820.762; ERROR/1348.162; ERROR/1650.173 |
| dxtc2 | RACE | 0.318 → 0.315 | 586.8x → 638.8x | co: RACE/112.078; RACE/201.208; RACE/201.897 |
| knn | RACE | 13.092 → 11.936 | 285.7x → 323.5x | co: RACE/2209.875; RACE/3861.143; RACE/3877.083 |
| tridiagonal | RACE | 0.719 → 0.769 | 6330.1x → 4768.9x | co: ERROR/3667.28; ERROR/3652.647; ERROR/3669.239 |
| expdist | RACE | 2.021 → 1.818 | 185.4x → 154.4x | co: CLEAN/151.659; CLEAN/283.708; CLEAN/280.698 |
| overlap | CLEAN | 0.418 → 0.365 | 31.2x → 33.4x | co: CLEAN/17.709; CLEAN/12.192; CLEAN/12.19 |
| fpc | CLEAN | 1.57 → 2.535 | 31.2x → 26.6x | co: CLEAN/67.253; CLEAN/67.725; CLEAN/67.346 |
| gpp | CLEAN | 0.268 → 0.269 | 33.9x → 25.6x | co: CLEAN/6.927; CLEAN/6.827; CLEAN/6.877 |
| crs | RACE | 1.521 → 2.469 | 3.3x → 2.3x | co: RACE/5.375; RACE/6.534; RACE/5.575 |
| mr | CLEAN | 1.771 → 1.709 | 26.9x → 1.5x | co: CLEAN/3.275; CLEAN/2.623; CLEAN/2.27 |

Control (SAME apps):
equal overlap: old CO CLEAN (0 rep), old CO+chain CLEAN (0 rep), new CO CLEAN (0,0,0 rep), new CO+chain CLEAN (0,0,0 rep)
equal fpc: old CO CLEAN (0 rep), old CO+chain CLEAN (0 rep), new CO CLEAN (0,0,0 rep), new CO+chain CLEAN (0,0,0 rep)
equal gpp: old CO CLEAN (0 rep), old CO+chain CLEAN (0 rep), new CO CLEAN (0,0,0 rep), new CO+chain CLEAN (0,0,0 rep)
equal crs: old CO RACE (7 rep), old CO+chain RACE (9 rep), new CO RACE (7,7,7 rep), new CO+chain RACE (9,9,9 rep)

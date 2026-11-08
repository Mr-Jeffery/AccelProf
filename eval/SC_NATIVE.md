# SuperCollider's native HeCBench binaries (X11)

Branch eval/sc-native-hecbench (from origin/cuVein 98371ee1). Reproduce: `python eval/sc_native/check.py` (reads eval/results/sc_native/summary.csv only). All runs rtx4060ti16g, inside ubuntu2204.sif, cap 84,600 s per run; native time = median of 3 runs in the same container.

## Step 0 (SASS at sm_89, addresses/registers/comments removed; artifact commit 6a8c46c4 vs ours 7d2d3c56)

| program | SC label | same program (rule) | same input | source check (diff 6a8c46c4..7d2d3c56) | re-run |
|---|---|---|---|---|---|
| atomicCAS | racy | DIFFERENT (3) | yes | label changed (a3c11f79) | yes |
| dxtc2 | racy | DIFFERENT (3) | yes | label changed (6e11c2bb) | yes |
| knn | racy | DIFFERENT (3) | yes | label changed (22574e78) | yes |
| tridiagonal | racy | DIFFERENT (3) | yes | label still applies | yes |
| expdist | racy | DIFFERENT (3) | yes | label changed (3583b2c4) | yes |
| mr | race-free | DIFFERENT (3) | no (artifact no args, ours `100`) | label still applies | yes |
| overlap, fpc, gpp, crs | race-free | SAME (3) | yes | not needed | collector-only mode only |
| cuHadron, 17 programs | per program | SAME (3) | yes | n/a | no (not asked) |
| cuHadron, 10 programs | per program | not decidable (no binary of ours) | yes | n/a | no |

## Results (HeCBench, 10 programs; old = our own builds, new = SuperCollider's native binaries)

| program (label) | racecheck | iGUARD | vector-clock | scalar-clock | collector-only mode | SuperCollider |
|---|---|---|---|---|---|---|
| atomicCAS (RACE) | CLEAN 84.3x → CLEAN 79.9x | RACE 1091x → RACE 1099x * | TO † | TO → RACE * | CLEAN 299x → RACE 438x | RACE 1.4x † |
| dxtc2 (RACE) | CLEAN 1905x → RACE 1728x | CLEAN 20.5x → CLEAN 25.2x | RACE 9147x → RACE 7496x | RACE 1847x → RACE 1095x | RACE 587x → RACE 639x | RACE 10.5x † |
| knn (RACE) | CLEAN 712x → CLEAN 765x * | RACE 11.4x → RACE 10.8x * | CLEAN 4889x → RACE * | CLEAN 807x → RACE 1202x * | RACE 312x → RACE 324x | RACE 3.6x † |
| tridiagonal (RACE) | RACE 7693x → RACE 8712x * | CLEAN 56.1x → CLEAN 56.7x | RACE 66714x → RACE 55140x * | RACE 11969x → RACE 12135x * | RACE 6330x → RACE 4769x | RACE 16.5x † |
| expdist (RACE) | CLEAN 180x → RACE 206x | CLEAN 3.3x → CLEAN 2.8x | TO * | RACE 1234x → RACE 728x * | RACE 185x → RACE 154x | RACE 2.7x † |
| overlap (CLEAN) | CLEAN 19.5x † * | CLEAN 4.1x † | CLEAN 177x † | CLEAN 78.5x † | CLEAN 35.2x → CLEAN 33.4x | CLEAN 1.0x † |
| fpc (CLEAN) | CLEAN 269x † * | RACE 23.5x † | CLEAN 857x † | CLEAN 285x † | CLEAN 31.2x → CLEAN 26.6x | CLEAN 1.1x † |
| gpp (CLEAN) | CLEAN 14.0x † * | RACE 428x † | CLEAN 401x † | CLEAN 92.6x † | CLEAN 33.9x → CLEAN 25.6x | CLEAN 1.3x † |
| crs (CLEAN) | CLEAN 3.8x † * | CLEAN 3.8x † | CLEAN 53.7x † | CLEAN 20.8x † | RACE 3.3x → RACE 2.3x | CLEAN 1.0x † |
| mr (CLEAN) | CLEAN 10.4x → CLEAN 0.8x | RACE 51.1x → RACE 1.4x | CLEAN 251x → CLEAN 5.0x | CLEAN 92.9x → CLEAN 2.3x | CLEAN 26.9x → CLEAN 1.5x | CLEAN 1.0x † |

† old row kept (not re-run: SAME program, or SuperCollider); * 1 run; cell = verdict slowdown, changed cell = old → new; TO = timeout, ERR = error.

Control (overlap, fpc, gpp, crs, collector-only mode, 3 runs): verdicts and report counts equal the old rows (crs 7 / 9 reports). Overlap scalar-clock smoke test (1 run, 1,200 s): CLEAN, 0 reports, equal to the 3 old runs.

## Aggregates, HeCBench SuperCollider subset (labels = SuperCollider paper flags; old → new)

HeCBench SuperCollider subset (10 programs), old → new:

| tool | TP/(TP+FN) | FP/(FP+TN) | TO | ERR | geomean slowdown (n) |
|---|---|---|---|---|---|
| racecheck | 1/5 → 3/5 | 0/5 | 0 | 0 | 116.5x (10) → 91.8x (10) |
| iGUARD | 2/5 | 3/5 | 0 | 0 | 28.7x (10) → 20.0x (10) |
| vector-clock | 2/3 → 3/3 | 0/5 | 2 | 0 | 1118.6x (8) → 489.8x (7) |
| scalar-clock | 3/4 → 5/5 | 0/5 | 1 → 0 | 0 | 354.4x (9) → 218.9x (9) |
| collector-only mode | 4/5 → 5/5 | 1/5 | 0 | 0 | 107.8x (10) → 74.4x (10) |
| SuperCollider | 5/5 | 0/5 | 0 | 0 | 2.3x (10) |
## Missing and why

- atomicCAS vector-clock: not run at cap=84600 (Jeffery); recorded TO, old row also TO. atomicCAS scalar-clock (resubmitted, Jeffery): TO at 84,600 s after 60,000 of 60,003 kernels; 2 reports in that prefix (global:0x40-0xd0:RAW, global:0x40-0x100:RAW), counted RACE, no slowdown (jobs 329004 / 329005).
- tridiagonal vector-clock and scalar-clock: the first analysis (wt-x1b harness, serial) hit its 13,800 s limit; re-scored from the same recordings with the old rows' verdict code (origin/cuVein 98371ee1, 16 workers; jobs 328968/328969, 137 s / 136 s): RACE, 24 reports each, as the old rows.
- expdist vector-clock: TO at 84,600 s; analysis of the 4-kernel prefix ran out of memory (108 GB): no reports. knn vector-clock: TO at 84,600 s, 2 reports in the 279-kernel prefix, counted RACE, no slowdown.
- Race locations for atomicCAS, dxtc2, expdist in SuperCollider's reports: missing (no line table; SuperCollider not re-run).
- cuHadron: not re-run; 10 of 27 programs not decidable (no binary of ours). racecheck on atomicCAS: rc 9, hazards 0 in old and new runs, counted CLEAN as in the old row.
- Patched `bin/accelprof` copy (shadow ACCEL_PROF_HOME, `bin/` untouched), needed because the artifact binaries link cudart statically; it changes no detection logic (collector, analyzer, verdict code, harness unchanged; only adds the shared cudart to the process):
  `-  LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE} ${ARGS} ...`
  `+  LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE} ${ARGS} ...` (X11_CUDART=/usr/local/cuda-13.3/lib64/libcudart.so.13)

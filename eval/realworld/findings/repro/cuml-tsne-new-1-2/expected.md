# Expected output: cuml-tsne-new-1-2 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`cuml-tsne-new-1-2 N=1024 cells=341 reps=20 out[0]=1024 (expect 1024) runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
A correct walk accepts nodes that partition the bodies, so every body's `normsum` (sum of accepted masses) is exactly 1024.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` | `normsum != 1024` for some body: a lane walked a stale stack entry (subtrees missed or counted twice) |
| `repro_fixed` | `RESULT: OK` | any mismatch |
| `repro_perturb` (lane 0 sleeps 20 µs before each stack write) | **probably `RESULT: OK`**: lane 0's `if` reconverges before the reads. Formal-only race; report plainly if no wrong output appears. Runtime grows with the number of pushes (seconds) | `RESULT: WRONG` would mean other lanes read before lane 0's write |

Detectors on `repro`:
- **cuVein scalar-clock.** Intra-warp RAW, DR: `STS` line 18 (root push) → `LDS` lines 20/21, and `STS` line 29 (cell push) → `LDS` lines 20/21 (and the WAR back). On `repro_fixed` the pairs should be ordered *only where ptxas kept a `WARPSYNC`*. The compile check found 2 `WARPSYNC` in `repro_fixed` against 1 in `repro`, so some pairs may still be reported. Record which: that is a model-boundary data point, not a race left under PTX.
- **racecheck on `repro`.** "Warp Level Programming" RAW/WAR warnings, lines 18/29 vs 20/21. On `repro_fixed`: racecheck understands `__syncwarp`; expect none.

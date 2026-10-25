# Expected output: cuml-tsne-new-1-3 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`cuml-tsne-new-1-3 N=1048576 grid=<3*SMs> block=512 reps=20 runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host computes each block's min/max over the points it scans (block = (j / 512) % grid, plus `posxd[0]`/`posyd[0]`) and compares exactly.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` (the upstream driver's output was finite and stable in 3/3 native runs) | a block's min/max misses a value: a reader got a stale `sminx[k]` |
| `repro_fixed` | `RESULT: OK` | any mismatch |
| `repro_perturb` (threads 256..511 sleep 100 µs before their initial stores) | **probably `RESULT: OK`**: thread i < 256's `bar.sync` waits until those threads exit, after their stores. Report plainly if it stays correct | `RESULT: WRONG` would show the barrier did not wait for the non-arriving threads |

Detectors on `repro`:
- **cuVein scalar-clock.** RAW, DR, `STS` line 24 → `LDS` lines 28–31 (B1), and `STS` 28–31 → `LDS` 28–31 (B2), as the 8 upstream reports.
- **cuVein on `repro_fixed`.** None.
- **racecheck on `repro`.** RAW errors, line 24 vs line 28 (the upstream run showed 800k such errors). On `repro_fixed`: none.
- Optionally `compute-sanitizer --tool synccheck` on `repro`, which may flag the divergent barrier (not predicted).

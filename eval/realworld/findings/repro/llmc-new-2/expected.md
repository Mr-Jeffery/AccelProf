# Expected output: llmc-new-2 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`llmc-new-2 T=256 grid=(64,1) block=256 reps=20 runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host reference is the exact formula in double, with tolerance 1e-4 + 1e-3·|ref|.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` natively. The upstream driver printed 0/4096 mismatches natively but **279/4096 under racecheck**, so `repro` under racecheck is expected to print `WRONG`. | whole rows off by one warp's partial sum: `m` grows in steps of up to T per bad row |
| `repro_fixed` | `RESULT: OK`, also under racecheck | any mismatch |
| `repro_perturb` (warp 0 sleeps 100 µs between the barrier and its `shared_val` read) | `RESULT: WRONG` in every run: warps 1..7 store the next row's partials before warp 0 reads, so the rows handled by warp 0's `local_sum` are wrong | `RESULT: OK` would mean warp 0 still read before the others' next store. Check that `NANOSLEEP` sits between `BAR.SYNC` and the `LDS` in the SASS (the compile check found 1 `NANOSLEEP`) |

Detectors on `repro`:
- **cuVein scalar-clock.** One report (WAR/RAW): the `STS` at line 18 vs the `LDS` at line 20, shared, DR, as on the upstream build.
- **cuVein on `repro_fixed`.** None: the second `BAR.SYNC` orders the read before the next write.
- **racecheck on `repro`.** WAR and RAW errors (cross-warp) and "Warp Level Programming" warnings (same warp), lines 18/20. On `repro_fixed`: none.

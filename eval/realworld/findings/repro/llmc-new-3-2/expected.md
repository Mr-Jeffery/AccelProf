# Expected output: llmc-new-3-2 reproducers (kernel 8; not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`llmc-new-3-2 kernel8 T=256 grid=(64,1) block=256 reps=20 runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
All three files include PR #847's `block.sync()` after the init (line 23), so llmc-new-3's WAW is absent.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` (the upstream program passed 3/3 natively; kernel 8 was never run under racecheck) | whole rows wrong by a neighbouring row's warp partial |
| `repro_fixed` | `RESULT: OK` | any mismatch |
| `repro_perturb` (warp 0 sleeps 100 µs between the barrier at line 32 and its read at line 33) | `RESULT: WRONG` in every run: warps 1..7 store the next row's partials (line 31) before warp 0 reads | `RESULT: OK`: check that `NANOSLEEP` sits between `BAR.SYNC` and the `LDS` |

Detectors on `repro`:
- **cuVein scalar-clock.** Three WAR reports (`LDS` line 33 vs `STS` line 31 of the next unrolled iteration), DR, plus the benign same-value WAW of line 31 with itself (4×).
- **cuVein on `repro_fixed`.** The WARs disappear. The same-value WAWs stay (benign).
- **racecheck on `repro`.** WAR errors (cross-warp) and warp-level warnings, lines 31/33. Possibly none natively if no lap occurs under racecheck's schedule; record what it prints.

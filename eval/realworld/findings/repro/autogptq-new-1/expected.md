# Expected output: autogptq-new-1 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`autogptq-new-1 m=64 n=256 grid=(32,4) block=32 reps=50 runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host reference runs the two phases lane by lane in program order and compares exactly.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK`. The upstream driver printed 0/128 mismatches natively and under racecheck | packed words with nibbles from the poisoned/previous tile (a read before the other lane's write) |
| `repro_fixed` (`__syncthreads()` between phases) | `RESULT: OK` | any mismatch |
| `repro_perturb` (lanes 16..31 sleep 100 µs before each unpack iteration) | **probably `RESULT: OK`**: the `if` reconverges before the stores, and the loop's `BSYNC` reconverges the warp before the repack loads. A formal-only race: report plainly if no wrong output can be produced | `RESULT: WRONG` would show the convergence barrier does not hold readers back |

Detectors on `repro`:
- **cuVein scalar-clock.** ~112 RAW intra-warp DR reports, `STS.U8` lines 17/19 vs `LDS.U8` line 33 (up to 16 more may come out as `barrier-ordered`, as on the upstream build; see the triage).
- **cuVein on `repro_fixed`.** None for these pairs: the `BAR.SYNC` orders them. With `__syncwarp()` instead, the reports would remain (no `WARPSYNC` in the SASS).
- **racecheck on `repro`.** "Warp Level Programming" RAW warnings, lines 17/19 vs 33. None on `repro_fixed`.

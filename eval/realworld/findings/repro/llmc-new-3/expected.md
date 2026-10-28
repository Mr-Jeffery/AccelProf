# Expected output: llmc-new-3 reproducers (kernel 7; not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`llmc-new-3 kernel7 T=256 grid=(256,1) block=256 reps=20 runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host reference is the exact formula in double, with tolerance 1e-4 + 1e-3·|ref|.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` natively. The upstream program passed 3/3 natively and **failed under racecheck** ("Mismatch of dpreatt"), so `repro` under racecheck is expected to print `WRONG` | rows t ≥ 32 off by one warp's partial (a lost `block_acc[r]`) |
| `repro_fixed` | `RESULT: OK`, also under racecheck | any mismatch |
| `repro_perturb` (warp 0 sleeps 100 µs before its init) | `RESULT: WRONG` in every run: warps 1..7 store their sums, then warp 0 zeroes `block_acc[0..31]`, so rows t ≥ 32 lose all of warps 1..7 | `RESULT: OK` would mean the stores of warps 1..7 came after the init anyway. Check the SASS order (`NANOSLEEP` before the init `STS`) |

Detectors on `repro`:
- **cuVein scalar-clock.** WAW, DR, the `STS` at line 20 (init) vs line 26 (warp sum). Also the benign same-value WAW of line 26 with itself (all lanes of a warp, one instance).
- **cuVein on `repro_fixed`.** The init/sum WAW disappears. The same-value line-26 WAW stays (benign; the fix does not touch it).
- **racecheck on `repro`.** WAW errors, line 20 vs line 26, in blocks t ≥ 32. Nothing on `repro_fixed`.

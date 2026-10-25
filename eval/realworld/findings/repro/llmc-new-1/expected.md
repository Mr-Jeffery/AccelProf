# Expected output: llmc-new-1 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints two lines:
`llmc-new-1 kernel10 tail: grid=<2*SMs> block=512 reps=200 runs_with_wrong_sums=<k> err=no error` and `RESULT: OK|WRONG|ERROR`.
The last block sums `b+1` (dbias) and `2(b+1)` (dweight) over all blocks b. The host compares against `grid(grid+1)/2` and twice that, exactly: the values are integers below 2^24.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `runs_with_wrong_sums=0`, `RESULT: OK`. The upstream program matched in 3/3 native runs. | `k > 0`: the last block read a stale (zero, from the `cudaMalloc`/previous run) or partial scratch entry |
| `repro_fixed` | `RESULT: OK` | any `k > 0` |
| `repro_perturb` (odd blocks sleep 20 µs before storing) | `RESULT: OK`. No perturbation of the source order can push a store past the same block's later barrier and atomic. A wrong result would need the hardware to make the store visible at L2 after the atomic, which sm_89 is not known to do. State plainly if it stays OK. | `k > 0` |

Detectors on `repro` (line numbers of `repro.cu`):
- **cuVein scalar-clock.** Cross-block RAW, global, DR. The `STG.E.128` of lines 21/22 (`scratch_dbias`/`scratch_dweight` stores) vs the `LDG.E.128` of lines 35/36, possibly line-tagged 37 (the accumulate line), as in the upstream build.
- **cuVein on `repro_fixed`.** No report for this pair: two `MEMBAR.SC.GPU` around the atomic give a release and an acquire pattern.
- **racecheck on `repro`.** No hazards. Racecheck does not check global memory.

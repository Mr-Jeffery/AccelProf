# Expected output: cuml-tsne-new-1 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`cuml-tsne-new-1 grid=<2*SMs> block=1024 reps=20 acc[0]=<x> ref=<y> runs_with_mismatches=<r> total_mismatches=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
Every thread sums its warp's copy `dq[sbase .. sbase+11]`. The check is that every thread's sum equals thread 0's bit for bit, and is within 1e-4 relative of the host value. The host value uses double, so `acc[0]` and `ref` agree only to float precision.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` | some warp's sum differs: a lane read its warp's `dq` slot before the owning lane copied it (uninitialised shared memory) |
| `repro_fixed` | `RESULT: OK` | any mismatch |
| `repro_perturb` (warp 0 and lanes 16..31 of every warp sleep 100 µs inside the copy branch) | **probably `RESULT: OK`**. The cross-warp part is value-benign by construction. For the intra-warp part the branch reconverges (`BSYNC`) before the reads. Report plainly if no wrong output appears | `RESULT: WRONG`: a lane read before its warp-mate's delayed copy |

Detectors on `repro`:
- **cuVein scalar-clock.** WAR, DR, `LDS`/`STS` of line 23 with itself (cross-warp, value-benign). RAW, DR, `STS` line 23 → `LDS` line 27 (intra-warp).
- **cuVein on `repro_fixed`.** Neither: the restored `BAR.SYNC` orders both.
- **racecheck on `repro`.** Errors or warnings on line 23 (cross-warp WAR; racecheck may suppress same-value cases, not checked) and warp-level hazards line 23/27. None on `repro_fixed`.

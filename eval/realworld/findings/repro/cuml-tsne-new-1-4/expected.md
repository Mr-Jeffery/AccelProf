# Expected output: cuml-tsne-new-1-4 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`cuml-tsne-new-1-4 cells=341 grid=<SMs> block=768 reps=20 runs_with_wrong_cells=<r> total_wrong_cells=<m> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host compares every cell's `massd` and `countd` exactly (integers) and `posxd`/`posyd` within 1e-3 against the recursive host build.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` | a parent cell with a wrong count or centre of mass: it used a child's payload read before the child's stores were visible (stale or `-1`/0 data) |
| `repro_fixed` | `RESULT: OK` | any wrong cell |
| `repro_perturb` (odd cells sleep 20 µs before publishing) | **probably `RESULT: OK`**. A wrong cell needs a stale L1 hit on the payload line after the strong flag read; nothing in the program forces one. Report plainly if no wrong output appears | `RESULT: WRONG`: a consumer read a stale `countd`/`posxd`/`posyd` |
| any | the kernel spins until children are ready. A hang would mean a lost flag, which the fix does not change | timeout |

Detectors on `repro`:
- **cuVein scalar-clock.** DR reports, the payload `STG.E` at line 32 (countd/posxd/posyd) vs the `LDG.E` at lines 30/31. SC reports on the `massd` flag, line 35 (`STG.E.STRONG.SYS`) vs lines 18/21/24 (`LDG.E.STRONG.SYS`).
- **cuVein on `repro_fixed`.** The DR payload reports should go: release pattern plus acquire fence. The SC flag reports stay; they are the intended synchronization.
- **racecheck.** Not applicable (global memory).

# Expected output: cuml-tsne-new-1-5 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Each binary prints
`cuml-tsne-new-1-5 N=50000 grid=<3*SMs> block=512 reps=20 bodies_in_tree(last)=50000 runs_with_bad_tree=<r> err=no error` and `RESULT: OK|WRONG|ERROR`.
The host walks the tree from the root (node NNODES). A correct tree reaches each of the 50,000 bodies exactly once. A cycle, a repeated node or a leftover lock (−2) poisons the count (large negative).

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `RESULT: OK` | `bodies_in_tree != 50000`: a body lost (overwritten slot), duplicated, or a lock left behind |
| `repro_fixed` (`volatile` `childd`) | `RESULT: OK` | any bad tree |
| `repro_perturb` (lock holders sleep 20 µs before fence and unlock) | **probably `RESULT: OK`**, slower. Stale reads are re-validated by the CAS. Report plainly if no wrong output appears | `RESULT: WRONG` |
| any | a hang means a lock that is never released. Not expected | timeout |

Detectors on `repro`:
- **cuVein scalar-clock.** DR reports on `childd`: `LDG.E` line 18 (L239) vs `ATOMG.CAS` lines 22/24 and `STG.E` lines 29/32/35/37; CAS vs `STG`; `STG` vs `STG` line 37. The same 16 kinds as upstream.
- **cuVein on `repro_fixed`.** The DR reports become SC: all `childd` accesses are `.STRONG.SYS` or atomics, the intended lock-free protocol. No DR expected.
- **racecheck.** Not applicable (global memory).

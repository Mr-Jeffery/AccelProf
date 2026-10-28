# Expected output: pytorch_cluster-new-1 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89).

- `repro` / `repro_fixed` print one line:
  `pytorch_cluster-new-1 [FIXED ]fps_kernel<float> B=2 N=512 M=128 no error out[0..3]=0,a,b,c invalid=k/256 -> OK|WRONG OUTPUT`
- `repro_perturb` prints three such lines, `PERTURBED mode=0|1|2`.
- `invalid=k` counts the picks `out[m]` that are not a farthest point given the GPU's own previous picks (plus a wrong start index), recomputed on the host. Coordinates are integers in [0,100), so the check is exact and ties are accepted.
- Exit code: `repro` and `repro_fixed` return 1 if k > 0. `repro_perturb` returns 1 only if mode 0 is wrong.

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `invalid=0/256 -> OK`. The upstream driver printed 0 mismatches in 3 native runs. Under racecheck the upstream driver gave 61/256 mismatches, so `repro` under racecheck may print WRONG OUTPUT. | `invalid>0`: some `out[m]` carries the index of a nearer point (a torn value/index pair) |
| `repro_fixed` | `invalid=0/256 -> OK`, also under racecheck | any `invalid>0` |
| `repro_perturb mode=0` | same as `repro`: OK | n/a |
| `repro_perturb mode=1` (writer thread 64 delayed between its value store and its index store; one side only) | probably OK. The reader normally loads slot 64 before the writer's value store, so no tear. Any `invalid>0` here would show that a one-sided delay suffices. | `invalid>0` |
| `repro_perturb mode=2` (mode 1 + reader thread 0 delayed ~10 us at step 64) | `invalid>0 -> WRONG OUTPUT`: deterministic tear whenever thread 64 updates slot 64. Wrong picks are expected in roughly a quarter of the iterations (estimate). | `invalid=0` would mean the tear did not happen: check that the writer's `STS` precedes its NANOSLEEP and the reader's `LDS` follow its NANOSLEEP (they do in the CUDA 13.4 SASS) |

Detectors on `repro` (`repro.cu` lines):
- **cuVein scalar-clock:** 14 RACE/WAR/DR reports, `LDS` line 27 vs `STS` line 28 (value) and `LDS.64` line 29 vs `STS.64` line 29 (index), one pair per step i = 1..64; none for i = 128. On `repro_fixed`: none in the reduction.
- **racecheck:** WAR hazards on `best_dist`/`best_dist_idx`, same-warp warnings for i < 32 and cross-warp errors at warp boundaries and for i = 32, 64. On `repro_fixed`: none expected.

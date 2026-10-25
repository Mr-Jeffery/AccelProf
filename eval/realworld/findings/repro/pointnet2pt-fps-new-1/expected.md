# Expected output: pointnet2pt-fps-new-1 reproducers (not run yet; predictions only)

Build: `bash build.sh` (CUDA 13.4, sm_89). Every binary prints one line of this form:

`pointnet2pt-fps-new-1 [FIXED|PERTURBED ]fps<512> B=2 N=2048 M=256 no error idx[0..3]=0,a,b,c invalid=k/512 -> OK|WRONG OUTPUT`

- `invalid=k` counts the picks `idx[j]` that do not maximise the min-distance to `idx[0..j-1]` (plus `idx[0] != 0`), recomputed on the host. Coordinates are integers, so the check is exact.
- Exit code: 1 if k > 0, else 0.
- `idx[0..3]` was not predicted (no GPU run yet). `a,b,c` must agree between `repro` and `repro_fixed` whenever both print OK, unless distance ties make the GPU choose a different valid farthest point (the check accepts that).

| binary | native expectation | what a wrong output looks like |
|---|---|---|
| `repro` | `invalid=0/512 -> OK`: the race is latent under the native schedule. The upstream driver printed 0 mismatches in 3 native runs. | `invalid>0 -> WRONG OUTPUT`. Under compute-sanitizer racecheck the upstream driver gave 503/512 mismatches, so `repro` under racecheck may print WRONG OUTPUT too. |
| `repro_fixed` | `invalid=0/512 -> OK`, also under racecheck | any `invalid>0` would mean the fix is incomplete |
| `repro_perturb` | `invalid>0 -> WRONG OUTPUT`, deterministic, most of the 512 picks after the first few iterations. Warp 1 waits ~100 us before the line-37 read, thread 0 overwrites `dists_i[0]` at line 30 in the meantime, and warp 1 measures each iteration from the wrong point. | `invalid=0 -> OK` would mean the delay did not let thread 0 reach the write first (check `nvdisasm`: NANOSLEEP must precede the `LDS [0x...]` of the read) |

Detectors on `repro` (line numbers are `repro.cu`'s):
- **cuVein scalar-clock:** one RACE, WAR, DR, `STS` line 30 (upstream L112) vs `LDS` line 37 (upstream L170). On `repro_fixed`: no report for that pair.
- **racecheck:** WAR errors `Read Thread (t>=32)` at the line-37 `LDS` vs `Write Thread (0,0,0)` at the line-30 `STS`, cross-warp, plus same-warp warnings for t < 32. RAW errors appear if a read observed the new value. On `repro_fixed`: no hazards on `dists_i[0]` expected.

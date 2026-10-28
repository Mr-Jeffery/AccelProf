
### 1.2 Allocations, nodes, checks run once per route

| job | node | partition | what |
|---|---|---|---|
| 315585 `t21a-hold` | c38 (16 cores, 125 GB, sm_75 GPU unused) | `rtx2060super` | CPU builds, `lineinfo`, `smoke`, SASS attribution |
| 315642 `t21a-hold2` | c63 | `rtx2060super` | started late, never used |
| 315614 `t21a-gpu` | c3 (RTX 4060 Ti 16 GB, sm_89, driver 580.82.07) | `rtx4060ti16g` | every `native`, `reach` and `racecheck` run below |

`lineinfo` (SASS of one kernel with and without `-lineinfo`, `cuobjdump -sass -arch sm_89`): R1h `targets/cccl-1/lineinfo.check`
SAME; R2 `targets/lit-arrayfire-1/lineinfo.check` SAME (all eight `*nonfinal_kernel*` instantiations); R1
`targets/hecbench-dxtc2-1/lineinfo.check` SAME (kernel `compress`, 2,576 SASS lines). The traced builds are the `-lineinfo` ones
(which are the ones built). R1h include proof: `h_proof.txt` next to every artifact of the R1h targets (cccl-1..4: checkout
headers only; raft-1: the checkout's raft/rmm/rapids-logger headers, CCCL from the toolkit because raft is not a CCCL target).
R2: `targets/<id>/r2/fixdiff.check` RESULT PASS for all eleven R2 targets. Every artifact holds sm_89 SASS (no PTX-only
architecture): `eval/realworld/elf_census.txt` (`harness/cuda_elfs.py`, executable plus `ldd` libraries).

`eval/realworld/manifest.csv`: 56 rows (28 targets x 2 variants), the columns of `eval/baselines/manifest.csv` plus
target/variant/wave/route/kernel/expected_class/oracle/cmd. All rows are a plain `exe` + `args`, so `parallel.py` can consume
them (it symlinks the executable into a scratch work directory and extracts the CUDA ELFs of that executable; the kernels
of interest are in the executables). `run_target.py` was therefore not needed. T21a runs no detector, so the rows are not
exercised with `parallel.py`. Native and racecheck results: `eval/realworld/native/<id>-<variant>.json` (3 runs: rc, wall,
stdout md5), `.kernels.csv` and `.reach` (nsys kernel list; REACHED means the oracle's kernel appears), and
`eval/realworld/racecheck/<id>-<variant>.txt` (outputs above 300 KB are truncated to header + 400 lines + summary; the full
files, up to 15 MB, are in `/mnt/beegfs/fzheng4/realworld/racecheck_full/` with their sha256 in the truncation line).
Racecheck is `n/a` for global-memory targets (cccl-3, cccl-4, cmssw-1, pytorch-3, pytorch-4, ginkgo-5, amrex-1, raft-1).
`--print-limit 2000` caps the printed hazards: the errors/warnings counts in the summary line are the totals.

## 2. Oracle (step 4) and what is pending

Drafts are in `eval/realworld/oracle/<id>.json`: 28 for the built targets (sites re-checked against the sources and against
`nvdisasm -g` of the built binaries, `harness/sassline.sh`), plus 22 source-derived drafts for the 18 candidates and 4 wave-3
core targets (`"built": false`, lines re-checked against the source at the pinned/buggy commit; discrepancies between records
and sources are in each file's `open_questions`). Optional keys beyond the brief's schema were added where a target has more
than one pair (`pairs`, `extra_pairs`, `additional_pairs`, `other_conflicting_accesses`, `upstream_status`). **The
fresh-context review (step 4) has not been done**: the oracle commit hash is not written here yet, and T21b/T21c must not
score before it.

## 3. Facts found while building that T21b/T21c need

1. **Volatile shared memory has no strong token in SASS on sm_89.** `st.volatile.shared` / `ld.volatile.shared` lower to plain
   `STS` / `LDS` (cccl-1, hecbench-hungarian-1, opencv-2); volatile and atomic global accesses carry `.STRONG.SYS` /
   `.STRONG.GPU` (cccl-3, raft-1). The pre-registered SC class of the volatile-shared targets (opencv-2, hungarian-1,
   opencv_contrib-new-1, pcl-new-1, droidslam-new-1) depends on the detector knowing volatile from something other than the SASS
   access mnemonic; each oracle says what the SASS shows (D20 question for the report).
2. **`llamacpp-2`: ptxas emitted no `WARPSYNC`** in either build; the fixed PTX has one `bar.warp.sync -1` (kernel with
   `.maxntid 32`) that ptxas turned into a single NOP, so the fixed SASS is the buggy SASS plus a NOP. The conflicting lanes are
   separated only by full-mask shuffles and `REDUX`. A detector reading SASS cannot see this fix (the finding the brief asked for).
3. **Races that show without a detector.** On the sm_75 smoke builds (debugging only): pytorch-3, pytorch-4, opencv-2, lit-shoc-1
   and ginkgo-5 produce wrong or varying output in the buggy variant and correct output in the fixed one. On the sm_89
   artifacts under compute-sanitizer racecheck the buggy runs of ginkgo-1, llamacpp-4 and llamacpp-5 return wrong results
   (non-zero exit of the application inside the sanitizer). Natively on sm_89 `outputs_differ` is true for the buggy runs of
   opencv-2, lit-shoc-1 and pytorch-4 (and for programs whose output contains timings).
4. **Racecheck on fixed builds is not clean for several targets** (cccl-2, kokkos-5, kokkos-6, lit-shoc-1, lit-exllamav3-1
   report hazards in both variants); the known residuals of the brief (kokkos-5's second intra-warp RAW, hecbench-hungarian-1,
   hecbench-dxtc2-1, pytorch-4, cccl-3, cmssw-1, raft-1) are recorded in the oracles as `fixed.expected: residual` where the
   record says so. Racecheck reports hazards in every buggy shared-memory variant; the fixed variants of the other shared-memory targets report none. Whether the hazards left in the five fixed builds above are the oracle's residual or other races (cccl-2's oracle expects none) is T21b's triage; the counts are in the table.
5. **Access budgets.** All figures are estimates (counted from the code or SASS, or `ncu` instruction counts on the sm_75 smoke
   build for the helper-C targets), none measured by a detector. All are below the 1e8 hard limit; hecbench-hungarian-1 (4.4e7,
   the app's `n_tests=100` is fixed by the `_n_` branch) and amrex-1 (about 1e7) are above the 1e7 aim.
6. **Transient BeeGFS failures.** After the BeeGFS client on c38 was unloaded and remounted (~17:08), a few build runs printed
   `mkdir: cannot create directory '/mnt/beegfs/fzheng4': Permission denied` at the artifact copy and left an empty artifact
   directory while the build rc was 0. The affected builds were re-run; the final check is that all 56 artifacts exist and hold
   sm_89 code (`elf_census.txt`). `rw.sh build` does not check its artifact copy: look for an empty `artifacts ->` line.

## 4. Not done / left

- Step 4 review of the 50 oracle drafts by a fresh-context reader and the reviewed-oracle commit (coordinating session).
- Wave 3 (`pytorch-8` R4 wheels, `cudf-3/5/9` R1 + R3) is not started (D22 default). The four oracle drafts exist.
- The extended tier is untouched. No detector was run.
- The candidates' builds are T21c's (routes in the corpus section of CLAUDE.md); their oracle drafts are source-derived only.

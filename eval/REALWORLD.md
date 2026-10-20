# REALWORLD — real-world race corpus (T21)

Branch `study/realworld-corpus` (T21a), from `docs/t21-realworld-corpus` 910c016 (CLAUDE.md T21 brief; cuVein afccba7 + the
brief). The ARC main checkout's cuVein was at 59a98aa (T22/T23 merged) when this started: `eval/baselines/parallel.py` and
`run_cuvein.py` are identical in the two, so nothing here depends on the difference. T21 never rebuilds or reinstalls the
runtime; T21a runs no detector at all. Facts only: a number that was not obtained is reported as missing.

## 0. Harness (T21a steps 1 and 2)

**Layout.** `eval/realworld/harness/` holds the scripts, `eval/realworld/targets/<id>/` one directory per target
(`target.sh`, driver sources, R2 harness trees under `r2/`, the checks `fixdiff.check` / `lineinfo.check`, `status.json`).
Nothing of an upstream tree is committed except R2 harness files (`targets/<id>/r2/{buggy,fixed}/`), which are byte-for-byte
`git cat-file blob <commit>:<path>` and keep their licence header. BeeGFS: `/mnt/beegfs/fzheng4/realworld/{src,build,runs}/<id>/…`.

**Storage, as measured on 2026-10-20.** Creating a small file costs about 60 ms on the NFS home and about 180 ms on BeeGFS
(1,582 files: 90 s on home, over 5 min on BeeGFS). The brief's layout therefore holds in this form: the revision travels as
one tarball (`git archive` of only the paths the build needs -> `~/incoming/realworld/export/<id>/<variant>.tar.gz` -> BeeGFS
`src/<id>/<variant>.tar.gz`), the unpacked tree and the build run on node-local `/mnt/local/fzheng4/rw/<id>/<variant>/`, and
BeeGFS keeps the source tarball, the built artifacts (`build/<id>/<variant>/`), the run directories and the logs.

**Clones** (login node, git only): `harness/clone_repos.sh`, partial bare clones in `~/incoming/realworld/<repo>.git`
(`--filter=blob:none`; `--filter=tree:0` for pytorch, cmssw, opencv). 16 repositories, 0.4 GB in total, built in 90 s
(`harness/repos.tsv`). `harness/export_rev.sh <repo> <sha> <out.tar.gz> [paths]` prefetches the blobs of the wanted paths in
batches of 400 (a whole ginkgo tree by lazy fetch took 3m26s, by batch prefetch a 1,086-blob kokkos tree 3 s) and then runs
`git archive`.

**Per-target driver** `harness/rw.sh <id> <phase>`; phases `export` (login), `stage`, `build`, `lineinfo` (compute), `native`,
`reach`, `racecheck` (sm_89 node). `harness/hrun.sh` runs a phase as a job step inside a held allocation
(`harness/hold.sh`, `harness/hold_gpu.sh`; the cluster allocates whole nodes and the `normal` queue was hours long).
Every job script starts with `harness/job_header.sh`, which exits 97 with the hostname when `/home/fzheng4/AccelProf`,
`/mnt/beegfs/fzheng4` or the worktree is missing. Logs: `eval/x_logs/*.log` (not committed; `*.log` is gitignored).

**Routes** (rules as in the brief, T21a step 2). Every build: `-arch=sm_89` (SASS for sm_89, never PTX-only), `-lineinfo`, the
project's own optimisation flags, never `-G`; buggy and fixed use identical flags. `nvcc` has no `-H` of its own: the R1h proof
is `nvcc -Xcompiler -H` (the host compiler's include tree) analysed by `harness/h_proof.sh`; the SASS comparison with and
without `-lineinfo` is `harness/lineinfo_check.sh` (`cuobjdump -sass -arch sm_89`, which prints the `nvdisasm` listing).
R2: `harness/r2_extract.sh` then `harness/fixdiff.py <id> --write` (blob sha1 equal to the commit's blob, and
`git diff --no-index buggy fixed` over the copied files equal to `git diff <buggy> <fix>` of those files, hunks compared verbatim).
`harness/cuda_elfs.py` lists the CUDA ELFs a process can load (`ldd` + `cuobjdump -lelf/-lptx`, optional `-xelf all`) for the
shared-library targets; the run-time module list and the alignment stage are T21b's.

**Toolchain found on the nodes.** gcc 12.4, cmake 3.26, ninja, make, python 3.13 (miniconda), git. `/usr/local/cuda` is a
symlink whose target differs by node: **13.4** on c38 (the brief says 13.3; installed: cuda-13.0, 13.2, 13.4). Each build log and
each `status.json` records the toolkit it used. Excluded nodes (no `/home/fzheng4`, 2026-10-20): **c23, c46**; also c2, c21,
c37, c54 (T21 rule). Held work nodes: see section 1.2.

**Deviations from the brief, and why.** (1) The unpacked trees live on node-local disk, not BeeGFS (storage above). (2) The
CPU builds ran in an allocation on c38, partition `rtx2060super`, not `normal`: the `normal` queue's estimated start was
three hours (twelve hours for a day-long hold) while c38 was idle; c38's GPU (sm_75) is not used for any result. All native
runs, `reach` checks and racecheck runs are on sm_89 nodes.

## 1. Corpus

Per-target status, written by `eval/realworld/harness/report.py` from `eval/realworld/targets/<id>/status.json`, `native/`, `racecheck/` and the checks in each target directory. Waves 1 and 2 (28 targets) are the commitment (D22); wave 3 is not started unless Jeffery says so.

| wave | id | route | status | driver / input | kernel reached (nsys) | native (3 runs) | racecheck | checks |
|---|---|---|---|---|---|---|---|---|
| 1 | `lit-arrayfire-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `bitsandbytes-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `cmssw-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `llamacpp-2` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `llamacpp-4` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `llamacpp-5` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `cccl-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | lineinfo SAME: |
| 1 | `cccl-2` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `cccl-3` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `cccl-4` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `opencv-2` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `hecbench-dxtc2-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `hecbench-hungarian-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `hecbench-morphology-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `hecbench-surfel-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `lit-fbgemm-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `pytorch-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `pytorch-3` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `pytorch-4` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `pytorch_cluster-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 1 | `lit-shoc-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `amrex-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `ginkgo-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `ginkgo-5` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `kokkos-5` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `kokkos-6` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `raft-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 2 | `lit-exllamav3-1` | - | pending | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 3 | `pytorch-8` | - | not started (D22) | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 3 | `cudf-3` | - | not started (D22) | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 3 | `cudf-5` | - | not started (D22) | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |
| 3 | `cudf-9` | - | not started (D22) | - | buggy: -; fixed: - | buggy: -; fixed: - | buggy: -; fixed: - | - |

Counts by wave (status keyword): wave 1: pending 21; wave 2: pending 7; wave 3: not started (D22) 4

### 1.1 Per-target notes and exact commands

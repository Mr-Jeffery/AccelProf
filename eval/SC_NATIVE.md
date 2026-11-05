# SuperCollider native binaries vs ours (X11)

## Step 0 — same program? (jobs 327374 first pass, 327378 final; scripts in eval/x11/)

Base: origin/cuVein 98371ee1. HeCBench: artifact commit 6a8c46c4 (its Dockerfile) vs ours 7d2d3c56 (shallow clone, 2026-09-01), so rule 1 never applies; cuHadron: artifact states no commit. SASS compared at sm_89 after removing addresses (incl. branch/call targets), register numbers, comments. Artifact HeCBench binaries carry SASS sm_75..sm_121 (+sm_120 PTX), cuHadron sm_80..sm_120; ours sm_89 only. Not run on a GPU: "runnable" is read from the SASS archs.

| suite | program | same program (rule) | same input | runnable on | re-run proposed |
|---|---|---|---|---|---|
| HeCBench | atomicCAS | DIFFERENT (3; `_Z16atomicAddDerivedIdEvPT_`) | yes (`10000`) | sm_89 | yes |
| HeCBench | dxtc2 | DIFFERENT (3; `_Z8compressPKjS0_P5uint2i`) | yes (same args; data files at 6a8c46c4 not checkable) | sm_89 | yes |
| HeCBench | knn | DIFFERENT (3; `_Z15cuInsertionSortPfPiiii`) | yes (`100`) | sm_89 | yes |
| HeCBench | tridiagonal | DIFFERENT (3; `_Z33sweep_small_systems_global_kernelPKfS0_S0_S0_PfS1_iib`) | yes (`-num_systems=30000`) | sm_89 | yes |
| HeCBench | expdist | DIFFERENT (3; `_Z8distanceIdEvPKT_S2_iiS2_S2_PS0_`) | yes (`10000 10`) | sm_89 | yes |
| HeCBench | mr | DIFFERENT (3; `_Z8mr32_effPKjS0_Pii`) | no (artifact: no args; ours: `100`) | sm_89 | yes |
| HeCBench | overlap | SAME (3) | yes (no args) | sm_89 | no |
| HeCBench | fpc | SAME (3) | yes (`256 100`) | sm_89 | no |
| HeCBench | gpp | SAME (3) | yes (no args) | sm_89 | no |
| HeCBench | crs | SAME (3) | yes (`1 1`) | sm_89 | no |
| cuHadron | asyncmemcpy/kernel_memcpy_dtoh_race | SAME (3) | yes | sm_89 | no |
| cuHadron | asyncmemcpy/memcpy_htod_kernel_race | SAME (3) | yes | sm_89 | no |
| cuHadron | false_positives/global_bytewise_readwrite | SAME (3) | yes | sm_89 | no |
| cuHadron | false_positives/global_bytewise_writewrite | SAME (3) | yes | sm_89 | no |
| cuHadron | false_positives/shared_bytewise_readwrite | SAME (3) | yes | sm_89 | no |
| cuHadron | false_positives/shared_bytewise_writewrite | SAME (3) | yes | sm_89 | no |
| cuHadron | hostdevice/global_readwrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | hostdevice/global_writeread_race | SAME (3) | yes | sm_89 | no |
| cuHadron | hostdevice/global_writewrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | interkernel/global_readwrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | interkernel/global_writewrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | intersubwarp/shared_readwrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | intersubwarp/shared_writewrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | interwave/global_writewrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | memcpy/global_readwrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | memcpy/shared_readwrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | memcpy/shared_writewrite_race | SAME (3) | yes | sm_89 | no |
| cuHadron | bulkcpy/global_readwrite_race | not decidable (no binary of ours) | yes | sm_90 (c29), per run script | no |
| cuHadron | bulkcpy/global_readwrite_race_g2s | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | bulkcpy/global_writewrite_race | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | bulkcpy/shared_readwrite_race | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | bulkcpy/shared_writeread_race_g2s | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | bulkcpy/shared_writewrite_race_g2s | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | dsmem/shared_readwrite_race | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | dsmem/shared_writewrite_race | not decidable (no binary of ours) | yes | sm_90 (c29) | no |
| cuHadron | multigpu/global_readwrite_race | not decidable (no binary of ours) | yes | needs 2 GPUs, per run script | no |
| cuHadron | multigpu/global_writewrite_race | not decidable (no binary of ours) | yes | needs 2 GPUs, per run script | no |

## Source check: does the labelled race survive in our HeCBench commit?

Range `6a8c46c4` (artifact, 2025-09-09) .. `7d2d3c56` (ours, 2026-09-01), 5,862 commits; `git log` / `git diff` per `src/<app>-cuda/` from a blobless clone of zjin-lcf/HeCBench (job 327582 and the attribution job; diffs in eval/x_logs/x11/srccheck/). Decision from the diff only. SuperCollider label = the racy / race-free flag of the artifact subset (`scripts/hecbench/benchmarks/artifact_subset.json`: 5 racy, 5 race-free; REPRODUCTION.md section 3 lists the same 5 racy apps). Race location: the artifact's own reports in the old SuperCollider rows (knn and tridiagonal only; those artifact binaries carry line tables). The PLDI'26 paper states no per-application location (its Table 1 gives counts per suite). For atomicCAS, dxtc2 and expdist the location is missing: the artifact binaries have no line table and its raw reports were not kept.

| application | SuperCollider label | commits in range (count) | touches the labelled race (yes/no, commit) | decision |
|---|---|---|---|---|
| atomicCAS | racy | 6 | yes, a3c11f79 (location missing): `kernels.h`, the plain `*address` first read of the CAS loops becomes `__nv_atomic_load_n` (CUDA >= 12.8) | LABEL CHANGED (a3c11f79); location missing |
| dxtc2 | racy | 7 | yes, 6e11c2bb (location missing): `compress()` prologue rewritten, the colorSums / bestFitLine / sortColors shared-memory steps are now separated by `cg::sync` (00850447 and 557f37ba also change `main.cu`) | LABEL CHANGED (6e11c2bb); location missing |
| knn | racy | 9 | yes, 22574e78: `main.cu:45-49` `begin_A/begin_B/step_A/step_B/end_A` lose `__shared__`; the writes at `main.cu:60-64` (SuperCollider's reported lines) are now thread-private | LABEL CHANGED (22574e78) |
| tridiagonal | racy | 8 | no: net diff is Makefile/CMake only (`-std=c++17`, `LAUNCHER`); `cyclic_kernels.cu:108,225,226` (reported lines) and the code ordering them are unchanged | LABEL STILL APPLIES |
| expdist | racy | 7 | yes, 3583b2c4 (location missing): `kernel.h` `distance_tiled`, the `sh_B` / `sh_scale_B` fill is guarded by `tx == 0` and a `__syncthreads()` is added before first use | LABEL CHANGED (3583b2c4); location missing |
| mr | race-free | 7 | no labelled race (artifact subset marks it race-free); diff: host repeat loop and `cudaMemset` moved (b1a8e1a2), `static const` mask table made local in `sprp32.h` (f7d0d5b9); no new shared or global kernel accesses | LABEL STILL APPLIES (race-free) |

## How the artifact binaries are run (deviations from our own-build runs)

- **Container.** The artifact binaries need GLIBC 2.34, the cluster has 2.28: every tool run, and the native timing (job 327526), executes inside `ubuntu2204.sif` (`singularity exec --nv`, the image `run_supercollider.py` uses; `/mnt/beegfs`, `/opt`, `/usr/local` bound).
- **cudart.** The artifact binaries link cudart statically; the collector (`libcompute_sanitizer.so`) references cudart symbols (e.g. `cudaDeviceGetStreamPriorityRange`) that only a shared-cudart program exports, so it fails to load into them (`symbol lookup error`). cuRace clock-mode and collector-only runs therefore use a copy of `bin/accelprof` (in a shadow `ACCEL_PROF_HOME` made of symlinks to the installed runtime; `bin/` itself is untouched) with one changed line, 307:

  ```
  -        LD_PRELOAD=${LD_PRELOAD_LIB} ${EXECUTABLE} ${ARGS} >> ${OUTPUT_REDIRECT} 2>&1
  +        LD_PRELOAD="${X11_CUDART}:${LD_PRELOAD_LIB}" ${EXECUTABLE} ${ARGS} >> ${OUTPUT_REDIRECT} 2>&1
  ```
  `X11_CUDART=/usr/local/cuda-13.3/lib64/libcudart.so.13`. It changes no detection logic: the collector, `libsanalyzer`, `python/`, the verdict code and the harness are the installed ones; the line only adds a second, shared cudart to the process so the collector's symbols resolve (the program keeps its own static cudart). The image has no `git`; a shim answers the two metadata calls of `accelprof` (`rev-parse HEAD`, `status --porcelain` of `ACCEL_PROF_HOME`). racecheck and iGUARD run unpatched.
- **Checks that the patched path reproduces our results.** collector-only on the artifact binaries of gpp and crs: events 10,368,000 / 9,864,919, 10 / 50 kernels, verdicts CLEAN / RACE (7 reports), identical to the old rows. Clock-mode smoke test (overlap, scalar-clock, 1 run, 1,200 s, through the container and the patched `accelprof`) against the old row: see the line below once the job has run (jobs 327694 recording, 327695 analysis).

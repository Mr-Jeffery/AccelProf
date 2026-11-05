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

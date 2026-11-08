## Item 4: recall table (T21b, 28 targets) and candidate counts (T21c), third mode added

Sources: C2's `eval/results/realworld_co/recall.csv` and `realworld_co_t21c/recall.csv` at origin/eval/collector-only-realworld 016d93f; T21b `eval/results/realworld/recall.csv` (study/realworld-recall) for vector-clock and scalar-clock; T21c `eval/results/realworld_t21c/recall.csv` for the candidates. (C2's aggregate `eval/COLLECTOR_ONLY_REALWORLD.md/.csv` still shows hecbench-hungarian-1, raft-1 and colmap-new-1 as NOT-SCORED/ERROR; the per-set recall.csv files hold their re-analysis rows, so the counts below use those files. Reported to C2 / the coordinator as a finding.)

T21b recall.csv (mode, flavor) rows: {('vector-clock', 'main'): 58, ('scalar-clock', 'main'): 58, ('vector-clock', 'certain'): 8}

**Buggy builds, per component** (outcome counts; CO excludes the pending amrex-1 row):

| components | outcome | vector-clock | scalar-clock | collector-only |
|---|---|---|---|---|
| data-race components (oracle expects DR) | DETECTED | 25 | 25 | 21 |
| data-race components (oracle expects DR) | MISSED | 1 | 1 | 4 |
| data-race components (oracle expects DR) | PENDING (left out) | 0 | 0 | 1 |
| data-race components (oracle expects DR) | **total** | 26 | 26 | 26 |
| strong-conflict components (oracle expects SC) | DETECTED | 2 | 2 | 2 |
| strong-conflict components (oracle expects SC) | DETECTED-AS-DR | 3 | 3 | 3 |
| strong-conflict components (oracle expects SC) | **total** | 5 | 5 | 5 |

**Fixed builds** (one per target):

| outcome | vector-clock | scalar-clock | collector-only |
|---|---|---|---|
| CLEAN-FOR-PAIR | 20 | 20 | 17 |
| PENDING (left out) | 0 | 0 | 1 |
| RESIDUAL-AS-EXPECTED | 6 | 6 | 7 |
| STILL-REPORTED | 1 | 1 | 3 |
| **total** | 27 | 27 | 28 |

Paper (both modes): 25 of 26 data-race components, 5 of 5 strong-conflict components; fixed builds 21 clean for the pair, 6 residual, 1 still reported.

**Per target and component** (outcome per mode; pending = analysis re-run running):

| target | variant | comp | vector-clock | scalar-clock | collector-only |
|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | pending |
| amrex-1 | fixed | - | — | — | pending |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| bitsandbytes-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-1 | fixed | - | STILL-REPORTED | STILL-REPORTED | STILL-REPORTED |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED |
| cccl-3 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-4 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cmssw-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| ginkgo-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED |
| ginkgo-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| hecbench-hungarian-1 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| hecbench-hungarian-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-morphology-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-surfel-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED |
| kokkos-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | RESIDUAL-AS-EXPECTED |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED |
| kokkos-6 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-arrayfire-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-exllamav3-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-fbgemm-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-shoc-1 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| lit-shoc-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | STILL-REPORTED |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-4 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| opencv-2 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| opencv-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | STILL-REPORTED |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-3 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-4 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch_cluster-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED |
| raft-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |

## Candidate set (T21c): scored components

| id | component | expected | scalar-clock | collector-only | CO n_race / n_sc |
|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | 272/0 |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | 56/24 |
| droidslam-new-1-buggy | SC | SC | DETECTED-AS-DR | DETECTED-AS-DR | 21/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | not run | / |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | 1/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | 9/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 2/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DETECTED-AS-DR | DETECTED-AS-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 3/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | 136/0 |
| pcl-new-1-buggy | SC | DR+SC | DETECTED-AS-DR | DETECTED-AS-DR | 136/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 1/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | 14/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | 1/0 |

Collector-only candidate outcomes (components run): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}. Scalar-clock outcomes over the same components: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}.
lightgbm-new-1/2 are unscored (Jeffery's decision); llamacpp-open-2 was not run in C2.

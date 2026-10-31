## Recall set (T21b): per target and component, CO-R next to vector-clock, scalar-clock and the edges-only run (C2)

CO-R rows come from `eval/results/co-offline/realworld/recall.csv` (rw_score.py of study/realworld-recall on the re-analysed, re-attributed scalar-clock recordings). `NOT-SCORED` = the id has no row: its scalar-clock analysis did not finish (amrex-1: ERROR analysis-timeout at 82,800 s in T21b, not re-run).

| target | variant | comp | vector-clock | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |
|---|---|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | MISSED | stays ERROR (not re-run) | / |
| amrex-1 | fixed | - | — | — | NOT-SCORED | NOT-SCORED | / |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 65/0 |
| bitsandbytes-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 30/0 |
| cccl-1 | fixed | - | STILL | STILL | STILL | STILL | 30/0 |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 493/0 |
| cccl-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 486/0 |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 51/8 |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 51/8 |
| cccl-3 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 51/8 |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/9 |
| cccl-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/9 |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 7/0 |
| cmssw-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 0/8 |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 15/0 |
| ginkgo-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 6/0 |
| ginkgo-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 114/0 |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 3/0 |
| hecbench-hungarian-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 298/251 |
| hecbench-hungarian-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 259/253 |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 8/0 |
| hecbench-morphology-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 14/0 |
| hecbench-surfel-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 24/0 |
| kokkos-5 | fixed | - | CLEAN | CLEAN | RESIDUAL | RESIDUAL | 23/0 |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 32/0 |
| kokkos-6 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 26/0 |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 6/0 |
| lit-arrayfire-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 4/0 |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 84/0 |
| lit-exllamav3-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| lit-fbgemm-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 52/0 |
| lit-shoc-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 52/0 |
| lit-shoc-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 40/0 |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 8/0 |
| llamacpp-2 | fixed | - | CLEAN | CLEAN | STILL | STILL | 8/0 |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| llamacpp-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1032/0 |
| llamacpp-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 768/0 |
| opencv-2 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 411/0 |
| opencv-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 3/0 |
| pytorch-1 | fixed | - | CLEAN | CLEAN | STILL | STILL | 3/0 |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-3 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-4 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 1/0 |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 12/0 |
| pytorch_cluster-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 32/2 |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 32/2 |
| raft-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 32/2 |

**Counts** (rows of each mode; CO-R: ids without a row are not in the count):

| components | outcome | vector-clock | scalar-clock | edges only (C2) | CO-R |
|---|---|---|---|---|---|
| buggy, data-race components | DETECTED | 25 | 25 | 21 | 25 |
| buggy, data-race components | MISSED | 1 | 1 | 5 | 0 |
| buggy, data-race components | **total** | 26 | 26 | 26 | 25 |
| buggy, strong-conflict components | DETECTED | 2 | 2 | 2 | 2 |
| buggy, strong-conflict components | DETECTED-AS-DR | 3 | 3 | 3 | 3 |
| buggy, strong-conflict components | **total** | 5 | 5 | 5 | 5 |
| fixed builds | CLEAN-FOR-PAIR | 20 | 20 | 17 | 17 |
| fixed builds | NOT-SCORED | 0 | 0 | 1 | 0 |
| fixed builds | RESIDUAL-AS-EXPECTED | 6 | 6 | 7 | 7 |
| fixed builds | STILL-REPORTED | 1 | 1 | 3 | 3 |
| fixed builds | **total** | 27 | 27 | 28 | 27 |

## The detections the edges-only run missed

| target (component) | scalar-clock | edges only (C2) | CO-R | verdict |
|---|---|---|---|---|

Buggy data-race components DETECTED by scalar-clock and MISSED by the edges-only run (computed): [('cccl-3', 'DR'), ('ginkgo-5', 'DR'), ('kokkos-5', 'DR'), ('raft-1', 'DR')]

| CCCL top-k (cccl-3, DR) | DETECTED | MISSED | DETECTED | detected |
| Ginkgo range-minimum (ginkgo-5, DR) | DETECTED | MISSED | DETECTED | detected |
| Kokkos rw_sum (kokkos-5, DR) | DETECTED | MISSED | DETECTED | detected |
| raft-1 (raft-1, DR) | DETECTED | MISSED | DETECTED | detected |

## Candidate set (T21c)

| id | component | expected | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |
|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 620/0 |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 67/28 |
| droidslam-new-1-buggy | SC | SC | DET-as-DR | DET-as-DR | DET-as-DR | 67/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | — | DETECTED | 16/0 |
| llamacpp-open-2-fixed | - | DR | CLEAN | — | STILL | 16/0 |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 9/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 3/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | DETECTED | 657/0 |
| pcl-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 657/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 15/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |

scalar-clock: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'MISSED': 1, 'DETECTED (family)': 1}

edges only (C2): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}

CO-R: {'DETECTED': 15, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}

PCL (pcl-new-1) data-race half: scalar-clock DETECTED, edges only MISSED, CO-R DETECTED

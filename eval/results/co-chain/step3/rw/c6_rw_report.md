## Recall set (T21b): per target and component, CO+chain next to vector-clock, scalar-clock and C2's collector-only run

CO+chain rows: `rw_score.py` of study/realworld-recall on the chain-closure attribution of the C2 recordings (`rw_attribute.py` with `chain_closure=True`). `NOT-SCORED` = no row: the id was not attributed (see the missing list in CO_CHAIN.md).

| target | variant | comp | vector-clock | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |
|---|---|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | MISSED | NOT-SCORED | / **changed** |
| amrex-1 | fixed | - | — | — | NOT-SCORED | NOT-SCORED | / |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 65/0 |
| bitsandbytes-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 16/0 |
| cccl-1 | fixed | - | STILL | STILL | STILL | STILL | 16/0 |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 457/0 |
| cccl-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 447/0 |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 57/8 **changed** |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 57/8 |
| cccl-3 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 58/8 |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/15 |
| cccl-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/15 |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 5/0 |
| cmssw-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 0/6 |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 15/0 |
| ginkgo-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 6/0 **changed** |
| ginkgo-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 114/0 |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 3/0 |
| hecbench-hungarian-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 445/310 |
| hecbench-hungarian-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 441/310 |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 52/0 |
| hecbench-morphology-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 68/0 |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 27/0 |
| hecbench-surfel-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 13/0 |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 69/0 **changed** |
| kokkos-5 | fixed | - | CLEAN | CLEAN | RESIDUAL | RESIDUAL | 71/0 |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 94/0 |
| kokkos-6 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 87/0 |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 10/0 |
| lit-arrayfire-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 176/0 |
| lit-exllamav3-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 156/0 |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| lit-fbgemm-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 134/0 |
| lit-shoc-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 134/0 |
| lit-shoc-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 120/0 |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 14/0 |
| llamacpp-2 | fixed | - | CLEAN | CLEAN | STILL | STILL | 14/0 |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| llamacpp-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1546/0 |
| llamacpp-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 1026/0 |
| opencv-2 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 2521/0 |
| opencv-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 9/0 |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 5/0 |
| pytorch-1 | fixed | - | CLEAN | CLEAN | STILL | STILL | 5/0 |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| pytorch-3 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-4 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 1/0 |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 18/0 |
| pytorch_cluster-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED | MISSED | 29/2 |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 29/2 |
| raft-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 27/2 |

**Counts** (rows of each mode):

| components | outcome | vector-clock | scalar-clock | CO (C2) | CO+chain |
|---|---|---|---|---|---|
| buggy, data-race components | DETECTED | 25 | 25 | 21 | 24 |
| buggy, data-race components | MISSED | 1 | 1 | 5 | 1 |
| buggy, data-race components | **total** | 26 | 26 | 26 | 25 |
| buggy, strong-conflict components | DETECTED | 2 | 2 | 2 | 2 |
| buggy, strong-conflict components | DETECTED-AS-DR | 3 | 3 | 3 | 3 |
| buggy, strong-conflict components | **total** | 5 | 5 | 5 | 5 |
| fixed builds | CLEAN-FOR-PAIR | 20 | 20 | 17 | 17 |
| fixed builds | NOT-SCORED | 0 | 0 | 1 | 0 |
| fixed builds | RESIDUAL-AS-EXPECTED | 6 | 6 | 7 | 7 |
| fixed builds | STILL-REPORTED | 1 | 1 | 3 | 3 |
| fixed builds | **total** | 27 | 27 | 28 | 27 |

## The data-race components C2's run missed and scalar-clock detected

| target (component) | scalar-clock | CO (C2) | CO+chain |
|---|---|---|---|
| CCCL top-k (cccl-3, DR) | DETECTED | MISSED | DETECTED |
| Ginkgo range-minimum (ginkgo-5, DR) | DETECTED | MISSED | DETECTED |
| Kokkos rw_sum (kokkos-5, DR) | DETECTED | MISSED | DETECTED |
| RAFT select_k (raft-1, DR) | DETECTED | MISSED | MISSED |

Buggy data-race components scalar-clock DETECTED and C2 MISSED (computed): [('cccl-3', 'DR'), ('ginkgo-5', 'DR'), ('kokkos-5', 'DR'), ('raft-1', 'DR')]

## Candidate set (T21c)

| id | component | expected | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |
|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | NOT-SCORED | / **changed** |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 72/43 |
| droidslam-new-1-buggy | SC | SC | DET-as-DR | DET-as-DR | DET-as-DR | 187/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | — | NOT-SCORED | / **changed** |
| llamacpp-open-2-fixed | - | DR | CLEAN | — | NOT-SCORED | / **changed** |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 18/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 6/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 9/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | DETECTED | 550/0 **changed** |
| pcl-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 550/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 3/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 23/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |

scalar-clock: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'MISSED': 1, 'DETECTED (family)': 1}

CO (C2): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}

CO+chain: {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}

PCL (pcl-new-1) data-race half: scalar-clock DETECTED, C2 MISSED, CO+chain DETECTED

## CO+chain components detected through derived / rescued reports

Per attributed id: how many of the id's reports in the attribution are edge / rescued / derived (chain_src); components where the matched reports are all non-edge are listed in the attribution JSON (`c6-step3/rw/*/attrib`).

- cccl-1-buggy: 16 reports: edge 12, rescued 4, derived 0
- cccl-1-fixed: 16 reports: edge 12, rescued 4, derived 0
- cccl-2-buggy: 457 reports: edge 454, rescued 0, derived 3
- cccl-3-buggy: 65 reports: edge 44, rescued 0, derived 21
- cccl-3-fixed: 66 reports: edge 44, rescued 0, derived 22
- cccl-4-buggy: 17 reports: edge 5, rescued 2, derived 10
- cccl-4-fixed: 15 reports: edge 5, rescued 1, derived 9
- cmssw-1-buggy: 5 reports: edge 3, rescued 0, derived 2
- cmssw-1-fixed: 6 reports: edge 3, rescued 0, derived 3
- ginkgo-5-buggy: 6 reports: edge 3, rescued 3, derived 0
- hecbench-dxtc2-1-buggy: 114 reports: edge 92, rescued 10, derived 12
- hecbench-hungarian-1-buggy: 755 reports: edge 281, rescued 33, derived 441
- hecbench-hungarian-1-fixed: 751 reports: edge 276, rescued 32, derived 443
- hecbench-morphology-1-buggy: 52 reports: edge 8, rescued 16, derived 28
- hecbench-morphology-1-fixed: 68 reports: edge 8, rescued 8, derived 52
- hecbench-surfel-1-buggy: 27 reports: edge 14, rescued 0, derived 13
- hecbench-surfel-1-fixed: 13 reports: edge 0, rescued 0, derived 13
- kokkos-5-buggy: 69 reports: edge 19, rescued 14, derived 36
- kokkos-5-fixed: 71 reports: edge 23, rescued 10, derived 38
- kokkos-6-buggy: 94 reports: edge 32, rescued 10, derived 52
- kokkos-6-fixed: 87 reports: edge 26, rescued 10, derived 51
- lit-arrayfire-1-buggy: 10 reports: edge 6, rescued 1, derived 3
- lit-arrayfire-1-fixed: 8 reports: edge 4, rescued 1, derived 3
- lit-exllamav3-1-buggy: 176 reports: edge 84, rescued 0, derived 92
- lit-exllamav3-1-fixed: 156 reports: edge 64, rescued 0, derived 92
- lit-shoc-1-buggy: 134 reports: edge 22, rescued 10, derived 102
- lit-shoc-1-fixed: 120 reports: edge 10, rescued 10, derived 100
- llamacpp-2-buggy: 14 reports: edge 8, rescued 0, derived 6
- llamacpp-2-fixed: 14 reports: edge 8, rescued 0, derived 6
- llamacpp-5-buggy: 1546 reports: edge 1032, rescued 0, derived 514
- llamacpp-5-fixed: 1026 reports: edge 768, rescued 0, derived 258
- opencv-2-buggy: 2521 reports: edge 105, rescued 27, derived 2389
- opencv-2-fixed: 9 reports: edge 8, rescued 1, derived 0
- pytorch-1-buggy: 5 reports: edge 3, rescued 0, derived 2
- pytorch-1-fixed: 5 reports: edge 3, rescued 0, derived 2
- pytorch_cluster-1-buggy: 18 reports: edge 12, rescued 6, derived 0
- raft-1-buggy: 31 reports: edge 24, rescued 3, derived 4
- raft-1-fixed: 29 reports: edge 22, rescued 3, derived 4
- cuml-tsne-new-1-buggy: 115 reports: edge 80, rescued 3, derived 32
- droidslam-new-1-buggy: 187 reports: edge 21, rescued 15, derived 151
- llmc-new-2-buggy: 2 reports: edge 1, rescued 0, derived 1
- llmc-new-3-k8-buggy: 18 reports: edge 9, rescued 0, derived 9
- mmcv-fps-new-1-buggy: 6 reports: edge 2, rescued 0, derived 4
- openpcdet-fps-new-1-buggy: 9 reports: edge 3, rescued 0, derived 6
- pcl-new-1-buggy: 550 reports: edge 136, rescued 42, derived 372
- pointnet2pt-fps-new-1-buggy: 3 reports: edge 1, rescued 0, derived 2
- pytorch_cluster-new-1-buggy: 23 reports: edge 14, rescued 9, derived 0
- sglang-open-1-buggy: 2 reports: edge 1, rescued 1, derived 0

# C2: collector-only mode on the real-world recall and candidate sets

Branch `eval/collector-only-realworld` (from `eval/collector-only` fd03443, C1 step 1). Measurement only: no change in `nv-compute/`, `sanalyzer/`,
`python/hb_oracle.py` or any rule in `python/sync_dominance.py`. Written 2026-10-28. **Status: 2 of the 72 runs are unscored: amrex-1 buggy and fixed. Their long re-analyses (jobs 322934, 322935, analysis timeout 82,800 s) ended `ERROR analysis-timeout=82800s` (1,246 / 1,452 kernel JSONs) and the jobs then reached the 24 h limit before attribution; no report counts exist for them. The other 70 runs are scored (the 5 other analysis-timeout ids via their long re-analyses).**

## 0. Setup (facts)

- Runtime: `~/AccelProf` f551ca0, libsanalyzer sha256[:16] `5a20fd14ab6c6806`, collector `b746b4dd23e90f46`, fatbin `a2d7368bc1c61986`, late fatbin `e96343121c74ca0a`;
  checked at the top of every job (`co_job.sh`, exit 99 on a mismatch); all job logs show the same four hashes.
- Mode: harness mode `collector-only` (C1: `BASELINE_MODES=collector-only`, `accelprof -v -n 1`, no `YOSEMITE_HB_*` variable, meta `hb_trace=false`).
- Harness: the T21b/T21c real-world harness (`eval/realworld/harness/`, copied from `study/realworld-candidates`), manifests `manifest_t21b.csv` (56 rows, 28 targets x buggy/fixed) and
  `manifest_t21c.csv` (the 16 rows below plus the 4 not run), oracles and `recall_pairs.json` as in those runs, builds as in those runs (no target rebuilt; paths in the manifests).
  Added for C2: `co_header.sh`, `co_job.sh`, `co_attr.sh`, `co_rean.sh`, `co_diff.py`, `co_tables.py`, `co_post.sh`; `RW_MODES` in `rw_attribute.py`/`rw_score.py`;
  `blib.xelf_all` and the dot-order prefilter of `run_cuvein._analyze_reports` ported from the T21b/T21c branches (order of the dot search only; verdicts unchanged).
- Policy of the T21b/T21c runs: one rep per id, `--confirm`, tool timeout = cap = 1,200 s, analysis timeout 3,600 s, atomic-scope sidecar, `accelprof -n 1`.
  Job: array 322549 (44 tasks, `--array=0-43%2`, partition `rtx4060ti16g`, whole nodes, at most 2 at a time; nodes c24, c40, c62 and others per `eval/x_logs/co-rw-main-322549_*.log`),
  excluded nodes c0 c1 c2 c21 c22 c23 c34 c37 c46 c54. `CUDA_HOME=/usr/local/cuda-13.4` for the recordings (as instructed). The T21b/T21c `recall_job.sh` defaulted to `/usr/local/cuda-13.3`
  for the recordings; their attribution used 13.3 or 13.4 depending on the node (33 / 21 of the 54 recall attrib files name 13.3 / 13.4; 19 / 1 of the 20 T21c ones).
- Tool timeouts: 0 of the 72 runs (the 5,400 s pass for timeouts therefore had nothing to run).
- Analysis errors: 7 runs ended `ERROR analysis-timeout=3600s` (amrex-1 buggy/fixed: 1,246/1,452 kernel JSONs; hecbench-hungarian-1 buggy/fixed: 7,066/6,964; raft-1 buggy/fixed: 4 kernel JSONs each;
  colmap-new-1 buggy: 7 kernel JSONs), the same ids whose scalar-clock analysis needed the long runs in T21b/T21c. They are re-analysed from the stored recordings with a 82,800 s analysis timeout
  (`co_rean.sh`, CPU jobs 322934-322940, T21c's procedure for colmap-new-1). Five finished and amrex-1 x2 did not (rows `baselines-cuvein-shardrean-*`, scored below; the scoring uses the re-analysis row where the first row is ERROR);
  amrex-1 buggy/fixed ended ERROR at 82,800 s and stay NOT-SCORED, not MISSED (the scorer's own label for them is MISSED with cause m4).
- Not run, per the brief: lightgbm-new-1, lightgbm-new-2 (scalar-clock analysis did not finish in 23 h), llamacpp-open-2 buggy and fixed (deprioritised).
- Comparison runs are the existing T21b (`eval/results/realworld`, scalar-clock and vector-clock) and T21c (`eval/results/realworld_t21c`, scalar-clock) results, not re-run.
- Files: `eval/COLLECTOR_ONLY_REALWORLD.csv` (the recall table's source format, `recall.csv` columns, both sets), `eval/results/realworld_co/` and `eval/results/realworld_co_t21c/` (per-id CSVs, `attrib/`, `recall.csv`,
  `other_reports.csv`, `co_only.csv`, `perf.csv`), logs `eval/x_logs/co-*`.

## 1. Recall set (T21b: 28 targets, buggy and fixed builds)

Outcome per target and component, collector-only (CO) next to scalar-clock (SC) and vector-clock (VC) from the T21b run (`eval/results/realworld/recall.csv`, same oracle pairs `recall_pairs.json`). DET-as-DR = detected as the other class; RESIDUAL = residual as registered; STILL = pair still reported on the fixed build; NOT-SCORED = the run ended ERROR (see 5).

| target | variant | comp | CO | SC | VC | CO n_race/n_sc | CO run |
|---|---|---|---|---|---|---|---|
| amrex-1 | buggy | DR | NOT-SCORED (analysis timeout at 82,800 s) | MISSED | MISSED | / | ERROR |
| amrex-1 | fixed | - | NOT-SCORED (analysis timeout at 82,800 s) | - | - | / | ERROR |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 65/0 | RACE |
| bitsandbytes-1 | fixed | - | CLEAN | CLEAN | CLEAN | 64/0 | RACE |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 12/0 | RACE |
| cccl-1 | fixed | - | STILL | STILL | STILL | 12/0 | RACE |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED | 454/0 | RACE |
| cccl-2 | fixed | - | CLEAN | CLEAN | CLEAN | 447/0 | RACE |
| cccl-3 | buggy | DR | MISSED | DETECTED | DETECTED | 36/8 | RACE |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED | 36/8 | RACE |
| cccl-3 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | 36/8 | RACE |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED | 1/4 | RACE |
| cccl-4 | fixed | - | CLEAN | CLEAN | CLEAN | 0/5 | CLEAN |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 3/0 | RACE |
| cmssw-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | 0/3 | CLEAN |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 15/0 | RACE |
| ginkgo-1 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| ginkgo-5 | buggy | DR | MISSED | DETECTED | DETECTED | 3/0 | RACE |
| ginkgo-5 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 92/0 | RACE |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | 3/0 | RACE |
| hecbench-hungarian-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | 235/239 | RACE |
| hecbench-hungarian-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | 235/250 | RACE |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 8/0 | RACE |
| hecbench-morphology-1 | fixed | - | CLEAN | CLEAN | CLEAN | 8/0 | RACE |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 14/0 | RACE |
| hecbench-surfel-1 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| kokkos-5 | buggy | DR | MISSED | DETECTED | DETECTED | 19/0 | RACE |
| kokkos-5 | fixed | - | RESIDUAL | CLEAN | CLEAN | 23/0 | RACE |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED | 32/0 | RACE |
| kokkos-6 | fixed | - | CLEAN | CLEAN | CLEAN | 26/0 | RACE |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 6/0 | RACE |
| lit-arrayfire-1 | fixed | - | CLEAN | CLEAN | CLEAN | 4/0 | RACE |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 84/0 | RACE |
| lit-exllamav3-1 | fixed | - | CLEAN | CLEAN | CLEAN | 64/0 | RACE |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 1/0 | RACE |
| lit-fbgemm-1 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 22/0 | RACE |
| lit-shoc-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | 22/0 | RACE |
| lit-shoc-1 | fixed | - | CLEAN | CLEAN | CLEAN | 10/0 | RACE |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED | 8/0 | RACE |
| llamacpp-2 | fixed | - | STILL | CLEAN | CLEAN | 8/0 | RACE |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED | 1/0 | RACE |
| llamacpp-4 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED | 1032/0 | RACE |
| llamacpp-5 | fixed | - | CLEAN | CLEAN | CLEAN | 768/0 | RACE |
| opencv-2 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | 105/0 | RACE |
| opencv-2 | fixed | - | CLEAN | CLEAN | CLEAN | 8/0 | RACE |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 3/0 | RACE |
| pytorch-1 | fixed | - | STILL | CLEAN | CLEAN | 3/0 | RACE |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED | 1/0 | RACE |
| pytorch-3 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED | 2/0 | RACE |
| pytorch-4 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | 1/0 | RACE |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED | 12/0 | RACE |
| pytorch_cluster-1 | fixed | - | CLEAN | CLEAN | CLEAN | 0/0 | CLEAN |
| raft-1 | buggy | DR | MISSED | DETECTED | DETECTED | 24/1 | RACE |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED | 24/1 | RACE |
| raft-1 | fixed | - | RESIDUAL | RESIDUAL | NOT-SCORED | 22/1 | RACE |

- collector-only: buggy DETECTED (23); buggy DETECTED-AS-DR (3); buggy MISSED (4); buggy NOT-SCORED (analysis timeout at 82,800 s) (1); fixed CLEAN-FOR-PAIR (17); fixed RESIDUAL-AS-EXPECTED (7); fixed STILL-REPORTED (3); fixed NOT-SCORED (analysis timeout at 82,800 s) (1)
- scalar-clock: buggy DETECTED (27); buggy DETECTED-AS-DR (3); buggy MISSED (1); fixed CLEAN-FOR-PAIR (20); fixed RESIDUAL-AS-EXPECTED (6); fixed STILL-REPORTED (1)
- vector-clock: buggy DETECTED (27); buggy DETECTED-AS-DR (3); buggy MISSED (1); fixed CLEAN-FOR-PAIR (20); fixed NOT-SCORED (1); fixed RESIDUAL-AS-EXPECTED (5); fixed STILL-REPORTED (1)

## 2. Candidate set (T21c)

| id | comp | expected | CO | CO class reported | SC (T21c) | CO n_race/n_sc |
|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | 128 RACE / 0 SC | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | 272 RACE / 0 SC | DETECTED | 272/0 |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | 56 RACE / 24 SC | DETECTED | 56/24 |
| droidslam-new-1-buggy | SC | SC | DET-as-DR | 21 RACE / 0 SC | DET-as-DR | 21/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | 17 RACE / 0 SC | DETECTED | 17/0 |
| llmc-new-1-buggy | DR | DR | DETECTED | 8 RACE / 0 SC | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | 1 RACE / 0 SC | DETECTED | 1/0 |
| llmc-new-3-buggy | DR | DR | DETECTED(fam) | 2 RACE / 0 SC | DETECTED(fam) | 2/0 |
| llmc-new-3-k8-buggy | DR | DR | DETECTED | 9 RACE / 0 SC | DETECTED | 9/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | 2 RACE / 0 SC | DETECTED | 2/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | 64 RACE / 0 SC | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DET-as-DR | 64 RACE / 0 SC | DET-as-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | 3 RACE / 0 SC | DETECTED | 3/0 |
| pcl-new-1-buggy | DR | DR+SC | MISSED | 136 RACE / 0 SC | DETECTED | 136/0 |
| pcl-new-1-buggy | SC | DR+SC | DET-as-DR | 136 RACE / 0 SC | DET-as-DR | 136/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | 1 RACE / 0 SC | DETECTED | 1/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | 14 RACE / 0 SC | DETECTED | 14/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | 1 RACE / 0 SC | DETECTED | 1/0 |
| lightgbm-new-1-buggy | | | not scored | | - | not run: analysis did not finish in 23 h under scalar-clock (Jeffery's decision) |
| lightgbm-new-2-buggy | | | not scored | | - | not run: analysis did not finish in 23 h under scalar-clock (Jeffery's decision) |
| llamacpp-open-2-buggy | | | not scored | | MISSED | not run: deprioritised (Jeffery) |
| llamacpp-open-2-fixed | | | not scored | | CLEAN | not run: deprioritised (Jeffery) |

## 3. Reports on the buggy builds

Other reports = reports no oracle pair, registered residual or both-builds pair explains (the scorer's `other_reports.csv`, deduplicated pc pairs), buggy builds.

| target | CO other | SC other |
|---|---|---|
| bitsandbytes-1 | 64 | 0 |
| cccl-2 | 360 | 0 |
| cccl-3 | 36 | 25 |
| cccl-4 | 4 | 9 |
| cmssw-1 | 1 | 2 |
| colmap-new-1 | 116 | 0 |
| cuml-tsne-new-1 | 79 | 91 |
| droidslam-new-1 | 6 | 7 |
| ginkgo-5 | 3 | 3 |
| hecbench-dxtc2-1 | 40 | 49 |
| hecbench-hungarian-1 | 470 | 525 |
| hecbench-morphology-1 | 4 | 4 |
| kokkos-5 | 4 | 2 |
| kokkos-6 | 26 | 12 |
| lit-arrayfire-1 | 4 | 0 |
| lit-exllamav3-1 | 21 | 1 |
| lit-shoc-1 | 12 | 40 |
| llamacpp-2 | 6 | 0 |
| llamacpp-5 | 1024 | 256 |
| llamacpp-open-1 | 16 | 0 |
| llmc-new-1 | 4 | 4 |
| opencv_contrib-new-1 | 9 | 9 |
| pcl-new-1 | 43 | 381 |
| pytorch-1 | 2 | 0 |
| raft-1 | 24 | 19 |
| **total** | **2378** | **1439** |

### Reports collector-only makes and scalar-clock does not (same target, buggy build)

Key = (kernel, unordered pc pair, space), over all reports of both modes (RACE and SC verdicts), attributed runs only.

| id | CO reports | SC reports | both | CO only | SC only | note |
|---|---|---|---|---|---|---|
| amrex-1-buggy |  |  |  |  |  | no collector-only attribution |
| bitsandbytes-1-buggy | 65 | 1 | 1 | 64 | 0 |  |
| cccl-1-buggy | 12 | 30 | 12 | 0 | 18 |  |
| cccl-2-buggy | 454 | 128 | 89 | 365 | 39 |  |
| cccl-3-buggy | 44 | 41 | 20 | 24 | 21 |  |
| cccl-4-buggy | 5 | 11 | 5 | 0 | 6 |  |
| cmssw-1-buggy | 3 | 7 | 3 | 0 | 4 |  |
| ginkgo-1-buggy | 15 | 15 | 15 | 0 | 0 |  |
| ginkgo-5-buggy | 3 | 6 | 3 | 0 | 3 |  |
| hecbench-dxtc2-1-buggy | 92 | 111 | 89 | 3 | 22 |  |
| hecbench-hungarian-1-buggy | 474 | 539 | 454 | 20 | 85 |  |
| hecbench-morphology-1-buggy | 8 | 8 | 8 | 0 | 0 |  |
| hecbench-surfel-1-buggy | 14 | 8 | 8 | 6 | 0 |  |
| kokkos-5-buggy | 19 | 16 | 11 | 8 | 5 |  |
| kokkos-6-buggy | 32 | 18 | 18 | 14 | 0 |  |
| lit-arrayfire-1-buggy | 6 | 2 | 2 | 4 | 0 |  |
| lit-exllamav3-1-buggy | 84 | 43 | 43 | 41 | 0 |  |
| lit-fbgemm-1-buggy | 1 | 1 | 1 | 0 | 0 |  |
| lit-shoc-1-buggy | 22 | 50 | 20 | 2 | 30 |  |
| llamacpp-2-buggy | 8 | 2 | 2 | 6 | 0 |  |
| llamacpp-4-buggy | 1 | 1 | 1 | 0 | 0 |  |
| llamacpp-5-buggy | 1032 | 264 | 264 | 768 | 0 |  |
| opencv-2-buggy | 105 | 411 | 105 | 0 | 306 |  |
| pytorch-1-buggy | 3 | 1 | 1 | 2 | 0 |  |
| pytorch-3-buggy | 1 | 2 | 1 | 0 | 1 |  |
| pytorch-4-buggy | 2 | 2 | 2 | 0 | 0 |  |
| pytorch_cluster-1-buggy | 12 | 12 | 12 | 0 | 0 |  |
| raft-1-buggy | 25 | 24 | 14 | 11 | 10 |  |
| autogptq-new-1-buggy | 128 | 112 | 112 | 16 | 0 |  |
| colmap-new-1-buggy | 272 | 504 | 156 | 116 | 348 |  |
| cuml-tsne-new-1-buggy | 80 | 95 | 78 | 2 | 17 |  |
| droidslam-new-1-buggy | 21 | 67 | 21 | 0 | 46 |  |
| lightgbm-new-1-buggy |  |  |  |  |  | not run (excluded by the brief) |
| lightgbm-new-2-buggy |  |  |  |  |  | not run (excluded by the brief) |
| llamacpp-open-1-buggy | 17 | 1 | 1 | 16 | 0 |  |
| llamacpp-open-2-buggy |  |  |  |  |  | not run (excluded by the brief) |
| llmc-new-1-buggy | 8 | 8 | 8 | 0 | 0 |  |
| llmc-new-2-buggy | 1 | 1 | 1 | 0 | 0 |  |
| llmc-new-3-buggy | 2 | 2 | 2 | 0 | 0 |  |
| llmc-new-3-k8-buggy | 9 | 8 | 8 | 1 | 0 |  |
| mmcv-fps-new-1-buggy | 2 | 2 | 2 | 0 | 0 |  |
| opencv_contrib-new-1-buggy | 64 | 64 | 64 | 0 | 0 |  |
| openpcdet-fps-new-1-buggy | 3 | 3 | 3 | 0 | 0 |  |
| pcl-new-1-buggy | 136 | 657 | 136 | 0 | 521 |  |
| pointnet2pt-fps-new-1-buggy | 1 | 1 | 1 | 0 | 0 |  |
| pytorch_cluster-new-1-buggy | 14 | 14 | 14 | 0 | 0 |  |
| sglang-open-1-buggy | 1 | 1 | 1 | 0 | 0 |  |

CO-only reports: 1489.

Shape between the two pcs (definitions in `harness/co_diff.py`) against the scalar-clock verdict for the same pair (read from the scalar-clock kernel JSONs of the same kernel):

| shape | CO-only reports | SC: ORDERED (barrier-ordered) | SC: ORDERED (other) | SC: RACE/SC | SC: no verdict for the pair |
|---|---|---|---|---|---|
| loop around the barrier | 214 | 214 | 0 | 0 | 0 |
| warp barrier between | 0 | 0 | 0 | 0 | 0 |
| exit before the barrier | 532 | 532 | 0 | 0 | 0 |
| barrier on one branch | 66 | 55 | 1 | 0 | 10 |
| other | 677 | 669 | 8 | 0 | 0 |
| **total** | **1489** | 1470 | 9 | 0 | 10 |

Per target:

| id | CO-only | loop around the barrier | warp barrier between | exit before the barrier | barrier on one branch | other | SC barrier-ordered |
|---|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | 16 | 0 | 0 | 0 | 0 | 16 | 16 |
| bitsandbytes-1-buggy | 64 | 64 | 0 | 0 | 0 | 0 | 64 |
| cccl-2-buggy | 365 | 0 | 0 | 5 | 0 | 360 | 365 |
| cccl-3-buggy | 24 | 0 | 0 | 1 | 17 | 6 | 18 |
| colmap-new-1-buggy | 116 | 116 | 0 | 0 | 0 | 0 | 116 |
| cuml-tsne-new-1-buggy | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| hecbench-dxtc2-1-buggy | 3 | 0 | 0 | 0 | 0 | 3 | 3 |
| hecbench-hungarian-1-buggy | 20 | 0 | 0 | 0 | 20 | 0 | 10 |
| hecbench-surfel-1-buggy | 6 | 6 | 0 | 0 | 0 | 0 | 6 |
| kokkos-5-buggy | 8 | 0 | 0 | 0 | 0 | 8 | 8 |
| kokkos-6-buggy | 14 | 4 | 0 | 0 | 0 | 10 | 14 |
| lit-arrayfire-1-buggy | 4 | 4 | 0 | 0 | 0 | 0 | 4 |
| lit-exllamav3-1-buggy | 41 | 10 | 0 | 11 | 20 | 0 | 41 |
| lit-shoc-1-buggy | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| llamacpp-2-buggy | 6 | 6 | 0 | 0 | 0 | 0 | 6 |
| llamacpp-5-buggy | 768 | 0 | 0 | 512 | 0 | 256 | 768 |
| llamacpp-open-1-buggy | 16 | 0 | 0 | 0 | 0 | 16 | 16 |
| llmc-new-3-k8-buggy | 1 | 0 | 0 | 1 | 0 | 0 | 1 |
| pytorch-1-buggy | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| raft-1-buggy | 11 | 0 | 0 | 2 | 9 | 0 | 10 |

## 4. Slowdown and peak RSS (one rep per id; slowdown = tool wall / native wall)

| id | CO verdict | CO wall s | native s | CO slowdown | CO peak MB | SC slowdown | SC peak MB | VC slowdown | VC peak MB |
|---|---|---|---|---|---|---|---|---|---|
| amrex-1-buggy | ERROR | 38.5 | 1.0 | 39.3 | 1297.8 | 124.2 | 27608.7 | 2109.0 | 14795.0 |
| amrex-1-fixed | ERROR | 39.6 | 0.8 | 50.0 | 1297.0 | 28.9 | 27458.1 | 313.6 | 10800.8 |
| autogptq-new-1-buggy | RACE | 1.1 | 0.3 | 4.2 | 845.5 | 5.2 | 942.1 |  |  |
| bitsandbytes-1-buggy | RACE | 2.9 | 0.5 | 5.8 | 861.2 | 12.4 | 897.8 | 32.3 | 877.1 |
| bitsandbytes-1-fixed | RACE | 1.9 | 0.5 | 4.0 | 863.6 | 7.6 | 894.8 | 11.3 | 876.1 |
| cccl-1-buggy | RACE | 1.8 | 0.3 | 5.7 | 850.3 | 6.9 | 845.4 | 7.5 | 850.3 |
| cccl-1-fixed | RACE | 1.5 | 0.3 | 5.0 | 846.4 | 7.1 | 858.3 | 6.6 | 850.3 |
| cccl-2-buggy | RACE | 1.9 | 0.3 | 6.0 | 852.1 | 7.0 | 855.1 | 7.9 | 852.8 |
| cccl-2-fixed | RACE | 2.0 | 0.3 | 6.3 | 849.2 | 7.3 | 855.1 | 7.3 | 851.9 |
| cccl-3-buggy | RACE | 2.4 | 0.5 | 4.8 | 862.6 | 8.2 | 981.3 | 13.2 | 959.9 |
| cccl-3-fixed | RACE | 2.1 | 0.3 | 7.0 | 863.2 | 9.8 | 976.4 | 21.8 | 959.1 |
| cccl-4-buggy | RACE | 1.9 | 0.4 | 5.3 | 850.6 | 6.9 | 870.5 | 7.9 | 856.6 |
| cccl-4-fixed | CLEAN | 1.6 | 0.3 | 5.4 | 850.6 | 7.5 | 900.2 | 8.4 | 856.6 |
| cmssw-1-buggy | RACE | 1.5 | 0.3 | 5.2 | 849.7 | 7.7 | 1025.1 | 8.4 | 873.3 |
| cmssw-1-fixed | CLEAN | 1.6 | 0.3 | 5.5 | 848.4 | 6.9 | 1024.1 | 8.2 | 871.0 |
| colmap-new-1-buggy | ERROR | 2.3 | 0.4 | 6.3 | 948.8 | 38.3 | 1177.1 |  |  |
| cuml-tsne-new-1-buggy | RACE | 2.0 | 0.4 | 5.4 | 873.0 | 8.5 | 1012.4 |  |  |
| droidslam-new-1-buggy | RACE | 1.6 | 0.3 | 4.7 | 847.4 | 5.8 | 870.7 |  |  |
| ginkgo-1-buggy | RACE | 1.6 | 0.3 | 5.7 | 849.4 | 4.6 | 759.5 | 7.2 | 850.8 |
| ginkgo-1-fixed | CLEAN | 1.8 | 0.3 | 6.1 | 848.5 | 5.8 | 859.6 | 7.3 | 849.4 |
| ginkgo-5-buggy | RACE | 1.9 | 0.6 | 3.1 | 1109.7 | 1.9 | 1057.8 | 3.6 | 1098.4 |
| ginkgo-5-fixed | CLEAN | 1.5 | 0.4 | 4.1 | 1105.6 | 6.3 | 1058.5 | 7.6 | 1040.5 |
| hecbench-dxtc2-1-buggy | RACE | 1.7 | 0.8 | 2.1 | 848.1 | 8.4 | 874.1 | 12.8 | 862.0 |
| hecbench-dxtc2-1-fixed | RACE | 1.7 | 0.4 | 4.1 | 847.2 | 5.7 | 872.6 | 6.0 | 860.6 |
| hecbench-hungarian-1-buggy | ERROR | 85.6 | 0.6 | 150.1 | 853.1 | 196.7 | 870.6 | 192.1 | 853.2 |
| hecbench-hungarian-1-fixed | ERROR | 86.3 | 0.8 | 113.7 | 854.9 | 216.1 | 873.1 | 193.3 | 843.0 |
| hecbench-morphology-1-buggy | RACE | 2.4 | 0.5 | 5.3 | 851.8 | 10.5 | 934.4 | 15.5 | 898.6 |
| hecbench-morphology-1-fixed | RACE | 2.3 | 0.5 | 5.1 | 852.1 | 9.8 | 935.5 | 15.5 | 900.7 |
| hecbench-surfel-1-buggy | RACE | 2.3 | 0.5 | 4.9 | 848.9 | 7.3 | 874.9 | 8.3 | 865.8 |
| hecbench-surfel-1-fixed | CLEAN | 2.0 | 0.6 | 3.2 | 852.8 | 8.1 | 878.8 | 10.4 | 865.8 |
| kokkos-5-buggy | RACE | 3.0 | 0.5 | 6.5 | 850.6 | 4.2 | 967.8 | 6.0 | 889.9 |
| kokkos-5-fixed | RACE | 1.9 | 0.3 | 6.2 | 850.0 | 7.1 | 972.6 | 8.3 | 891.8 |
| kokkos-6-buggy | RACE | 2.4 | 0.4 | 6.0 | 852.7 | 5.2 | 969.4 | 8.6 | 890.8 |
| kokkos-6-fixed | RACE | 1.8 | 0.4 | 4.8 | 852.7 | 6.6 | 966.9 | 9.0 | 891.9 |
| lit-arrayfire-1-buggy | RACE | 2.4 | 0.3 | 7.2 | 849.5 | 7.3 | 876.7 | 8.2 | 854.2 |
| lit-arrayfire-1-fixed | RACE | 2.0 | 0.3 | 6.1 | 848.2 | 7.3 | 873.9 | 8.0 | 852.3 |
| lit-exllamav3-1-buggy | RACE | 3.0 | 0.3 | 8.9 | 849.7 | 7.9 | 865.7 | 11.2 | 852.4 |
| lit-exllamav3-1-fixed | RACE | 2.1 | 0.4 | 5.0 | 849.8 | 7.3 | 865.7 | 11.1 | 852.4 |
| lit-fbgemm-1-buggy | RACE | 2.8 | 0.5 | 5.9 | 851.1 | 6.7 | 904.8 | 7.7 | 861.6 |
| lit-fbgemm-1-fixed | CLEAN | 2.1 | 0.4 | 4.9 | 851.2 | 7.3 | 908.4 | 8.0 | 862.4 |
| lit-shoc-1-buggy | RACE | 4.1 | 0.3 | 13.6 | 860.2 | 10.6 | 909.6 | 14.4 | 881.7 |
| lit-shoc-1-fixed | RACE | 1.9 | 0.5 | 3.6 | 857.9 | 7.6 | 912.4 | 11.0 | 881.8 |
| llamacpp-2-buggy | RACE | 2.7 | 1.4 | 1.9 | 1117.3 | 3.6 | 2189.0 | 0.9 | 1311.2 |
| llamacpp-2-fixed | RACE | 2.2 | 1.5 | 1.5 | 1122.0 | 22.7 | 2181.9 | 7.9 | 1324.8 |
| llamacpp-4-buggy | RACE | 2.2 | 2.1 | 1.1 | 1102.0 | 12.3 | 2005.7 | 2.3 | 1162.3 |
| llamacpp-4-fixed | CLEAN | 1.9 | 1.5 | 1.3 | 1103.9 | 34.0 | 2006.1 | 6.2 | 1161.5 |
| llamacpp-5-buggy | RACE | 2.8 | 1.5 | 1.9 | 1102.3 | 22.4 | 2071.8 | 8.0 | 1150.6 |
| llamacpp-5-fixed | RACE | 1.8 | 1.5 | 1.2 | 1104.3 | 27.8 | 2015.0 | 5.7 | 1146.7 |
| llamacpp-open-1-buggy | RACE | 4.0 | 1.3 | 3.0 | 1124.1 | 20.3 | 2182.7 |  |  |
| llmc-new-1-buggy | RACE | 2.0 | 0.4 | 5.1 | 1118.0 | 7.8 | 1491.5 |  |  |
| llmc-new-2-buggy | RACE | 1.4 | 0.3 | 4.6 | 850.6 | 4.9 | 953.9 |  |  |
| llmc-new-3-buggy | RACE | 1.9 | 0.4 | 5.2 | 1135.2 | 6.0 | 1340.2 |  |  |
| llmc-new-3-k8-buggy | RACE | 1.9 | 0.4 | 5.2 | 1145.4 | 6.3 | 1269.8 |  |  |
| mmcv-fps-new-1-buggy | RACE | 2.1 | 0.4 | 5.0 | 946.4 | 7.0 | 1119.8 |  |  |
| opencv-2-buggy | RACE | 1.6 | 0.3 | 5.5 | 850.3 | 7.5 | 866.4 | 11.2 | 854.7 |
| opencv-2-fixed | RACE | 1.4 | 0.3 | 4.8 | 848.9 | 9.9 | 866.8 | 8.4 | 848.5 |
| opencv_contrib-new-1-buggy | RACE | 6.7 | 0.3 | 21.7 | 851.7 | 6.2 | 876.0 |  |  |
| openpcdet-fps-new-1-buggy | RACE | 2.8 | 0.3 | 8.5 | 851.9 | 10.7 | 939.7 |  |  |
| pcl-new-1-buggy | RACE | 1.6 | 0.3 | 5.2 | 864.9 | 4.9 | 1018.8 |  |  |
| pointnet2pt-fps-new-1-buggy | RACE | 1.5 | 0.3 | 5.7 | 851.2 | 18.4 | 906.4 |  |  |
| pytorch-1-buggy | RACE | 1.6 | 0.5 | 3.3 | 857.1 | 7.3 | 891.9 | 9.8 | 867.4 |
| pytorch-1-fixed | RACE | 1.7 | 0.4 | 4.0 | 852.3 | 8.0 | 893.3 | 8.4 | 867.4 |
| pytorch-3-buggy | RACE | 1.6 | 0.3 | 5.5 | 851.4 | 9.0 | 862.7 | 8.3 | 853.2 |
| pytorch-3-fixed | CLEAN | 4.6 | 0.3 | 13.2 | 849.4 | 7.3 | 862.7 | 10.9 | 855.2 |
| pytorch-4-buggy | RACE | 1.6 | 0.7 | 2.4 | 865.0 | 10.6 | 946.9 | 9.8 | 875.7 |
| pytorch-4-fixed | RACE | 1.6 | 0.4 | 4.4 | 864.2 | 5.0 | 957.1 | 6.0 | 874.9 |
| pytorch_cluster-1-buggy | RACE | 1.7 | 0.3 | 5.6 | 848.4 | 11.8 | 867.6 | 14.5 | 856.6 |
| pytorch_cluster-1-fixed | CLEAN | 3.8 | 0.3 | 12.4 | 848.4 | 7.1 | 868.4 | 7.5 | 851.1 |
| pytorch_cluster-new-1-buggy | RACE | 1.2 | 0.3 | 4.1 | 848.7 | 6.0 | 962.8 |  |  |
| raft-1-buggy | ERROR | 3.7 | 0.4 | 8.8 | 879.9 | 5.1 | 1057.4 | 10.0 | 940.0 |
| raft-1-fixed | ERROR | 2.0 | 0.4 | 4.6 | 878.7 | 7.1 | 1047.2 | 13.9 | 941.2 |
| sglang-open-1-buggy | RACE | 1.3 | 0.3 | 4.7 | 848.2 | 4.9 | 983.5 |  |  |

Median slowdown over the 65 CO runs that ended RACE/CLEAN: 5.1x (min 1.1x, max 21.7x); median SC slowdown over the 65 ids where both ended RACE/CLEAN: 7.3x.


## 5. Open and missing numbers

- NOT-SCORED rows: amrex-1 buggy and fixed (analysis timeout at 3,600 s; long re-analysis with a 82,800 s analysis timeout also ended ERROR, jobs 322934/322935, then 24 h job limit). Their report counts, other-report counts, CO-only reports and shapes are absent from sections 1-3.
- 10 CO-only pairs of hecbench-hungarian-1 buggy have "no verdict" for the scalar-clock side: the lookup scans at most 40 scalar-clock kernel JSONs of the kernel (the recording has 7,066) and found none that judges the pair.
- Slowdown/peak RSS rows of the 5 re-analysed ids show the verdict of the first (ERROR) row; the tool wall and RSS are those of the recording, which the re-analysis does not change.
- Not run: lightgbm-new-1, lightgbm-new-2, llamacpp-open-2 (buggy, fixed).
- Peak RSS is `blib.run_timed(poll_mem=True)` (the summed VmRSS poll X1b used); the T21b/T21c columns are the same measurement from their runs. Slowdown = tool wall / native wall of the same id, one rep each,
  so the 1-3 s runs are start-up dominated.

## 6. Method notes for sections 3

- "Report" = a deduplicated (kernel, unordered pc pair, space) with verdict RACE or SC from `rw_attribute.py`, which re-runs `sync_dominance.analyze` on every stored kernel JSON of the mode
  (collector-only JSONs carry no `hb_*` key).
- CO-only = in the collector-only report set, not in the scalar-clock set of the same id (T21b/T21c attrib files). SC-only (columns "SC only") = the reverse; those are not triaged.
- Shape (`co_diff.py`, first match in the order of the table): loop around the barrier = a block barrier lies on every path between the pcs but a loop's wrap-around path skips it, or a block barrier lies on
  every cycle through the region of either pc; warp barrier between = no block barrier between, a WARPSYNC between (or on every cycle); exit before the barrier = a block barrier is reachable from a pc and that
  pc reaches EXIT on a path with no block barrier; barrier on one branch = a block barrier lies on some path between the pcs but not on every path; other = none of these.
- "SC verdict for the pair" = `sync_dominance.analyze` (installed rules) on the scalar-clock kernel JSONs of the same kernel in the T21b/T21c store: ORDERED with `hb_class=barrier-ordered` means the
  scalar-clock barrier-only pass found no pair of conflicting instances of these two pcs unordered by a barrier in that run. This is the answer to "ordered by a barrier instance in the run" for the
  CO-only reports; it is a statement about the recorded run, not a proof for other schedules. The scalar-clock event stream was recorded with `BASELINE_HB_DUMP=0` (aggregates), so the individual barrier
  instances are not re-derived here.

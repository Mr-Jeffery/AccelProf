# T21a step 4 - fresh-context review of the 50 pre-registered oracles

Four fresh-context Opus reviewers (one per group below, run 2026-10-20 by the coordinating session) each read only the oracle
files, the T21 definitions in CLAUDE.md (the corpus section, T21a step 4, D19-D22), `targets.jsonl` for repos, commits
and paths, and the upstream sources at the exact commits (partial clones under `~/incoming/realworld/`; for R2 the
harness copies, checked byte-identical to `git show`). They did not read `eval/REALWORLD.md`, the racecheck output or
build logs. Each file now carries a `review` object (verdict, every change with old value, reason and file:line
evidence); the 22 source-derived drafts also gained `line_basis` on each site. No pre-registered pair was rejected.

Verdicts: 32 confirmed, 18 corrected, 0 rejected.
Fields listed are those whose content changed (ignoring the added `line_basis`).

**Not re-checked by the reviewers:** every SASS statement (opcodes, `.STRONG` tokens, WARPSYNC/NOP) in the oracles is
the builder's; the reviewers' `srun -p normal` jobs could not start (partition full, estimated start 2026-10-21) and were
withdrawn. Access widths were checked from source types.

| id | reviewer group | verdict | changed fields | depends on D20 |
|---|---|---|---|---|
| amrex-1 | C (wave 2, R1/R1h) | corrected | `thread_relation`, `extra_pairs` (new) | no |
| autogptq-new-1 | D (candidates, wave 3) | confirmed | none | no |
| bitsandbytes-1 | B (R2) | confirmed | none | no |
| cccl-1 | A (wave 1, R1/R1h) | confirmed | none | no |
| cccl-2 | A (wave 1, R1/R1h) | corrected | `thread_pair_example`, `open_questions` | no |
| cccl-3 | A (wave 1, R1/R1h) | corrected | `fixed` | yes |
| cccl-4 | A (wave 1, R1/R1h) | confirmed | none | no |
| cmssw-1 | B (R2) | corrected | `sites`, `thread_pair_example` | no |
| colmap-new-1 | D (candidates, wave 3) | confirmed | none | no |
| cudf-3 | D (candidates, wave 3) | confirmed | none | no |
| cudf-5 | D (candidates, wave 3) | confirmed | none | no |
| cudf-9 | D (candidates, wave 3) | confirmed | none | no |
| cuml-tsne-new-1 | D (candidates, wave 3) | corrected | `sites` | no |
| droidslam-new-1 | D (candidates, wave 3) | confirmed | none | yes |
| ginkgo-1 | C (wave 2, R1/R1h) | confirmed | none | no |
| ginkgo-5 | C (wave 2, R1/R1h) | corrected | `open_questions` | no |
| hecbench-dxtc2-1 | A (wave 1, R1/R1h) | confirmed | none | no |
| hecbench-hungarian-1 | A (wave 1, R1/R1h) | confirmed | none | yes |
| hecbench-morphology-1 | A (wave 1, R1/R1h) | corrected | `thread_pair_example` | no |
| hecbench-surfel-1 | A (wave 1, R1/R1h) | confirmed | none | no |
| kokkos-5 | C (wave 2, R1/R1h) | corrected | `thread_pair_example`, `fixed`, `extra_pairs_both_builds` (new) | no |
| kokkos-6 | C (wave 2, R1/R1h) | confirmed | none | no |
| lightgbm-new-1 | D (candidates, wave 3) | confirmed | none | no |
| lightgbm-new-2 | D (candidates, wave 3) | confirmed | none | no |
| lit-arrayfire-1 | B (R2) | confirmed | none | no |
| lit-exllamav3-1 | B (R2) | confirmed | `open_questions` | no |
| lit-fbgemm-1 | B (R2) | confirmed | none | no |
| lit-shoc-1 | B (R2) | corrected | `open_questions` | yes |
| llamacpp-2 | A (wave 1, R1/R1h) | confirmed | none | no |
| llamacpp-4 | A (wave 1, R1/R1h) | confirmed | none | no |
| llamacpp-5 | A (wave 1, R1/R1h) | confirmed | none | no |
| llamacpp-open-1 | D (candidates, wave 3) | confirmed | none | no |
| llamacpp-open-2 | D (candidates, wave 3) | corrected | `upstream_status` | no |
| llmc-new-1 | D (candidates, wave 3) | corrected | `sites`, `thread_pair_example`, `buggy_expected`, `sites_llmc_layernorm_cuh` (new) | no |
| llmc-new-2 | D (candidates, wave 3) | corrected | `buggy_expected` | no |
| llmc-new-3 | D (candidates, wave 3) | corrected | `other_conflicting_accesses` | no |
| mmcv-fps-new-1 | D (candidates, wave 3) | confirmed | none | no |
| opencv-2 | B (R2) | corrected | `extra_pairs`, `open_questions` | yes |
| opencv_contrib-new-1 | D (candidates, wave 3) | confirmed | none | yes |
| openpcdet-fps-new-1 | D (candidates, wave 3) | confirmed | none | no |
| pcl-new-1 | D (candidates, wave 3) | confirmed | none | yes |
| pointnet2pt-fps-new-1 | D (candidates, wave 3) | confirmed | none | no |
| pytorch-1 | B (R2) | confirmed | none | no |
| pytorch-3 | B (R2) | confirmed | none | no |
| pytorch-4 | B (R2) | corrected | `sites`, `open_questions`, `extra_pairs` (new) | no |
| pytorch-8 | D (candidates, wave 3) | corrected | `sites`, `other_conflicting_accesses`, `open_questions` | no |
| pytorch_cluster-1 | B (R2) | corrected | `thread_pair_example`, `open_questions` | no |
| pytorch_cluster-new-1 | D (candidates, wave 3) | confirmed | none | no |
| raft-1 | C (wave 2, R1/R1h) | corrected | `fixed`, `extra_pairs` (new) | yes |
| sglang-open-1 | D (candidates, wave 3) | confirmed | none | no |

## Decisions the review leaves to Jeffery

1. **D20, and how volatile shared memory is classed** (cccl-3, droidslam-new-1, hecbench-hungarian-1, lit-shoc-1, opencv-2, opencv_contrib-new-1, pcl-new-1, raft-1). By PTX, volatile vs volatile is strong vs
   strong (SC). The builder's SASS notes say volatile *shared* accesses compile to plain `LDS`/`STS` on sm_89 with no
   `.STRONG` token (volatile global accesses keep it), so a detector using the token rule would class them DR. Decide
   whether `expected_class` follows PTX or what the detector can observe, and how SC pairs count (D20).
2. **Fixed-build ground truth: strict PTX vs the fence + counter idiom.** raft-1 (`fixed.expected` changed to residual:
   the last block's relaxed `atomicInc` has no fence after it) and cccl-3 (residual DR+SC under strict PTX) stay racy
   under strict PTX; cmssw-1's fence + atomic hand-off is likewise open. Confirm "residual", or take the idiom reading
   ("absent") for T21b. The real fixed-build residuals of hecbench-hungarian-1 (intra-step pair) and
   hecbench-dxtc2-1 (L448 scatter) need the same absent-or-DR labelling call.
3. **llamacpp-2, fixed build.** The builder reports ptxas compiled the added `__syncwarp` to a NOP (one warp per
   block), so the fixed SASS equals the buggy SASS. By source and PTX the oracle says "absent"; decide how a
   fixed-build report is scored.
4. **pytorch-8 (wave 3).** For the fp16 driver the registered L952 is dead code (moved to L991); both `cp.async` writes
   to an address come from one thread (iterator built from `thread_idx` alone), so a cross-thread-only detector cannot
   report the registered pair. Choose a scoring rule (e.g. any cross-thread report with one side an mm1 `cp.async`
   write and the other in the aliased shared union) or add an fp32 run where L952 is live.
5. **llamacpp-open-2 is fixed upstream** (99db719bdf07, 2026-10-19, adds the end-of-loop `__syncwarp`; its parent's
   fattn files equal the pinned commit). Under T21c step 1 it becomes a recall target (buggy 1b70350c, fixed 99db719b);
   its tier was left unchanged.
6. **Pairs present in both builds, unrelated to the fixes** (recorded so a fixed-build report on them is not counted
   against the target): opencv-2 (halo loads canny.cu:252-268 vs the neighbouring block's store L302/L306),
   lit-exllamav3-1 (`warp_radixsort_posf16`, L103 vs L101, ballot/shuffle only), cccl-2 (discarded items all stored
   to `items_shared[480]`, warp_exchange_smem.cuh:156), kokkos-5 (`extra_pairs_both_builds`).
7. **Smaller items:** amrex-1's `thread_relation` is now a combined string (check downstream parsing); the
   hecbench-morphology-1 driver (192x192) differs from the CLAUDE.md table (128x128), already in its `open_questions`.

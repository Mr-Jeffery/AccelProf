# T21c step 1: upstream re-check of the 18 candidates

Checked 2026-10-24 13:10 EDT on the login node (git only) by `eval/realworld/harness/t21c_recheck.py`.
For each candidate it fetched the default branch into the partial clone under `~/incoming/realworld/`,
diffed every racy file of the record between the pinned commit and the fetched tip, and read the
logs. The raw result is `recheck.json`. PR states were read from GitHub on the same day.

## Summary

| result | n | candidates |
|---|---|---|
| racy files identical at the tip: still a candidate | 15 | autogptq-new-1, colmap-new-1, pointnet2pt-fps-new-1, llmc-new-1/2/3, lightgbm-new-1/2, mmcv-fps-new-1, openpcdet-fps-new-1, opencv_contrib-new-1, pcl-new-1, droidslam-new-1, cuml-tsne-new-1, pytorch_cluster-new-1 |
| fixed upstream: becomes a recall target, moves to T21b | 1 | llamacpp-open-2 |
| a shared file changed, race not touched: still a candidate | 1 | llamacpp-open-1 |
| one of three copies fixed: still a candidate on the other two | 1 | sglang-open-1 |

In every case the pinned commit is an ancestor of the tip.

## The three that changed

**llamacpp-open-2 (the D19 anchor): fixed.** Commit `99db719bdf07f7d537431ca556a0512bf3d995b6`, PR #30573
("CUDA: fix shared-memory WAR hazard in flash_attn_ext_vec"), by Paul Mairhofer, committed
2026-10-19. It adds `ggml_cuda_syncwarp()` at the end of the KV-loop body in `fattn-vec.cuh`, after the
V accumulation that reads `KQ`. That is the fix PR 28358 proposed for this race. The commit's parent has
`fattn-vec.cuh` identical to the pinned `1b70350c`. Per step 1 this becomes a recall target
(buggy `1b70350c`, fixed `99db719b`), as `oracle/REVIEW.md` item 5 already noted. Its tier in
`targets.jsonl` is unchanged.

**llamacpp-open-1: still open.** The only change in its files is the same `fattn-vec.cuh` commit above.
`fattn-common.cuh`, which holds `quantize_q8_1_to_shared`, is identical at the tip
`3f03b17724` (2026-10-24), so the `yq32`/`yds` aliasing at head size 64 is still there.

**sglang-open-1: one copy fixed.** The record names three copies of the race (no barrier between
`prefix[tid] = ...` and the `prefix[mid]` binary search):

| copy | at tip `773cb938fe` |
|---|---|
| `kernels/aot/csrc/moe/moe_align_kernel.cu` (the registered primary, the default `sgl_kernel` build) | unchanged, still racy |
| `kernels/jit/csrc/moe/moe_align_kernel.cu` | fixed: barrier added by `e6451c1a95` (PR #45916, "[Fix] gguf: Preserve MoE routing, weighting and allocation budgets", Cheng Wan, 2026-10-23), with the comment "Publish the prefix before other threads binary-search it below" |
| `kernels/jit/csrc/lora/trtllm_lora_temp/moe_lora_merged_align_kernel.cu` | rewritten by `d0022e1df3` (PR #45681), still no barrier between the `prefix[tid]` write and the search |

The candidate stays a candidate on the AOT copy, which is what it registers.

## PR states

| PR | state on 2026-10-24 |
|---|---|
| llama.cpp #28358 (jdziat, both llama.cpp races) | closed unmerged on 2026-10-06, a draft. The research agent's reading was right, the verifier's ("open") wrong. Its race 2 landed separately as #30573; its race 1 (llamacpp-open-1) is not fixed. |
| sglang #43030 (builtin-pb, the moe_align barrier) | open, not merged, conflicts with main, last updated 2026-10-20. Its JIT moe change is now on main via #45916. |

## Record quirk

`pcl-new-1` lists two paths with a note appended (`principal_curvatures.cu (same pattern, L150-L189)`,
`fpfh.cu (L223-L298)`). The script strips the note. Both files exist at the tip and are identical.

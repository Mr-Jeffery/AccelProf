# T21c step 2: native, reach and racecheck on the candidate builds

Run 2026-10-24 15:15–15:44 EDT on c57 (RTX 4060 Ti, sm_89, CUDA 13.4 runtime, compute-sanitizer 2026.3.0)
inside GPU hold 320154 (approved by Jeffery 2026-10-24: one node, about 4 h, no detector runs).
Command: `run_gpu_phases.sh` over the 17 candidates and llamacpp-open-2 (buggy and fixed); log
`eval/x_logs/t21c-gpu-batch.log`. The node then stayed idle until the 4 h limit (19:15) because the
completion check matched its own command line; it was not used for anything else.

Results are in `native/<id>-<variant>.json` (three runs: exit codes, wall time, stdout md5),
`native/<id>-<variant>.{kernels.csv,reach}` (nsys kernel list), and `racecheck/<id>-<variant>.txt`
(`--racecheck-report all --print-limit 2000`). The pair counts below come from the displayed
hazards only, at most 2,000 per run.

| id | native rc ×3 | outputs | reach | racecheck (errors / warnings) | top racecheck pairs (displayed) | at the oracle's sites? |
|---|---|---|---|---|---|---|
| autogptq-new-1 | 0 0 0 | same | yes | 0 / 1,008 | RAW marlin_repack.cu:30,32 vs :58 | yes |
| colmap-new-1 | 0 0 0 | same | yes | 0 / 7,522 | WAR patch_match_cuda.cu:502 vs :364 | yes (L502 vs LocalRefImage::Read) |
| pointnet2pt-fps-new-1 | 0 0 0 | same | yes | 3,217 / 136 | WAR/RAW sampling_gpu.cu:112 vs :170 | yes |
| mmcv-fps-new-1 | 0 0 0 | same | yes | 4,546 / 208 | WAR/RAW furthest_point_sample_cuda_kernel.cuh:67 vs :80 | yes |
| openpcdet-fps-new-1 | 0 0 0 | same | yes | 5,759 / 44 | WAR/RAW sampling_gpu.cu:147 vs :212 | yes (batch kernel) |
| pytorch_cluster-new-1 | 0 0 0 | same | yes | 387,874 / 856,164 | WAR fps_cuda.cu:54 vs :55, :56 vs :56 | yes |
| sglang-open-1 | 0 0 0 | same | yes | 985 / 36 | RAW moe_align_kernel.cu:220 vs :233 | yes |
| droidslam-new-1 | 0 0 0 | same | yes | 0 / 18,591 | RAW/WAR droid_kernels.cu:46–51 (warpReduce) | yes |
| pcl-new-1 | 0 0 0 | same | yes | 0 / 4,465,057 | RAW warp.hpp:164,168 vs normal_3d.cu:64 | yes |
| opencv_contrib-new-1 | 0 0 0 | same | yes | 0 / 166,335 | RAW hog.cu:191,192 vs :199; :199 vs :201; :201 vs :204 | yes (volatile reduction L196–L205) |
| llmc-new-2 | 0 0 0 | same | yes | 2,105 / 348 | WAR/RAW cuda_utils.cuh:175 vs :177 | yes |
| llmc-new-3 | 0 0 0 | same | yes | 1,523 / 0, **exit 1** | WAW attention_backward.cu:651 vs :659 | yes; under racecheck the program's own check failed (`Mismatch of dpreatt`), natively it passes |
| llmc-new-1 | 0 0 0 | same | yes | n/a (global memory) | — | — |
| cuml-tsne-new-1 | 0 0 0 | **differ** | yes | 800,261 / 382 | RAW barnes_hut_kernels.cuh:122 vs :130 | **no**: the oracle names L596–L656; the 2,000 displayed are all L122/L130 |
| lightgbm-new-1 | 0 0 0 | **differ** | yes | 9,690 / 0 | WAR/RAW cuda_algorithms.hpp:131 vs :136 (ShuffleReduceSum); first hazard in `CUDARMSEMetric::MetricOnPointCUDA` | to check: the oracle names `FixHistogramKernel`, cuda_histogram_constructor.cu L762–L763 |
| lightgbm-new-2 | 0 0 0 | **differ** | yes | 15,701 / 0 | WAR/RAW cuda_algorithms.hpp:131 vs :136 | to check: the oracle names `EvalKernel`, cuda_pointwise_metric.cu L31/L39 |
| llamacpp-open-1 | 0 0 0 | same | yes | 0 / 4,569 | WAW fattn-common.cuh:365 vs :370 | yes (`yq32[threadIdx.x]` vs the `yds` store) |
| llamacpp-open-2 buggy | 0 0 0 | same | yes | **0 / 0** | — | racecheck silent |
| llamacpp-open-2 fixed | 0 0 0 | same | yes | 0 / 0 | — | — |

Notes
- Every build reaches its kernel and exits 0 natively, three times out of three.
- **llamacpp-open-2:** racecheck reports nothing on sm_89 in either build. PR 28358 reported the race with racecheck on sm_120. The build helper found that ptxas emits no `WARPSYNC` in the D=128 f16 instance of `flash_attn_ext_vec`, in either build: the fix's `__syncwarp` survives in the PTX (`bar.warp.sync`) but not in the SASS. So the fixed SASS equals the buggy SASS at the racing accesses. CLAUDE.md note 2 applies: score what the frozen detector reports.
- **cuml-tsne-new-1, lightgbm-new-1/2:** stdout differs between runs. Not yet checked whether that is timing output or results.
- **lightgbm-new-1/2:** the displayed hazards come from the shared `ShuffleReduceSum` helper. Which kernel each comes from (the oracle's kernel or a metric kernel) is for the triage (step 3).
- **cuml-tsne-new-1:** the displayed hazards are not at the oracle's lines. `--print-limit 2000` may hide them; a rerun with a filter on the kernel would decide.

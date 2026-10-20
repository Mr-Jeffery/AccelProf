# Real-world race corpus — commits and issues examined and rejected (2026-10-13)

One section per research slice. Each line is something a research agent opened and rejected, with the reason. Kept so later searches do not re-examine the same commits; also the denominator for the corpus funnel. Written by the research agents; not independently re-checked.

## ml-frameworks

### Rejected / examined-and-dropped items (ml-frameworks)
Format: repo sha-or-issue : reason

#### open-mmlab/mmcv
- mmcv 76e870f : logic/host-side bug, not a kernel data race
- mmcv 09b64a6 : logic/host-side bug, not a kernel data race
- mmcv 1a2f174 : logic/host-side bug, not a kernel data race
- mmcv f6fd6c2 : logic/host-side bug, not a kernel data race
- mmcv 0d3cdc6 : logic/host-side bug, not a kernel data race

#### pytorch/vision
- vision e395a79c1 : fix is a test/thread-count change, no kernel race
- vision 10f68dbd7 : default-stream (inter-kernel / stream) fix, out of scope
- vision 9b7c7d395 : atomicAdd determinism alert only (FP atomic order), out of scope
- vision bd4471ccc : atomicAdd determinism alert only (FP atomic order), out of scope

#### pytorch/audio
- no race-fix commits found in message grep (rnnt / forced_align)

#### facebookresearch/detectron2
- no race-fix commits found in message grep

#### pytorch/pytorch
- pytorch 45b869e3d : wrong-kernel selection bug, not a race
- pytorch issue #192304 (FuzzWarp umbrella) : out-of-bounds reads, different bug class
- pytorch 2a20f3eab : int32 index overflow, not a race
- pytorch d5b1941b0 : int32 index overflow, not a race
- pytorch 9933e59c2 : host-side (CPU thread) race
- pytorch 925131a85 : host-side (CPU thread) race
- pytorch 03c932172 : host-side (CPU thread) race
- pytorch a20c7ce84 : host-side race
- pytorch c295916af : host-side race
- pytorch d424e34e3 : CPU kernel race, not CUDA
- pytorch 27d32ac5d : NCCL / multi-GPU, out of scope
- pytorch issues #199896 #200039 #200040 #199612 #196257 : allocator / symm_mem / launcher / multi-device issues, not intra-kernel races (seen in the one open-issue search)
- GitHub PR search "racecheck syncthreads race is:open" on pytorch/pytorch : 0 results, so no open race PR to record

#### microsoft/onnxruntime
- onnxruntime 42399dfd : host-side TopK member-variable race, not a GPU kernel race

#### tensorflow/tensorflow
- tensorflow ef2f8891a : op-level buffer forwarding (inter-op aliasing), not intra-kernel
- tensorflow 50c58837d : index logic bug, not a race
- tensorflow a559acfb2 : DepthwiseConv2dBackpropInput small kernel disabled; cause not verified as a race, dropped

#### openxla/xla
- xla 03a3720d / ec1b95489 : while-thunk / thunk-level host races, out of scope
- xla 5e217196 : thunk-level host race, out of scope
- xla 1715abac ("Rewrite all reductions to race-free in MLIR mode") : not examined in depth (MLIR emitter, JIT-generated); left unchecked

#### jax-ml/jax
- jax 84a33c08 (Pallas MGPU dynamic_scheduling_loop backpressure race) : Mosaic GPU cluster-launch-control scheduling, sm_100/sm_90 only; read only the message, not recorded
- jax d0d662d2 (Blackwell collective matmul race) : needs sm_100 + clusters (distributed smem), out of scope
- (jax 0a66e2d0 recorded as jax-1, low confidence)

#### apache/mxnet
- mxnet 97daed81b : kernel rewritten with a sort-based approach using atomics, no isolated race fix

#### NVIDIA/apex
- apex 758826f : launch-config fix for a cross-block race, not a barrier fix and not unit-testable in isolation; not recorded

#### PaddlePaddle/Paddle
- Paddle b7565222 ("add syncthreads", DropOutNdForwardKernel) : the added __syncthreads sits inside a grid-stride loop with a per-thread index, only the one-line diff was read (kernel body not inspected, so unverified); the barrier sits in a per-thread loop and no shared-memory buffer is visible in the diff, so no demonstrable data race was established

## llm-inference

### Rejected / examined-and-dropped (llm-inference slice)

#### ggml-org/llama.cpp
- 5af118efdaf1098798a06b24fd8a557760e99631 (2024-09-11) "CUDA: fix --split-mode row race condition" -- diff read: host-side race on a memory-pool temp buffer shared by parallel CUDA streams (inter-stream), fixed by disabling stream-k; out of scope.
- 9e58d4d692ed3d350591cc86d06c73c61c122509 (2026-06-03) "Avoid PDL race conditions by disabling __restrict__ when PDL is used" -- Programmatic Dependent Launch (inter-kernel overlap, Hopper+ only), cross-kernel, out of scope.
- 192d8ae8b8826642f15836570b944ecd68cf175c (2026-05-26) "CUDA: missing PDL sync for FWHT" -- PDL inter-kernel, out of scope.
- 3fc4e105279105106b08a133a4e3e483116e621f / 2cd20b72 -- stream/event synchronisation between graph splits; host/inter-kernel.
- 849798132173c3c511dffe3a03c3c760d707b05f (2026-08-20) "ggml: fix backend split scheduler race condition" -- host-side scheduler.
- 05af0d2b1398394cfa67e1918fee7feabccaa9bc (2026-09-30) glm5-next "unique scatter rows" and 43fe9c64281ef735046adc025e9e7559a1f659a5 (2026-10-06) k-pool scatter race -- CPU-backend set_rows data race (ThreadSanitizer), graph construction, not a CUDA kernel.
- 481c65f091f74c5e7089dd0a3a1cc6b50cced31e (vulkan argsort), cd18a50ea573 (vulkan coopmat1), 3ea5360c00db (vulkan mul_mat_id), 3238b1400cf4 (vulkan FA), 60addddf3c56 (opencl FA tile), 3d94e967 (metal) -- not CUDA / not nvcc-compiled.
- b74f590eafec2fafc6e0e98ee93b2e5d3efa9042 (2026-09-06) "ggml-cuda: fix divergent barrier in f16 flash attention" (issue 27678, still open, synccheck "Barrier error ... Divergent thread(s)") -- barrier divergence (same __syncthreads reached by different instructions), no specific conflicting access identified; a synccheck, not racecheck, bug. Would be pattern early-exit-before-barrier but no race evidence. Dropped; see llamacpp-11 for the earlier misaligned-barrier fix which is kept at low confidence.
- e4b9af007beae34abba094cefd187658e89bbac8 (2026-08-31) "CUDA: XOR swizzle flash attn K,V smem fp16 tiles" -- feature commit; sub-bullet "fix shared memory race in FA on DGX Spark" is a fix of the PR's own new code (the `if constexpr (swz) __syncthreads()` at fattn-mma-f16.cuh L1515), not separable from the feature; buggy parent does not contain the swizzle. Dropped (could be examined via PR 25635 intermediate commits, unverified).
- 95e18884 kept (llamacpp-11, low confidence). c8771ab5f89387cdd7d9a8a69280dac46b45e02f (2024-06-26) "CUDA: fix misaligned shared memory read" -- alignment, not a race. 26a8406ba9198eb6fdd8329fa717555b4f77f05f (2024-12-09) "fix shared memory access condition for mmv" -- OOB/condition, not read in depth. 3913f8730ec6 "fix padding in timestep embedding kernels" -- OOB.
- 26546 "Out-of-bounds read in gated_delta_net_cuda on Pascal" (compute-sanitizer memcheck) -- OOB, wrong class.
- 28056 "missing sync in process_ubatch races zero-copy graph inputs against in-flight compute" -- host/inter-kernel on integrated GPUs, out of scope.
- 27102 / 27330 (CUDA watchdog hangs) -- hangs, no conflicting access identified.
- 28497 "qwen4exp indexer top-k selects a different cell set each run (CUB DeviceTopK over tied block scores)" -- tie-breaking nondeterminism in library kernel, not a race in repo code.
- 28652 CUDA graph cache key interference -- host-side.
- 76d66ee0be91e2bec93206e821ee1db8d023cff5 (2024-06-14) "CUDA: faster q2_K, q3_K MMQ + int8 tensor cores (#7921)" -- squashed feature commit; the "fix data race" is an intermediate commit inside the PR, no separate fix commit and no diff isolating it.
- 34c9d765bf173c551398f1e7fa4595019bc53bab (2025-08-09) "CUDA: add attention sinks for tile and wmma (#15178)" -- feature commit (review bullet 'remove syncthreads from tile'), not a race fix.
- d3dce4e0a (2026-01-04) "sampling : add support for backend sampling (#17004)" -- the soft_max_f32_parallelize_cols_single_row data-race fix is a sub-bullet inside a large squashed feature commit; no isolated fix. The later block_reduce fix 9bd4c09ea5 (llamacpp-4) covers that function.
- llama.cpp issue 24399 "sm_120 out-of-range shared-memory store in mul_mat_q<Q8_0,128> epilogue, intermittent crash" -- out-of-bounds store, wrong class.
- ikawrakow/ik_llama.cpp PR 2502 "CUDA: fix shared memory race in mmq_ids_helper" and 0xShug0/audio.cpp PR 837 (backport of llama.cpp #26385) -- forks / downstream copies of llamacpp-2 and llamacpp-4, repositories outside this slice.
- ggml.git / whisper.cpp.git ggml-cuda history (llama/NNNN mirror commits, e.g. ggml 7ae53f95, 3e12f441, 5f0b0e89, b1712969, 391d7449, 575d02f5, 38648430, 3c5fb16a, 6e2c0557) -- all are sync-mirrors of llama.cpp commits already recorded as llamacpp-2..13; no independent ggml/whisper.cpp race fix found; ggml-cuda in those repos is the same code.

#### vllm-project/vllm
- fe51194e2d7965149a655ca20af4f31dd668777d (2026-10-07) "[Bugfix][MiniMax-M3] Fence decode indexer shared-memory stage reuse (#60194)" -- CuTe DSL (JIT) kernel for Blackwell sm100; no sm_89/sm_90 hardware on the cluster.
- 3ecfdc377 (2025-12-29) "[ROCm][GPTQ][Bugfix] Fix GPTQ GEMM kernel output zeroing race condition (#30719)" and 4ac0d0eac (2026-10-03) ROCm RDNA3 split-K -- ROCm/HIP only.
- e6585ddb4 (2025-09-18) "Fix accuracy issue for silu_mul + nvfp4 quant fusion kernel (#24833)" -- math/precision rewrite (silu in fp32), no race.
- 369f47aa0 / 61249b177 (2025-12) "Remove (unnecessary) syncwarps" -- removal of redundant syncs, not a fix (judged from the subjects only).
- PR 28619 "fix IMA issue in certain cases of the moe marlin kernel" (issue 28220) -- illegal memory access, no racecheck evidence.
- Host-side / scheduler / multi-process race commits in vllm (many with 'race' in the subject) -- python or C++ host code, not GPU kernels.

#### flashinfer-ai/flashinfer
- 1ce02e57 (2026-10-06) "order the two-shot allreduce barrier so a growing grid cannot pass it early (#6091)", e4c7fcec (2026-07-24) "sync all sender threads before publishing the final FIFO step (#4092)", baa1dd60 (2026-09-14) DCP receiver unpack fence, 5b550737 (2026-10-10) cake_all_gather_matmul proxy fence, f13ec08a (2024-06-09) "synchronization issue in distributed operators (#290)" -- multi-GPU / NVLink communication kernels (cross-device, out of scope).
- e4f94f94 (2026-10-03) "construct FusedOp after the PDL grid dependency sync", 6812ddb4 (2026-07-28) "fix PDL load ordering" (xqa) -- PDL, inter-kernel.
- 0b727e676 (2026-06-24) "fix tinygemm barrier bug (#3630)" -- FlashInfer copy of TensorRT-LLM 42a3e55ce (recorded as trtllm-4); not recorded twice.
- d542cff8 (2026-09-25) "cake_warp_decode: extend NVFP4 warp-decode coverage and synchronization (#5134)" -- performance/coverage commit for Blackwell sm100/sm103 NVFP4; no isolated race fix identified.
- 479f67e7 (2026-04-07) "tinygemm2 hang issue due to barrier sync (#2996)" -- hang, no conflicting access.
- 4a23b40c / 558dd20d / c18a974a / ce52279d (2026-07..09) smem-budget fixes -- capacity/OOB, not races (judged from the subjects only, diffs not read).

#### sgl-project/sglang
- dbb1235d5873c1ca24288150957bc19e5959e78f (2025-09-05) "illegal sync based on undefined behaviour (#9620)" -- wrong __shfl_sync mask in GroupReduceMax (0xffff for all half-warps), a sync-mask UB bug, not a memory conflict.
- 0443e3179fa9feada0b90e03be8567218fedad47 (2026-09-16) "kda_prefill: fence shared writes before async proxy reads (#39124)" -- adds fence.proxy.async.shared::cta in a JIT-compiled tcgen05 (Blackwell sm100) kernel; generic-to-async proxy ordering, not a thread-level conflict, and sm100 only.
- 166c6f71811087d427feed48c685356965810707 (2026-08-11) "cutedsl_bf16_gemm: trailing cluster barrier for 2-CTA TGV kernel exit (#32954)" -- cluster (distributed shared memory) barrier, out of scope (and sm100).

#### Dao-AILab/flash-attention
- 188643b82d5b06679662028558d802bcd9acfe6c (2026-02-04) "Fix shared-memory race (#2229)" -- CuTe DSL SM100 (Blackwell) forward kernel, sScale offset aliasing (m_block_size*2 vs q_stage*m_block_size); JIT and not runnable on sm_89/sm_90.
- Hopper (hopper/ directory) semaphore / barrier-ordering commits -- TMA/wgmma kernels, mbarrier protocol bugs; examined by subject only, none with a clear thread-level conflict (unverified details).

#### NVIDIA/TensorRT-LLM
- 1745102e72e2aeca542190a7c28e2a3d39b7397a (2025-09-04) "Fuse d2t to logitsBitmaskKernel and fix a race condition in one-model spec (#7481)" -- race is between two kernels / host ordering, feature commit.
- 6c2ecad2fe061bdac1902520605c746d256c988f (2026-01-22) "add syncthreads for tinygemm to resolve intermittent accuracy problem (#10873)" -- the diff moves cudaTriggerProgrammaticLaunchCompletion (PDL, inter-kernel) and adds a trailing __syncthreads; not an intra-kernel conflict. The later 42a3e55ce is recorded as trtllm-4.
- 03430ed3793c45314d263702802faa35c8900dd5 (2025-07-30) "fix illegal smem access with chunked attention (#6401)" -- illegal access (OOB), not a race.
- bf7303c7f148ef63e2b1ffbe17beebaa26294efb (2026-01-21) "Fix accuracy issue of TWO-SHOT AllReduce kernel (#10841)" and 34fbc7052c37a05e005b9ac87b41fb89116721b2 (2025-10-16) "move PREEXIT in UB kernels (#8318)" -- multi-GPU allreduce / PDL (PREEXIT), out of scope.
- cf0f4f012 (2026-09-16) VisualGen Wan RoPE SMEM staging dedup -- perf change.

#### NVIDIA/Megatron-LM, deepseek-ai/*, others
- DeepGEMM 1f6f3f378920ccb5cc036ef43eb3f5972e921713 (2026-07-06) "Fix a race condition where in-flight tensormaps are updated in-place (#343)" -- race is between the TMA engine reading a tensormap descriptor in global memory and a thread overwriting it (cute::tma_desc_commit_group / wait_group added); the engine access is not a thread load/store, Hopper-only (sm90) and not modelable by a thread-level detector.
- DeepGEMM 78b69000794d0937b47ae3387eff7663410264d1 (2026-09-14) "Fix Mega MoE task info slot release ordering (#441)" -- adds fence.acq_rel.cta before an mbarrier arrive in the Mega MoE scheduler (SM100 code path, my reading; the kernel is Blackwell-targeted and I did not establish a thread-level conflict).
- DeepGEMM 477618cd51baffca09c4b0b87e97c03fe827ef03 (2026-02-03) "Fix a sync issue in SM100 MQA logits", d30fc36c8f229f4f873b90a492f6e19e6e610923 (2026-03-22) "Fix sync issue of TMEM alloc/dealloc" -- Blackwell (sm100) TMEM/tcgen05 kernels; no sm_89/sm_90 hardware.
- FlashMLA c7590278ce1bfb86440e514c697bc4190aecd19c (2025-08-14) "Fix accuracy issue in sum_OdO kernel" -- one-line change in an sm100 backward kernel header, no race identified. The sm90 sM-initialisation barrier in FlashMLA 01a27728 is recorded as flashmla-1; its PDL __ldg-reordering half is inter-kernel.
- NVIDIA/FasterTransformer: only d2ad747 (recorded as fastertransformer-1) matched the race search; repository archived.
- microsoft/DeepSpeed (csrc): no data-race fix found; matches were host-side (shm allreduce deadlock 82c498d9, GIL, aio), a shared-memory stride/bank-conflict change 65e5f6fc (performance) and a blockDim occupancy change 000ca191.
- state-spaces/mamba, Dao-AILab/causal-conv1d, IST-DASLab/marlin (14 commits), mit-han-lab/llm-awq: no commits matching the race/sync search; llm-awq a428ff86 "fix smem error" (2025-01-03) is a smem size fix, not a race.
- bitsandbytes 7d2ecd30c044840ba5f161ec73e5eaf30ac8131d (2022-07-22) "Fixed rowcol synchronization bug" -- the diff only moves a __syncthreads() past register-only fp16->fp32 conversion before a BlockReduce; no change in memory ordering, so no race can be established from the diff.
- lmdeploy a54e3e09 (2023-09-26) "fix race condition (#460)" and e8e5603c (2026-02-10) "fix data race for guided decoding in TP mode (#4341)" -- host-side (LlamaBatch.cc / guided decoding), not kernels.
- lmdeploy fed65b1f8a1a5adbf09b6f088a80e5ced6a6ca65 (2024-07-30) "Fix gmem to smem WAW conflict in awq gemm kernel (#2111)" -- IteratorB in gemm_s_f16/cta_iterator.h bounds the n-validity by min(cta_n+CTA_N, n) so out-of-tile cp.async copies stop; the diff supports an out-of-tile smem write (possible WAW with another thread's tile) but I could not establish which threads collide without the tile constants, the kernel was retired by b28a1d04 (2024-08-19) and the turbomind build is heavy; not recorded.
- exllamav2 commits 2175f67, fced82e, 65b9e17, 8a85865, 96ebec1, 507ce60 (2024-08) -- multi-GPU broadcast / cross-device barrier kernel and event sync, out of scope.
- facebookresearch/xformers 55a4798d99c350eca9d225a14003f226775e5f76 (2023-07-06) "[cutlassF] fix race condition (fairinternal/xformers#709)" -- the same cutlassF cp.async drain mechanism as ml-frameworks pytorch-8 (6dcdae14be); not recorded twice (the pytorch copy is the one reachable with a plain pip install torch).
- NVIDIA/Megatron-LM: only 8f8be7352 (recorded as megatron-1, Triton) matched the race search of the Triton/CUDA fusion code.

#### Later additions (same session)
- vllm a64e7b940734b68d849ed2b07ca1bc3824713555 (2024-10-10) "Machete garbage results for some models (large K dim) (#9212)" -- host-side TMA descriptor shape (scale_k) bug for the sm90 Machete GEMM, not a thread-level conflict.
- vllm 74370a0e3 (2026-09-22) "hadacore_transform: respect inplace parameter to fix garbage outputs" -- aliasing of in/out tensors chosen by a host flag, not an intra-kernel race (judged from the subject only).
- flashinfer af3f5e45ff79eb9fd39ae161662ea07e50cf33ba (2026-08-05) "MoE monokernel Bug fix, barrier remove and kernel rewrite (#4027)" -- bug 1 is cross-block handoff counters not reset when the scratchpad is reused across launches (inter-launch state), bug 2 is an fp8 scale overflow; the fix is a full kernel rewrite, no isolated intra-launch fix.
- flash-attention c92ca63268836a6ea519e9892eda4895fc31811d (2024-08-25) "FA3 FP8 qkv descales ... added sync for producer WG (#1173)" -- mixed feature commit on the Hopper TMA/wgmma kernel (sm90); the single named-barrier addition cannot be separated from the rewrite of the mainloop.
- flash-attention 20cda05 (2025-11-24) "[Cute,Bwd,Sm100] enable deterministic mode for sm100 bwd and fix race conditions (#2033)" and 2409214 (2026-07-19) FP8 accuracy -- Blackwell sm100 CuTe DSL, JIT, not runnable on the cluster.
- flash-attention 9b0bc97, 731f154, aacc10f, 470010f (2022-10-31..11-03) Triton fwd/bwd race fixes -- mostly workarounds that change EVEN_M/EVEN_N masking or disable a config to dodge a Triton compiler bug (not a pure synchronisation fix); only the debug_barrier ones (ff78ea4, 62025e1) are described in flashattn-3.
- TensorRT-LLM 9332a81ce (2026-08-31) "[#18338][fix] Fix barrier-divergence races in the Blackwell CuTe DSL GVR top-k decode kernel (#18339)" -- Blackwell CuTe DSL (JIT), not runnable on sm_89/sm_90 (title also suggests barrier divergence, a synccheck class).
- state-spaces/mamba 620cd98 (2025-12-23) "Deterministic bwd kernel for mamba2 (#827)" -- replaces floating-point atomics by a deterministic reduction; atomic-order nondeterminism is excluded.
- NVIDIA/TensorRT-LLM cpp/kernels/xqa: other commits in the same path were only searched by subject; only 26b57136e matched (recorded as trtllm-2/trtllm-3).
- TensorRT-LLM XQA directory (cpp/kernels/xqa) other fixes: 07dbde482 "Stabilize XQA attention sink normalization (#19220)" (numerical init of row max/sum), 5d73194ff "Declare the var in the correct scope (#11066)" (variable scope, mha_sm90.cu), 0f42a24f4 "Fix attention sink load in xqa (#8836)" (clamped vector load), f40217828 "Fix XQA IMA for invalid pages with sliding window (#14459)" (illegal memory access), c1aa7f31d / cbcea3327 / 8c82ee280 (numerics) -- none is a thread-level conflict (judged from diffs for the first three, from subjects for the rest).

## nvidia-libs

### Rejected / examined (nvidia-libs slice)
Format: repo sha(short) date - reason
- NVIDIA/cub c65c6bd5 2017-05-03 "bad member masks in partially full warp-synchronous algorithms" - adds member_mask args to WARP_SYNC/shfl; API change, not a demonstrated unordered access
- NVIDIA/cub 70fcc9f8 2018-01-24 "Fix for missing CTA-barrier" - NOT rejected: analysed and recorded as candidate cub-1 (medium confidence)
- NVIDIA/cccl 7b3d8c588 2025-08-07 "Fix grid dependency sync in cub::DeviceMergeSort (#5456)" - programmatic dependent launch (inter-kernel, sm_90); out of scope
- NVIDIA/cccl 2ce10e4e0 2026-08-24 "Fix result-validation race in env-overload examples (#10987)" - host-side missing stream.sync before checking
- NVIDIA/cccl 3aa7a9552 2024-12-05 "Add missing __syncthreads() to test (#3061)" - libcudacxx cp.async.bulk/TMA compile-only tests (mbarrier init), needs sm_90, tests are compile-only pass tests; not usable
- NVIDIA/cccl bc240d77b 2026-06-14 "remove __syncthreads() duplicate from agent_radix_histogram (#9445)" - perf cleanup, not a race
- NVIDIA/cccl 79a8d739f/92b8f097b/df6abfb0c/a4519b1a8/49327ff94 (STF, execution::run_loop races) - host-thread races
- NVIDIA/cccl 6190044aa/d7823c52c (cuda.compute python) - Python/host-level races
- NVIDIA/cccl 0e2cb9782 2020-08-17 thrust radix sort backend missing sync before temp storage destruction - host/stream-level
- NVIDIA/cccl aca9f7e84 2018-12-20 cub CachingDeviceAllocator mutex unlock order - host-side
- NVIDIA/cuCollections 11c9b2166 2024-06-27 "Fix potential sync failure in find kernel (#522)" - __syncthreads inside `if (idx<n)`; output_buffer[thread_idx] is per-thread slot, so no conflicting access (divergent barrier only)
- NVIDIA/cuCollections 1130a8bce 2022-09-20 "Reorder logic in flush_output_buffer" - compile-time memcpy_async selection, not a race
- NVIDIA/cuCollections 4e5ebcf9b 2022-05-18 "fix a sync issue" - benchmark host code only
- NVIDIA/cuCollections 14d8d7726 2024-07-30 non-async overload early return - host side
- NVIDIA/cub 89b35d4c 2022-08-30 "Fix BlockRadixRank" - partial-warp MatchAny mask (wrong result), not a race
- NVIDIA/cub ecfff953 2022-11-28 "Fix block scan" - tests only
- NVIDIA/cub 389b81be 2022-05-25 "Fix in-place execution of adjacent difference" - load policy change LDG->LDCA; no demonstrated unordered pair
- NVIDIA/cuda-samples b530f1c 2025-05-05 transpose copySharedMem fix - indexing bug (wrong result), not a race
- NVIDIA/cuda-samples 722c5dd, b38ed29 - indexing bugs; cd76533 CG dot product rewrite - refactor to cg::reduce, not a fix
- NVIDIA/cuda-samples history starts at CUDA 9.2 (2018-03), already Volta-safe; no pre-Volta warp-synchronous reductions remain in git history

#### Added in the second pass
- rapidsai/cuml 992ab91ab 2019-12-04 "missing syncthreads before the final global reduction phase" (fused_l2_nn.h) - one __syncthreads added before the spin-lock global min reduction; no smem/global conflict that it orders could be established (smem reuse of sxNorm vs page is already guarded by the barrier in run(); the rest is shfl reconvergence); the accompanying test fixes (workspace memset size, tolerance) suggest the real bug was in the test
- rapidsai/cuml 02018b99c 2019-11-01 "enabled unit-tests for fused-l2-nn kernel. Fixed race conditions in the original kernel" - large rewrite mixed with formatting and unrelated fixes (float2 vs float4 store, page logic); individual hazard not isolatable
- NVIDIA/cutlass e7a61c7 2022-07-12 "fix race condition when h < stride_h or w < stride_w" (strided dgrad) - fix is an early return for CTAs whose start_h/start_w >= H/W; by my reading the epilogue iterator then computes p_*q_ == 0 and divides by it / maps rows outside the CTA's class, i.e. an index/OOB-style bug rather than a clean data race; mechanism unverified, no test touched
- NVIDIA/cutlass 8aa95db (sm_90 GMMA accumulator register hazard) - register/ISA-level, not shared/global memory
- NVIDIA/cutlass 1d7cde1 (ScatterD pointer) - wrong pointer, not a race
- NVIDIA/cutlass c506e16 2025-01-07 "fix mem fence" (sm90_pipeline.hpp, fence_barrier_init after mbarrier init) and 331e2f4 2025-12-19 (Python CuTeDSL dense_gemm try_acquire condition) - sm_90/Blackwell mbarrier/pipeline items, async-proxy/cluster scope; not analysed further (would be needs_sm90 leads)
- NVIDIA/cutlass 6c30441 "Update barrier.h" - inverted assert only
- NVIDIA/cuCollections b1e2cd9 2021-08-05 "Fix a warp cg synchronization bug" (static_multimap vectorized_retrieve) - inactive lanes participated in warp-collective cg calls and loaded *(first+idx) out of range; invalid collective participation/OOB, no conflicting access established
- rapidsai/raft 057fb374 - host-side stream ordering
- rapidsai/cugraph 870c8cb0 - stream sync (inter-kernel)
- NVIDIA/cccl 82d74afed - leaks only
- NVIDIA/TransformerEngine 842b770c - removal of volatile, performance
- NVIDIA/DALI 3a6b103e - host-thread race
- NVIDIA/CUDALibrarySamples 107dbba - host allocator race
- rapidsai/cudf 81e68044 2026-09-01 and 090ef6072c 2026-01-29 - cg::reduce replaced by cub::BlockReduce to silence racecheck; the CG reduce is correct, racecheck false positive
- rapidsai/cudf 62535482de 2026-09-01 (DELTA_BYTE_ARRAY decode, PR 23910) - racecheck hazard caused by compiler speculatively loading both decoder sub-objects through a runtime-selected pointer; semantically identical code, false positive
- rapidsai/cudf ba3079468d 2025-12-05 "Fix racecheck errors in the ORC reader" (PR 20792) - hazard is a condition read vs branch write of s->top.data.max_vals executed by thread 0 only (short-circuit on t==0); the other threads' read is at best a speculative load; no semantic conflicting reader established (borderline, could be promoted with low confidence)
- rapidsai/cudf 34b4f05060 2025-12-16 - removal of a redundant __syncthreads (cleanup after 848319ab)
- rapidsai/cudf f46f82508b 2026-01-16 (PR 21043) - snap_kernel, unsnap_kernel, inflate_kernel renamed *_no_racecheck: maintainers declare racecheck reports on these kernels false positives ('complexity of the warp execution patterns'); useful as a NEGATIVE CONTROL for a detector (racecheck flags, maintainers say correct), not a race target
- rapidsai/cudf bd34658311 2026-04-17 (PR 22152) - block.sync() -> __syncthreads() in single_pass_shmem_aggs_kernel as a workaround for a CUDA 13.2 / sm_120 compiler problem (cg::thread_block::sync not fencing shared memory); toolchain bug, source is race-free
- rapidsai/cudf aab8a76b53 2024-04-02 (JSON FST destructor frees tables before FST finishes) and bd37009561, 6dec0b11ca, 52a7f51d1e, cc05b47228 - host/stream-level lifetime or ordering races
- rapidsai/cudf 99aed37ece 2025-09-04 (find_instance warp-parallel) - not all lanes took part in cg collectives (UB / hang class), sanitizer tools all passed
- rapidsai/cudf 96c31ea9a5 2026-06-30 "Fully initialize PageInfo before sort_pages copies it" - uninitialised memory, different bug class
- rapidsai/cudf 80d8c2ca8c, a3ce3a1b1b, 993bb6be8c - OOB / use-after-free
- NVIDIA/cub 075e61326 (2014, 'Fix race in warp-blocked/strided exchange') -> NOT rejected: recorded as cub-4 (low confidence, archive-only)
- NVIDIA/cub 285ee6c (2014-02-20 'Fix synchronization bug in device selection routines') and fab4d2e (2014-02-24 'Add missing cta barrier reduce by key between tiles') - 2014 block_*_region code, skimmed by diffstat only, mechanism not isolated; pre-Volta and would not build on sm_89 / CUDA 13. Unexamined leads for anyone targeting the archive
- NVIDIA/cub 0ddfbf6 (2013-11-18 radix sort key-value fix 'missing syncthreads' on pre-SM35, adds __syncthreads before LoadValues in BlockRadixSortDownsweepRegion) - same hazard family as cub-1 (aliased load_values union), 2013 code, only SM<35 path; not recorded separately
- NVIDIA/cub b3e5622 (2013-12-08 'race bug when running SM10 devicescan code on SM20+') - SM10 code path, not read in detail; unbuildable on CUDA 13
- NVIDIA/cub c2254c4 (2017-08-17 remove extra bar.sync in downsweep when using match ranking) - removal of a redundant barrier, not a race fix
- NVIDIA/cub edee0bc (2018-02-14 'Fix ... issue 112: Bug in WarpScan') - shfl constant / logical-lane refactor, a logic bug not a race
- NVIDIA/cub 64546dc (2015) -> recorded as cub-3 (low); 2f6f843 (2017) -> recorded as cub-2 (medium); the single-word-variant half of 64546dc (__threadfence_block to prevent loop hoisting) is a compiler-hoisting issue, not an inter-thread race
- NVIDIA/cub 5c4cbbd (2017-01-25 remove tail WARP_SYNC), 95920ca (restore volatile in block_load/store), 829f3f2 (restore __threadfence_block), c65c6bd (bad member masks in partially full warps), 0af3062 (__ballot_sync with nvcc >= 8.5) - 2016-17 Volta-prep churn, known from commit titles only; not read in detail, not recorded
- NVIDIA/warp 31fe800d / bb1156a0 - shared-array constructor warning and lane-width logic, not races
- NVIDIA/MatX c8ff3d7 / 1cc1d15 - host/test-level synchronisation, not examined further
- NVIDIA/DALI 2352071c, b98cba1a and other sync-named commits - not read in detail (likely host/stream-level, unverified)
- NVIDIA/Fuser 42e18f20 - volatile operators for half type, API fix, not a race
- NVIDIA/TransformerEngine 7ba2f9f1 (grouped MXFP8 TMA sync) -> sm_100 TMA path, not recorded (te-3 is a different commit, 57b5b607); 4f364c8e not analysed
- NVIDIA/thrust 2010-2013 commits - pre-Volta, not analysed; later thrust history overlaps cccl
- rapidsai/cudf 2cb8f3da3a (PR 14602) - only the gpuDecodeStream part is recorded (cudf-21); comment-only 'likely false positive' notes about s->dict_pos RAW not recorded

## scientific-hpc

### Rejected commits / issues (scientific-hpc slice)
Format: repo sha-or-issue (date) - reason

#### faiss
- facebookresearch/faiss 09c7aace (2023-11-14, "Faiss GPU CUDA 12 fix: warp synchronous behavior") - not a memory race: __shfl_*_sync with mask 0xffffffff while a partial warp participates in L2Norm.cu (lanes missing from the mask, undefined shuffle result). A sync-mask/UB bug with no conflicting memory access; the fix just rounds the block size to whole warps. Would need a shuffle-mask checker, not a race detector.
- facebookresearch/faiss 02dbb4e4, 3c4056d8, aa3ce376, 02cacc52, 2496f63f, a424dcb8 (2025-2026 "race"/TSAN commits) - CPU/OpenMP races in NNDescent, HNSW, sorting.cpp, stats counters; no CUDA code.
- facebookresearch/faiss dcd83f95 (2018-05-30, OnDiskInvertedlists race) - host-side.

#### amrex
- AMReX-Codes/amrex 0c4bc54f3 (2025-11-04, "use atomic add in SRD algorithm", #4754) - real plain-vs-atomic race on U_out in MLStateRedistribute but only reachable through ApplyMLRedistribution (no in-tree test); folded into the amrex-2 record rather than recorded separately.
- AMReX-Codes/amrex 729f9bc67, c27de5cb2, 284bf23b2, 26c7610ab (2019 "threadfence" commits for Tests/GPU/Locking, Random.cpp, Scan.H) - inter-kernel / global-lock / scan decoupled look-back tuning; old (Aug-Dec 2019) and no race report in the message; Scan.H change is a performance 'memory fence optimization'.
- AMReX-Codes/amrex 6f2c4aff9 (2026-04-30 getConstParticleTileData race), b96f6e5bd (TinyProfiler memory), 3e523ca0f (LaunchSafeGuard), 6c37da5d0, 781d25a12 (thread-safe CArena/TinyProfiler) - host-side OpenMP/CPU-thread races.
- AMReX-Codes/amrex b5e000952 (2026-04-29 std::atomic instead of omp flush), 255d30f38 (lockAdd for OpenMP) - host OpenMP.
- AMReX-Codes/amrex 9d2b74990 (atomicSetID wrapper access) - compile fix, not a race.
- AMReX-Codes/amrex aee9c5fe5 (2026-10-06 warp-aggregated atomics in DenseBins) - feature/perf change.

#### lammps
- lammps/lammps 8f681a331 (2026-01-26 "Add fences to fix race condition"), 25a68ffd5 (2025-11-11 "Fix race condition"), ee60bcb40 (2026-01-17 "Break up kernels to prevent race conditions") - KOKKOS comm / ellipsoid code: missing Kokkos::fence between kernels or splitting kernels, i.e. inter-kernel ordering, out of scope.
- lammps/lammps 6d38e5ae8 (2026-01-09 "Fix race condition in unpack_exchange_e_bonus") - slot allocation via two separate atomic counters made inconsistent; refactor removes the counter pair; no plain-vs-plain conflicting access identified (all shared counters are atomic).
- lammps/lammps 45c782308 (2021-02-18) - OpenMP host race in the GPU package (torque), host side.
- lammps/lammps a2f9fa8e7 (2019-12-06 tip4p hneigh kernel split) - message mentions nondeterministic results on Volta but the commit is a refactor into a new kernel; no race identified.
- lammps/lammps 3658bace1, f09c4cf67, bfb439572, daabd03df (2026-08/09 KOKKOS sweep fixes) - host/device coherence (DualView sync/modify), allocations, MPI; not intra-kernel races. f09c4cf67 and daabd03df also fence a pack kernel before MPI (inter-kernel/host).
- lammps/lammps 9e45fbc39 (2026-06-04 ewald/gpu stage E) - "parallel correctness" is an MPI rank with nlocal==0 skipping zeroing; host-side.

#### kaldi
- kaldi-asr/kaldi bc13196e7 (2016-01-08, "fixes to kernels that were using __syncthreads incorrectly") - early return before __syncthreads in _add_diag_mat_mat / _pvec_sum (barrier divergence); no demonstrable conflicting access and exited threads do not block bar.sync on sm_70+; leaves possible uninitialised temp_data reads, not a race. Commit message itself is unsure it fixes anything.
- kaldi-asr/kaldi 2d57eb92c (2021-06-02, "fix race in cuda-online-pipeline") - host-side (pinned memory, CPU threads).
- kaldi-asr/kaldi 083c64dfb (endpointing), 42352b63e (softmax re-impl), 70df8813d (TraceMatMat kernels) - new features / perf rewrites, no race fix.

#### cuSZ
- szcompressor/cuSZ ff7f1c7 (2021-04-23 "move syncthreads outside the if-block") - barrier inside a divergent bounds check (id < d0) in c_lorenzo_1d1l/2d1l/3d1l; the guarded threads that skip it have exited, the reads only touch lanes inside the guard, so there is no conflicting access, only barrier divergence; not a race.
- szcompressor/cuSZ bbb732a (2026-05-16 lrz-3c `0*NaN=NaN` shmem leak) - uninitialised shared memory / NaN propagation, not a race.
- szcompressor/cuSZ cc585eb and the other "[fix] various updates" commits - bulk commits with no race description (not examined further).

#### dbcsr
- cp2k/dbcsr 3411d8be (2019-07-11 libcusmm/jit race) - host OpenMP race on the kernel lock map.
- cp2k/dbcsr 53133860 (2016-12-16 "CUDA: Fix for race condition on P100", adds one syncthreads() in cusmm_dnt_medium.h inside 'if (!is_loaded)' after the global-to-register loads) - real fix commit but I could not identify the conflicting accesses: the loads land in registers (lba_r/lbb_r) and the shared array buff is already protected by the loop-end syncthreads(). No message detail, kernel is the pre-JIT 2016 version. Recorded here instead of guessing a mechanism.

#### magma / hypre / alpaka / gunrock / zfp
- icl-utk-edu/magma a7f36f55, d1adc1af, fb2a41bb, ef4dee2f (2012-2014 "avoid race condition between trsm and gemm", multi-GPU buffers) - stream/multi-GPU level, inter-kernel.
- hypre-space/hypre 6d6c8605, 97cd175d (2017/2019 "Fixed possible race conditions") - CPU/OpenMP code of that era.
- alpaka-group/alpaka e78e34e5 (2025-09-11 "fix race condition add test") - SYCL queue (syclGeneric/Queue.hpp), host-side.
- alpaka-group/alpaka 866e1e85, 6fceeb91, b9aab090 (atomic API changes) - API/semantics changes, not race fixes.
- LLNL/zfp (CUDA backend src/cuda_zfp) - no race/sync commits in the history (messages searched for race|sync|atomic|shared|warp).
- icl-utk-edu/magma a7f36f55 (2014-07-21, "Split triple gemm into part1 & part2 to avoid race condition", Mark Gates) - read in full: only the jb=16 variant triple_zgemm16_upper/lower was split. For jb=16 the launch is grid(jb/(4*4)=1, npages) with one block per page, so part 2 (reads all of B12) only reads what the same block wrote in part 1 and the existing __syncthreads suffices; the commit message's cross-block rationale does not apply to jb=16. The 32/64/above64 kernels were already split. No demonstrable race.
- icl-utk-edu/magma d1adc1af, fb2a41bb (2013-2014 multi-GPU potrf/getrf host/stream synchronisation) - multi-GPU / stream level.

#### openmm
- openmm/openmm 81753737 (2013-04-24, "missing synchronization in findInteractingBlocks()", one __syncthreads added at the end of storeInteractionData) - real fix commit but the conflicting pair is not demonstrable from the diff: the buffer reset is per-thread-slot and the preceding code already ends with a barrier on every path. A plausible conflict is the next outer iteration's 'numAtoms = 0' (thread blockDim-1) vs the previous call's 'numAtoms > 0' test, but that is my inference, not stated anywhere; not recorded.
- openmm/openmm 81df8d49 (2015-06-03 "race condition doing PME in a separate stream", forceBuffers += -> atomicAdd in gridInterpolateForce) and 5cb6ad03 (2015-11-05 "race condition in energy computation", PME energy buffer in separate stream + addEnergy kernel) - inter-stream races (PME stream vs default stream), different kernels.
- openmm/openmm 6fb1c8a4 (2022-04-09 race with multiple GPUs) - multi-GPU, host side.
- openmm/openmm 83284ce6 (2013-04-10), ad2d5c0a (2011-11-03) 'Added volatile keyword' - volatile added to legacy warp-synchronous shared arrays for compiler reasons; the code remains warp-synchronous (no race fix in the happens-before sense), later converted to SYNC_WARPS (see openmm-4/-5 family).
- openmm/openmm e7a00c6a (2012-05-23 "potential race condition in PME") - 2012 kCalculatePME.cu rewrite on the pre-OpenMM-4 kernel layout; not examined in depth (too old to build, mechanism unclear).

#### gromacs
- gromacs/gromacs 7ff2ce5fd (2021-10-21, release-2021 backport of 7ca97ff90, "Fixes #4199") - duplicate of gromacs-1 on the release branch; folded into that record's links.
- gromacs/gromacs f7a0391ea (2019-02-15 "Fix CUDA fallback shmem gather reduction", "Fixed some shmem races and an intra-warp WAR hazard") - strong provenance, but the fixed branch of reduce_atom_forces in pme_gather.cu is the non-power-of-two PME order fallback; GPU PME only supports order 4 (GMX_ASSERT 'Only PME order 4 is implemented'), so that branch is never executed.
- gromacs/gromacs 97f9f399c (2017-07-19 CUDA 9/Volta nonbonded), 525e24eee (2017-08-25 CUDA 9/Volta PME) - Volta porting patches replacing __shfl/__any by *_sync and adding sync points, no per-race description; the pruning-kernel companion a8d7fb4e1 is recorded as gromacs-3 because it names the WAR hazard.
- gromacs/gromacs bace7c979 (2026-01-22 'Remove hot path warp synchronizations') - compiler warp-uniformity workaround (shuffle broadcast of widx), performance only, no race.
- gromacs/gromacs 04c945018 (2019-11-02 race condition in GPU X halo exchange with GPU update) - inter-stream/event ordering, out of scope.
- gromacs/gromacs 3bce94467 (2022-12-27 barrier after stream fork in graph capture), 2dd46f284 - CUDA graph / stream level.
- gromacs/gromacs 8d7bd5ee6, 42fe7f365, 838061bde, 8aa14d11f (2020-2022 bonded kernel atomics/shmem refactors) - performance refactors, no race fix.

#### kokkos
- kokkos/kokkos 8e692cd49 (2020-01-21 "Fixing missing threadfence in particular for scan") - moves __threadfence() before __syncthreads() so all threads fence before the last-block hand-off instead of only thread 0 after it. Under the PTX memory model a bar.sync followed by one thread's cumulative fence + atomic is already a valid release pattern, and the commit gives no failing case; not a demonstrable race.
- kokkos/kokkos 31a136c60 (2021-05-04 race when multiple threads launch different Team ParallelFor/Reduce) and b87bb4354 (2026-07-07 thread-safety of internal scratch in CUDA/HIP/SYCL), e3350ee50 (2020 thread-unsafe setting of functor attributes) - host CPU-thread races.
- kokkos/kokkos 4f4f70303 (2019-01-23 'Fix another Volta mask issue'), 08655d813 (2019-01-21 reductions with -G on Volta) - __shfl/__syncwarp mask corrections, no demonstrable memory conflict.
- kokkos/kokkos 30ec1a1a3 (2025-02-07 lock arrays on device before launching graph) - CUDA graph, inter-kernel.

#### kokkos-kernels
- kokkos/kokkos-kernels 0f5c8cc5 (2022-09-08 'Barrier after broadcast', Fixes #1512) - CPU AVX512 SIMD type, compiler barrier for GCC 7.2, host side.
- kokkos/kokkos-kernels b44d889d (2022-01-26 'Added more barriers to GMRES'), 47024f09 (TeamGMRES fixes) - batched GMRES team kernels; changes are bundled with algorithmic fixes and the commit messages give no race description; not examined to the level of an access pair (possible future candidates).
- kokkos/kokkos-kernels d94fb370 (2019-09-26 'Add team barrier for accurate results', spiluk numeric) - ILU numeric team kernel, related to kokkos-kernels-1 (same kernel family); mechanism not read, skipped in favour of kokkos-kernels-1.
- kokkos/kokkos-kernels 27e5b8b0 (2018-05-14 LU Team 'move team barrier after diagonal modification') - CPU/GPU team LU, 2018 and message-only evidence; not examined.
- kokkos/kokkos-kernels 68b077fe (2018-04-05 hashmap operations for Volta GPUs) - 2k-line rewrite of the hashmap accumulator, no discrete race fix.

#### hoomd-blue
- glotzerlab/hoomd-blue 70dadf663 (2015-03-25 'Add missing __syncthreads() in rigid body force reduction') - TwoStepNVERigidGPU (legacy rigid-body GPU code of HOOMD 1.x, since removed); real missing barrier between a store to body_force[]/body_torque[] and a windowed reduction, but code no longer exists and not buildable; low value, not recorded.
- glotzerlab/hoomd-blue b3799ab80 (2016-10-10 'fix shared memory race') - ManagedArray::load_shared copy loop plus hpmc kernel missing __syncthreads; a real fix, but HPMC build of 2016 is not possible and the template code is hard to extract; not recorded (could be added if someone needs more HOOMD cases).
- glotzerlab/hoomd-blue 8d58d621c (2013-11-05 'Fixed bug (race condition)') - the diff only reduces threads_per_particle/shared neighbors and moves early returns around in NeighborListGPUBinned; no demonstrable race.
- glotzerlab/hoomd-blue 758507718, 4707ef749, 725318133, 0969c4ec0, 2807eb1eb, c095f565e - atomics/performance/feature commits matching the keyword search, not race fixes.

#### quda
- 2cc0f5951 (2021-05-14, dslash_coarse rewrite so MG setup passes synccheck): moves a shared-memory dimension-collapse out of a dim/dir-specialised branch so every thread reaches the barrier; this is barrier divergence (synccheck), the diff shows no conflicting shared-memory access that was unordered. Also needs a full QUDA + MG build.
- 9595e1e0a (2021-01-22, "rare potential data hazard in shmem tuning"): host-side tuning code in dslash.h / dslash_helper.cuh, no kernel conflict.
- 23caf3c4a (2021-01-13, multi-GPU heatbath evolution): one added line in lib/pgauge_exchange.cu (halo exchange), multi-GPU / inter-kernel.
- cf9173857 (2020-08-05, plaquette with heterogeneous atomics): removes a host-side zeroing of result_h before the launch; host/device ordering, not intra-kernel.
- 399ff809f (NVSHMEM interior signalling via shared counter): NVSHMEM / multi-GPU, out of scope.
- d0846a742 (missing synchronisation after null-stream removal), 000b4cc85 (explicit streams for Yhat max): inter-kernel / stream ordering, out of scope.
- 0cdae682b (Volta shfl fixes, "compiler bug?"): predicates warp_combine on a template flag; no shared/global conflict shown, suspected compiler issue.

#### cuSZp (szcompressor/cuSZp, 74 commits, history scanned)
- 671d5f438 (2025-08-15, "shared memory initialization"): adds `excl_sum = 0; base_idx = 0; __syncthreads();` to the compress/decompress kernels. In the parent, warp 0 never writes `excl_sum` (only `warp>0` does) yet reads it for `base_idx`; that is uninitialised shared memory, not a race. The decoupled look-back in the parent (flag / locOffset / cmpOffset with `__threadfence` after each store and spin loads) is fenced correctly, so no `missing-fence-handoff` either.
- e22e6c2 ("bugs mentioned by Catid"): two-line change in host entry files, host side.
- 47c8f51 (small fixes): host API / example only.
- Only one other commit message matches race|sync|fence|atomic|volatile|hazard|warp (792d3cb, host padding fix); not a race.
- szcompressor/cuSZp2 and skyler-ruiyuan/FZ-GPU: `git clone` asked for credentials (URLs not reachable anonymously under those names); could not be checked.

## vision-ml-ext

### Rejected / examined commits and issues (vision-ml-ext)
- opencv/opencv 4c7fd071f (PR #28118, stitching build_warp_maps: cudaMemcpyToSymbol constants race) - host-side / inter-kernel race on __constant__ symbols between concurrent warper builds, not intra-kernel.
- opencv/opencv e496345d3 (2012 LBP cascade 'fixed race conditions problems') - ancient gpu-module code, removed; diff only changes indexing/atomics API, no identifiable intra-kernel race.
- opencv/opencv 970293a22 (2019 __shfl_up_sync with mask) - API port for CUDA 9 (mask arg), not a race fix.
- opencv_contrib 33ae078b (PR #2801 hough stream fix) - stream/global-symbol handling, inter-kernel.
- opencv_contrib 504f15ca (PR #3618 moments fix) - out-of-bounds memory error, different class.
- opencv_contrib 48b5dedb (PR #3632 knnMatchConvert) - host-side pointer increment bug.
- opencv_contrib d7389d20 (PR #4165 StereoSGM launch bounds) - grid size/bounds bug, not race.
- opencv_contrib 5bf7569f (Farneback stream sync) - host-side stream synchronization, inter-kernel.
- opencv/opencv 2a0909acf / ebc3043c8 / 735785243 (2010-2011 stereobm/reduction volatile) - 15-year-old gpu-module code, pre-ITS, code long since rewritten; not pursued.
- LightGBM 3140ef48 - kept as low-confidence (see lightgbm-1), listed here as borderline: address-math bug whose consequence is cross-block aliasing.
- LightGBM 417c732c / d893cd1f / 77d9529d (row-wise hist dense / int overflow / memory error) - overflow / OOB, not race (not read in depth).
- xgboost 7a1d67f9 / ba69244a (integer atomic for GPU histogram) - determinism of float atomics, excluded by brief (atomic FP ordering).
- xgboost bbfffb44, 6ec7e300, b908680b - CPU-side / host-test races.
- gsplat 4bb5de3 (masked-tile early return before __syncthreads_count, 2DGS/3DGS/FromWorld3DGS fwd) - barrier divergence (UB, synccheck-class) but no conflicting memory access: exiting threads never publish data and sm_70+ treats exited threads as arrived. Not a data race. (Detector may still want it as a barrier-divergence probe; see SUMMARY.)
- torchsparse 96859d6 (replace atomicadd for half) - API replacement, not a race fix.
- pytorch_scatter 6e561c8 (2020 'atomics' segment_coo) - feature development, not a bug fix of an existing race (but see new-candidate notes for segment_coo arg write ties).
- pytorch_scatter 2693efc, 2a7622b, f98ff7e, cebec48, 0807f87, 19a94a9 - indexing / dtype / API / assertion / host-side fixes; no conflicting device accesses.
- pytorch_cluster 113e8a6, d16c692, de43120, 9c33077 (parent of fix pytorch_cluster-2, not itself a fix), 8c8014b, 4fa1fb2, d85bc4f, e83a45a - logic, indexing or empty-input bugs; not races.
- MinkowskiEngine 5cea6df, a235c70, 9cf0f35, 27754c1, 4868c3a, eeec95d, 37a6ab8, 62317d4, 5bb2090, 9a8eeec, 8d64f98 - indexing, empty-tensor, host-side or build fixes; no device race.
- hashcat 143e3e1e, 37763159 and the 2026 sanitizer-fix series - OOB, host-side or tooling (sanitizer build) fixes; not intra-kernel races.
- xmrig-cuda fad9956 - swaps/adds __syncwarp variant, not a race fix.
- instant-ngp 69d34ad - host-side thread-pool race (CPU threads); out of scope.
- dgl 473bf15f, 6454c791 - not races (logic / build).
- tiny-cuda-nn 1e235e8 - unexplained "sporadic zero-predictions" fix; possible BLOCK_DIM_Z=2 shared-memory lead but a race is not established from the commit; rejected as unverifiable.
- diff-gaussian-rasterization cc408a2 - buffer-size (OOB) fix, not a race.
- kaolin 3f0ee1e, e60696b - no evidence of a race in diff or message.
- pytorch3d 9ef1ee8, d689baa, 860b742 - not races (indexing / API / logic).
- colmap 4d4c1006 - non-trivially-copyable kernel argument (UB), not a race.
- Open3D acd2f69b (wrong pointer), 33743191 (assertion) - not races.
- catboost 4e49a456b6 (shfl mask 0xFFFFFF) and e0c275cd10 (reduction init value) - wrong-mask / init bugs, not unsynchronised conflicting accesses.
- cupy 48b957bc7 - host-side; 99aec9385 (with 4fa1f7dd9 + 2019a13e8) - HIP-only barrier, not applicable to CUDA.
- xgboost 58d783df, 29bfa94b, 4f75f514, 4230dcb6, 1be09848 - not races (logic / host-side / determinism).
- thundersvm c09fffc, 5aa0226 - convergence / algorithmic fixes, not races.
- lightgbm 417c732c, 77d9529d - not races (logic / host-side).

## literature

### Rejected / out-of-scope items examined (literature slice)
#### Simulee (ICSE 2020) known-bug list -> arrayfire (all hashes are fix commits in arrayfire/arrayfire)
- arrayfire 0e0c726d7d0 (2015-05-26 "Fixed race condition in CUDA hamming_matcher()"): mostly moves __syncthreads out of divergent `if (f<ntrain)` (barrier divergence) + restructure; the actual cross-thread race was fixed by the follow-up 0c5a381 (kept as lit-arrayfire-3).
- arrayfire d7abcf2358e (homography JacobiSVD, "continue" before __syncthreads): barrier divergence only, no conflicting access added/removed -> reject.
- arrayfire 31761d27f01 (homography computeMedian "Removed unnecessary __syncthreads"): redundant barrier -> reject.
- arrayfire c59116e3ec3 (ireduce.hpp warp_reduce) and 0d0d7d1285a (reduce.hpp warp_reduce): volatile warp-reduce whose __syncthreads sat inside `if (tidx<n)`; fix hoists barrier out of the branch -> barrier divergence + volatile removal; borderline warp-synchronous, rejected as primary candidates (pre-Volta lock-step code, commit message says 'race conditions' but diff is barrier placement).
- arrayfire ee4d0bd77d7 (SIFT descriptor) and faefa30c3a0 (barriers moved out of conditionals): barrier divergence, no data conflict -> reject.
- arrayfire dfbfca5fb77 (nearest_neighbour select_matches; Simulee 'fix syncthreads in cuda nearest neighbour'): barrier divergence in select_matches + type/transpose changes; no clean race -> reject.
#### Simulee known-bug list -> kaldi
- kaldi bc13196e7fe (2016-01-08 _add_diag_mat_mat, _pvec_sum): `return` before __syncthreads (early-exit-before-barrier), no cross-thread conflict shown -> reject.
- kaldi bb589475b10 (_div_rows_vec rewrite) and 42352b63e62 (_softmax_reduce rewrite): performance rewrites removing early returns/barriers; no concrete race -> reject.
#### Simulee new bugs (Table 3)
- kaldi issue #3029 (_sum_reduce unnecessary __syncthreads): redundant barrier -> reject.
- kaldi issue #3036 (_sum_reduce called with gridDim.x>1, 'race' at buffer[threadIdx.x-halfPoint]): kernel contract is single block; maintainers closed as discussion -> reject.
- kaldi _copy_low_upp/_copy_upp_low/_add_diag_vec_mat/_copy_from_mat/_splice/_copy_from_tp: Simulee 'races' are same-value stores to the same address from different threads or stride=0 degenerate shapes (its own kaldi-bug-report.log asks 'will it cause data race?'); no maintainer action -> reject.
- cudaSift #38, cudpp #180, CUDA-CNN g_getCost_3: redundant barriers only -> reject.
- gunrock #452 (Join kernel, barrier divergence; fixed in 16294438272cdae8bee4d2db0f4ff65e28bf4331): barrier divergence, no data conflict -> reject (see gunrock section later if re-examined).
#### iGUARD / SuperCollider / HeCBench (this pass)
- HeCBench issues #131, #132, #252, #258, #259, #260, #262, #267, #268, #283: reported with memcheck/OOB output (out-of-bounds, uninitialized), not racecheck hazards -> different bug class, reject.
- HeCBench build-system commits (parallel-make races, Makefile fixes) and HIP/SYCL-only variant commits: host/build or not CUDA kernels -> reject.
- HeCBench `pathfinder` 375a603e: changes launch geometry, no conflicting access removed -> reject.
- gunrock 37db5e76: host-side cudaDeviceSynchronize placement (inter-kernel / host ordering) -> reject.
- gunrock async-BFS / atomic commits surfaced by message grep but not tied to a conflicting access in one kernel launch (unexamined in depth) -> not taken.
- cuda-samples PR #363 (transpose): functional/indexing bug, not a race -> reject.
- CCCL/CUB grid-barrier (iGUARD finding): the barrier was removed from the library, not fixed -> reject as 'fixed' (no race-fix commit).
- iGUARD LonestarGPU mis/cc: no commit since 2020 in the repo (never fixed) -> could be 'open' but LonestarGPU is outside slice; recorded in papers/NOTES.md only.
- GPUVerify N-body example: not on GitHub (paper-only) -> not a checkable target.
- Faial `transposeDiagonal` and other micro-benchmarks: synthetic/benchmark files from the paper, no maintainer fix -> reject.
- CURD per-bug list: unverified (the thesis excerpt available lacks the Chapter 5/6 evaluation) -> not taken.
#### Part 2 (GitHub-wide search outside the skip list)
- FBGEMM 224b8741 (2026-06-02, bounds_check_indices_kernel_v2 '__syncthreads after tree reduction'): the race is inside `#ifdef USE_ROCM`; the CUDA path uses per-thread atomics only -> ROCm-only, reject.
- FBGEMM e78d2f91 (2026-03-24, atomicAdd for lxu_cache_locking_counter): message says paths are 'safe by construction', defensive hardening only -> not a real race, reject.
- FBGEMM bf7327ad (2025-03-13, volatile flag sync -> acquire/release in car.cu): multi-GPU custom all-reduce (cross-rank barrier) -> out of scope.
- FBGEMM 04dbc519 / 2aa38776 / 2e1b6f46 (ROCm __syncthreads deadlock), 26bfbd50 (remove redundant __syncthreads), 6a03a175 and the grid-stride commits (launch overflow): not races -> reject.
- torchao de873d15 (2026-04-15, 'Fix race condition in mxfp8 CUDA kernels'): order of fence.proxy.async vs __syncthreads before a TMA store; both versions are ordered by the barrier in the thread-level model, the defect is generic-vs-async-proxy visibility, and the kernels are sm_100/TMA -> not representable as a thread-level conflict, needs_sm90+, reject (could be re-added as needs_sm90 / low if a proxy-aware detector is the target).
- oneflow e571ebba ('Bugfix syncthreads (#903)', 2018): not examined in depth (squashed-looking history, kernels since rewritten) -> unverified, not taken.
- MegEngine b3b81609 (topk fp16 cuda118 accuracy): accuracy fix, not a race -> reject.
- astra-toolbox 7f5a50d5 ('Add missing synchronize before free in FFT'): host-side cudaDeviceSynchronize -> reject.
- TIGRE 44dd62b7, a0a9b5a8; dealii c46ca30f; HugeCTR c29356cb/a07bba19; nvblox 03ad203f; QuEST c230706b; TensorRT 60d62e66: matched the message regex by accident (no kernel race) -> reject.
- SHOC 240335ba (2014, OpenCL scan.cl twin of 700ab826): OpenCL, not CUDA -> reject (CUDA twin kept as lit-shoc-1).
#### Part 2, second half (this pass)
- caffe 846f2c3c (2015-08-28 'fix GPU data race'): host-side stream synchronisation change, no kernel access removed -> reject.
- stdexec c7ae38cb (2025-03-14 nvexec when_all race): host/scheduler-side state machine in nvexec, not an intra-kernel conflict -> reject.
- cuopt e1469d54, 6d668c48, 43c00e55, 48c0795b, a2907006: CPU-thread races, graph capture, cusparse handles, dlopen teardown -> host-side, reject.
- GPUMD bf3a0cbb ('remove syncwarp'): removal of a __syncwarp, not a race fix -> reject.
- deeplearning4j 23c8738d ('syncthreads (#136)'): removal/relocation of __syncthreads, no race stated -> reject.
- exllamav3 56e0b848 / 6b4e247f / 94b69de7 (TP pg_gather and CPU all-reduce): multi-GPU / CPU-side all-reduce -> out of scope. c74bb35b (RoPE __syncthreads under divergence, 'may affect ROCm'): barrier divergence only -> reject. ecaf05e1 (remove redundant warp sync): reject.
- exllamav3 73d8fc6d (2026-10-01 'Reductions: __syncthreads after reading reduced result (latent bug)'): trailing barrier added to block_reduce_argmax / block_reduce_max_h / block_reduce_sum_f; at HEAD only block_reduce_argmax (sampling_basic.cu:35) and block_reduce_sum_broadcast_f (activation_kernels.cuh:399) are called, and neither function has a call site in which a second reduction reuses the `shared[32]` array in the same kernel -> the commit says 'latent'; not a demonstrable race, reject (could be revisited if a second reduction in one kernel is found).
- pyfr issue #10 (cuBLAS dgemm racecheck output): library-internal false positives, repo archived 2026-04-12 -> reject.
- xmr-stak eb8376fa ('CUDA: use volatile pointer'), AutoAWQ/xmr 'asm volatile' commits: not races -> reject.
- gdrcopy 9c6c28ec ('Added missing __threadfence_system in pplat.cu'): host-visible fence in a latency microbenchmark, CPU-GPU ordering -> out of scope.
- chrono 4bf26bc0 (2015 'fixed some non-thread safe writes'): 168-line SPH rewrite, no isolated race diff -> unverified, not taken.
- cholla ae555519 (2022-07-11 'Fix race condition in GPU reductions'): global initialisation `*out = lowLimit` by thread 0 raced with other blocks' atomicMax of the same location; fix moves initialisation to the host (setScalarDeviceMemory) and the Calc_dt kernels stop using gridReduceMax. This IS a real cross-block initialisation-vs-atomic race, but the buggy version of gridReduceMax at the parent already wrote `out[blockIdx.x] = val` (atomicMax was commented out), so the pair that raced at the parent is not the one the message describes; the race existed only in an intermediate/other configuration -> not taken (ambiguous which variant the message describes).
- specfem3d 85a601ba (2019 'fixes attenuation setup ... avoiding synchronization issues in thread blocks'): 556-line mixed commit; only a shared-array rename sh_temp*_att and removal of a __syncthreads that 'seems to be necessary'; no isolated race -> not taken.
- GenomeWorks b17845fb ('fixed two data races'): host-side async H2D copy vs destructor of a host variable -> reject. 4fee9ca9 ('Improved warp syncing in Myers'): adds __syncwarp/asserts and restructures masks in warp-synchronous code; real change but 159-line rewrite mixing masks, shuffles and loop shape, no isolated race pair -> not taken (could be a 'warp-synchronous-ITS' candidate with more reading).
- FBGEMM 95946ae5 (2021 'warp sync primitives for min and max reduction'): optimisation, not a fix -> reject. FBGEMM c0e46ed0/f2408454: perf/adaptive sizing -> reject.
- CNTK af8a4cce / 4a681f27 (2017 'resolve race condition ...'): the race is in the CPU (OpenMP) ScatterValues path; GPU kernel changes are formatting only -> host-side, reject.
- sppark 9e5c7951 -> kept as lit-sppark-1; bd01032d -> lit-sppark-3; 17119848 -> lit-sppark-2. sppark 'cooperative grid.sync before store' variants elsewhere: none found.
- heavydb 91633679 ('WIP: Add warp synchronization for Volta'): compiler-side flag plumbing for the JIT (CudaMgr / codegen), not a kernel diff -> reject. heavydb 1ed4f56a (Maxwell-only failures, 'register reuse flag'): compiler/code-generation bug -> reject.
- spark-rapids-jni 013b0671, a05d01bc: host stream synchronisation -> reject. 0f772846, 98703422, 87a0a4fa: tests / numerics -> reject.
- AliceVision bb162224 / 289717ef: removal of cudaDeviceSynchronize -> reject. AITemplate 029ba1c6: softmax refactor, no race in message -> reject.
- icicle 7fa1416e ('fix includes and syncthreads', 2023): adds a __syncthreads in an early MSM prototype that was rewritten; the 144-line deletion hides the context -> not examined further, reject.
- espresso (2018 DipolarBarnesHut threadfence/volatile/syncthreads toggling by one author, b6ae226a / 4414758f / 51f06324 / 466858df): the series disables and reverts the same __threadfence; no net fix -> reject.
- octopus (gitlab MR !2197, batch_dotpv Volta race, 2023-10-26): GitLab not GitHub, the MR page does not show merge status or the diff; Octopus's mirror stars not checked -> unverified, not taken.
- ik_llama.cpp #2502 / llama.cpp #28475 mmq_ids_helper: on llama.cpp's skip list; ik_llama.cpp is covered by agent open-new (ikllama-1).
- popsift PR #82 is also recorded by agent open-new as popsift-1 (one row for the three races); this agent keeps lit-popsift-1/2/3 as separate rows per race.

## open-new

### Rejected / examined (open-new agent)
- nvlabs/tiny-cuda-nn issue #47: CUTLASS "Error Internal" with -G build; not a race.
- vllm-project/vllm PR #25996: __syncwarp missing symbol on ROCm build; build bug, not a race.
- vllm-project/vllm PR #28619: moe marlin illegal memory access (OOB), not a race.
- psychocoderHPC-bot/picongpu issue #13 (racecheck hazard in KernelFillGridWithParticles): read ParticlesInit.kernel at HEAD b8f83fcf; every write to finished/destFrames/destCounter is followed by worker.sync() before cross-thread reads -> no race found; likely racecheck false positive (the issue itself says unverified).
- hypre-space/hypre issue #584: racecheck WAW inside closed-source cuSPARSE csrmv (cusparseSpMV beta=0); cuSPARSE team called it false positive; not open-source kernel.
- GROMACS GitLab issue #4516 (NBNXM kernel racecheck, Clang-CUDA only): an unconditional __syncthreads sits between the reported lines; reporter suspects Clang miscompile; not a source-level race. Not verified further.
- triton-inference-server issue #8057: race inside closed-source TensorRT GEMM kernel; no source.
- ROCm/rocm-libraries PR #12266: HIP/gfx11 only.
- pytorch PR #198922/#199775 (cp.async drain): pytorch is owned by ml-frameworks agent.
- cutlass issue #3597 (Example 93 Blackwell GQA cta_reduce): sm100a only (tcgen05) -> see candidates if recorded.
- NVIDIA/cccl issue #1906 (CUB merge sort racecheck): reported as "no longer present in main"; cccl is owned by the nvidia-libs agent; not re-examined.
- pyfr issue #10 (racecheck report): hazard sits in cuBLAS (closed source), repo archived; false positive for our purposes.
- NVIDIA/cuda-samples issue #166: host-side bug, not a device race.
- rapidsai/cuml issue #4157: WebFetch failed (client error), details unverified; cuML cpp/src_prims/.../grid_sync.cuh at HEAD has __threadfence around the flag hand-off, so no race found there. cuML BoundingBoxKernel (tsne) has __threadfence too. (The tsne RepulsionKernel is recorded as cuml-tsne-1.)
- arrayfire reduce_all_kernel: last-block ticket has __threadfence -> OK. NVIDIA/cuda-samples scan.cu and fp16ScalarProduct: barriers present -> OK.
- facebookresearch/faiss: blockReduceAll has KillWARDependency (explicit barrier), L2Select has an explicit barrier -> OK. BlockSelect/WarpSelect internals were not read.
- opencv/opencv Canny edgesHysteresisLocalKernel (code.opencv.org bug #3562, fixed by 7fd21d21 in 2014): already recorded by the vision-ml-ext agent as opencv-2; not duplicated.
- BBuf/how-to-optim-algorithm-in-cuda causal_dot_product_kernel (fast-transformers copy): each thread owns shared_kv[e*M + m] for its own m, cross-block accumulation uses atomicAdd -> no race.
- NVlabs/nvdiffrast cudaraster (CoarseRaster/FineRaster/TriangleSetup .inl): warp-synchronous scans already use __syncwarp(mask) between steps (e.g. CoarseRaster.inl L455-L460) -> no race found.
- Dao-AILab/causal-conv1d causal_conv1d_fwd.cu smem_exchange loop (L63-L104): barriers at L92/L96/L100/L102 separate every write/read across the loop back-edge -> OK.
- mit-han-lab/torchsparse reduce_mask_cuda_int32: warp 0 lanes each touch only bitmask_shared[4*lane .. 4*lane+3] after the __syncthreads -> disjoint, OK. voxelize/count kernels use atomicAdd.
- NVIDIA/MinkowskiEngine pooling/broadcast/convolution kernels: all scatter-adds use atomicAdd; max-pool writes are to unique rows per reduce_by_key output -> OK.
- bytedance/lightseq ker_attn_softmax_lt32: cub::BlockLoad/Store VECTORIZE variants use no shared memory, so reuse of ts_load/ts_store is harmless -> OK.
- exllamav2 rope.cu / q_mlp_softmax.cuh, AutoGPTQ cuda_64/cuda_256 kernels: regex hits only; blockvec[] is read-only after the barrier, rope has no shared memory -> OK.
- open-mmlab/mmcv spconv reordering.cuh / sparse_maxpool.cu `outFeatures[inds[..]] +=`: one launch per kernel offset, output indices unique within a launch -> no collision (design assumption, not verified at runtime).
- BVLC/caffe batch_reindex_layer.cu L92 `c_data[...] += 1`: host-side loop, not a kernel.
- FasterTransformer / sglang / flashinfer / xgboost / faiss "shared-without-any-barrier" hits from my nosync.py scan: the ones I opened call cub::BlockReduce/BlockScan or a helper that contains the barrier; most hits were NOT individually read (the scan cannot see barriers inside callees), so this list is not exhaustive.

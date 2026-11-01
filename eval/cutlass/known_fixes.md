# Known races / sync bugs in NVIDIA/cutlass (web search, 2026-11-01)

Queries (GitHub search API via WebFetch, repo:NVIDIA/cutlass): `race` (39 hits, all read), `racecheck`, `"data race"`, `syncthreads OR syncwarp OR "missing sync" OR "missing barrier"` (53 hits, only first ~11 read), `compute-sanitizer` (59 hits, first 20 read), `semaphore OR split-k OR stream-k race OR hazard OR synchronization` (301 hits, first 20 read). Also CHANGELOG.md (main; only up to the 3.6.0 heading was read; 4.6-4.8 sections had no matches). Individual items fetched via api.github.com/repos/NVIDIA/cutlass/{issues,pulls}/N. Coverage is incomplete: no separate queries for `fence` or `cp.async wait`, and later pages of the large result sets were not read. Statements on "fix" come from page content; "unclear" = not stated.

## Issues / PRs

| # | URL | State | Fix commit / PR | Component | Summary | Arch | Sanitizer-found |
|---|---|---|---|---|---|---|---|
| 386 | https://github.com/NVIDIA/cutlass/pull/386 | merged 2021-12-20 | 288af365db7c665a251c0dc2b556d2d5ade1fd77 | Grouped GEMM | Added missing sync to avoid WAR hazards between tiles | unclear | unclear |
| 2162 | https://github.com/NVIDIA/cutlass/issues/2162 | closed 2025-04-28 | unclear | sm90_gemm_array_tma_warpspecialized_cooperative (grouped GEMM) | Suspected tensormap update in store warps not waiting for in-flight TMA stores (reporter: tma_store_wait<0> before update fixed mismatch) | sm90 | no |
| 2760 | https://github.com/NVIDIA/cutlass/issues/2760 | closed 2025-12-09 | unclear (related PR #2719 "Support PDL for SM90 Array TMA GEMM", merged 2025-12-09, same close time; link not stated) | sm90 array/grouped GEMM cooperative + pingpong | No wait_on_dependent_grids() with PDL enabled, kernel can read before prior kernel's results visible | sm90 | no |
| 2719 | https://github.com/NVIDIA/cutlass/pull/2719 | merged 2025-12-09 | n/a | SM90 array TMA GEMM | PDL support; appears to resolve #2760 (unclear) | sm90 | unclear |
| 2962 | https://github.com/NVIDIA/cutlass/issues/2962 | open | none | Array GEMM kernels / group tile scheduler | Scheduler constructor reads problem-shape array before wait_on_dependent_grids() under PDL | sm90, sm100 | no (code inspection) |
| 2626 | https://github.com/NVIDIA/cutlass/issues/2626 | closed 2025-12-27 | unclear | Example 77 FMHA backward (Sm100FmhaBwdKernelTmaWarpSpecialized) | racecheck reported race, synccheck "Missing wait"; default mode clean; root cause not stated | sm100 | yes (racecheck, synccheck) |
| 3324 | https://github.com/NVIDIA/cutlass/issues/3324 | closed 2026-06-19 | unclear | sm100 (blockscaled) mixed TMA/cpasync warpspecialized mainloops | ClusterBarrier CTA-scope semantics: leader CTA may see barrier full before peer CTA's cp.async smem writes visible cluster-wide; proposed cluster-scope acquire/release | sm100 | no |
| 3636 | https://github.com/NVIDIA/cutlass/pull/3636 | merged 2026-09-23 | 84a62ec421c23ac7b657c7ca709970c650e54954 | CuTeDSL dense_gemm_persistent_dynamic.py epilogue (CLC scheduler, TMA store) | Per-warp scheduler instance left epilogue tile counter at 0, reusing C-SMEM stages still owned by in-flight TMA stores (~1.1% wrong elements) | sm103 | no |
| 3316 | https://github.com/NVIDIA/cutlass/pull/3316 | open | none | CuTe Blackwell tutorials 04/05 2SM TMEM alloc | Peer CTA race at 2SM TMEM alloc (suspected signal to uninitialized mbarrier); cluster arrive+wait fix cut racecheck from 65 errors to 0 | sm100 | yes (racecheck) |
| 2835 | https://github.com/NVIDIA/cutlass/pull/2835 | open (draft) | none | Example 77 TMEM address | Missing barrier between MMA warp's TMEM address smem write and epilogue read when 0 KV tiles; tcgen05 dealloc may fail | sm100 | unclear |
| 3597 | https://github.com/NVIDIA/cutlass/issues/3597 | open | PR #3600 (open) proposed | Example 93 GQA cta_reduce | No sync after reading warp partials; next KV tile can overwrite shared max scratch; racecheck 8 hazards, 2193 wrong values | sm100 | yes (racecheck) |
| 3600 | https://github.com/NVIDIA/cutlass/pull/3600 | open | n/a | Example 93 GQA reduction scratch | Synchronize scratch before reuse (fix for #3597) | sm100 | n/a |
| 3598 / 3601 | https://github.com/NVIDIA/cutlass/issues/3598 , https://github.com/NVIDIA/cutlass/pull/3601 | open / open | none merged | Example 93 GQA mailbox init | Initialization overwrites active remote contributions (title-level only; details not read) | sm100 | unclear |
| 3643 | https://github.com/NVIDIA/cutlass/issues/3643 | open | PR #3647 (open) proposed | CuTe DSL 2cta_mma_blockscale_m128 example | Cross-CTA mbarrier arrivals at CTA scope instead of CLUSTER; SFB barrier never waited; CUDA_ERROR_LAUNCH_FAILED | sm100-family (Thor) | no |
| 3764 | https://github.com/NVIDIA/cutlass/issues/3764 | open | PR #3763 (open) proposed | Example 77 MLA fused split-KV reduction (sm100_fmha_mla_tma_warpspecialized.hpp) | Exact-value counter wait can be overshot (hang); thread 0 signals before other warps finish LSE writes (wrong output) | sm103 (B300) | no |
| 3331 | https://github.com/NVIDIA/cutlass/issues/3331 | open | PR #3380 (open) guards s2t | sm100 blockscaled mixed TMA/cpasync mainloop | SFA/SFB s2t (UTCCP) issued by both CTAs in 2SM mode; should be leader only; suspected, currently works | sm100 | no |
| 3652 | https://github.com/NVIDIA/cutlass/pull/3652 | open | none | Example 93 tgv_gqa.cuh EPILOG_warp | Missing tcgen05.ld wait before arrive releasing TMEM to MMA warp (suspected, not reproduced) | sm100 | no (clean under sanitizer on reduced repro) |
| 3653 | https://github.com/NVIDIA/cutlass/pull/3653 | open | none | Example 77 fwd/gen/MLA-fwd softmax->correction TMEM stats | tcgen05.st published via mbarrier.arrive without wait::st (found by PTX memory-model verification; not reproduced) | sm100 | no |
| 3654 | https://github.com/NVIDIA/cutlass/pull/3654 | open | none | Example 77 load collectives | Non-elected lanes may wait on stale mbarrier phase in producer_acquire; proposes __syncwarp (unconfirmed) | sm100 | no |
| 3808 | https://github.com/NVIDIA/cutlass/pull/3808 | open | none | CuTeDSL SM100 accumulator release | Wait for tcgen05.ld before releasing accumulator (title only; details not read) | sm100 | unclear |
| 3279 | https://github.com/NVIDIA/cutlass/pull/3279 | open | none | sm103 blockscaled GEMM main_sf_load | Missing PDL wait (title only) | sm103 | unclear |
| 3786 | https://github.com/NVIDIA/cutlass/pull/3786 | open | none | Epilogue fusion scalars | Read device-memory scalars after PDL wait (title only) | unclear | unclear |
| 3803 | https://github.com/NVIDIA/cutlass/pull/3803 | open | none | SM100 SSD example | Repeated/early TMEM frees (title only) | sm100 | unclear |
| 3435 | https://github.com/NVIDIA/cutlass/issues/3435 | open | none | tcgen05.alloc/dealloc cta_group::2 | Launch failure when one CTA deallocs (title only; sync relation unclear) | sm100 | unclear |
| 1716 | https://github.com/NVIDIA/cutlass/issues/1716 | open | none | CP_ASYNC non-ZFILL copy trait | Buffer overwriting with predicated copy (title only; sync relation unclear) | unclear | unclear |
| 3538 | https://github.com/NVIDIA/cutlass/issues/3538 | open | PR #3578 (open) | GemmWithKReduction parallel split-K | Workspace initialization skipped (semaphore/workspace correctness; race nature unclear) | any | unclear |
| 3539 | https://github.com/NVIDIA/cutlass/issues/3539 | open | PR #3624 (open) | EllGemm column-major split-K | Workspace sizing undersizes split-K semaphores (not a race per se; unclear) | any | unclear |
| 3440 | https://github.com/NVIDIA/cutlass/pull/3440 | closed, not merged | none | SubbyteReference::set() | atomicCAS retry condition fix (atomic correctness; details not read) | any | unclear |
| 658 | https://github.com/NVIDIA/cutlass/pull/658 | merged 2022-11-09 | n/a (merge) | singleton::get | Thread-safe singleton construction (host-side, not GPU) | host | unclear |
| 2573 | https://github.com/NVIDIA/cutlass/issues/2573 | open | none | SM90 cluster_sync | Question: why __syncthreads before cluster_sync (QST, not a bug) | sm90 | no |

## CHANGELOG.md hits

| Version | Entry | Type |
|---|---|---|
| 3.9.1 | Fixed Group Gemm hang issue in CUTLASS 3.x | hang (cause unclear) |
| 3.9.2 | GEMM hang issue when problem size K is 128 | hang (cause unclear) |
| 4.2.0 | Fix Hopper SM90 group gemm kernel to only use commit group and wait group instead of also waiting on mbarriers | sync fix, sm90 |
| 4.2.0 | Fix an issue where mbarriers are initialized with a zero arrival count | sync fix, any |
| 4.3.0 | Fix a race check issue of Blackwell SM103 kernels by adding missing elect one for prefetch barrier initialization | racecheck, sm103 |
| 4.3.0 | Fix a dead hang issue caused by early return warp | hang, any |
| 4.4.0 | Fix memory fence for clc scheduler in Blackwell SM120 pingpong kernel | fence fix, sm120 |
| 4.4.2 | Fix kernel loading race condition when multiple GPU are present in the same process in JAX | host-side race |
| 4.5.0 | Uses an additional barrier (mma_trampoline_barrier) to track cp.async arrivals in both CTAs | sync fix, sm100-family |

Count: 28 table rows of issues/PRs (item #s 3598/3601 share a row) + 9 CHANGELOG entries.

## Gap-fill (pass 2)

Queries run (GitHub search API via WebFetch, repo:NVIDIA/cutlass, per_page=100; "read" = items visible after WebFetch text truncation, not pagination limits; item details via api.github.com/repos/NVIDIA/cutlass/{issues,pulls}/N and /comments):
- `fence` : 61 hits, 14 read
- `barrier.h OR wait_eq OR arrive_inc OR GenericBarrier` : 11 hits, 11 read
- `stream-k OR streamk hang OR race OR wrong` : 526 hits (loose OR query), 15 read
- `block_striped OR BlockStripedReduce` : 3 hits, 3 read (only bf16x2 atomics feature requests/PR #1653, #1616; no sync bug)
- `semaphore volatile OR acquire OR fence OR release` : 22 hits, 18 read
- `"memory model" OR "memory ordering" OR threadfence OR "ld.acquire" OR "red.release"` : 25 hits, 14 read
- `cp.async wait` : 18 hits, 11 read
- `syncthreads OR syncwarp OR "missing sync"` : re-read chars 30000-130000 of the response (13 items visible, no total_count shown in that slice; pass 1 says 53). Only new items of interest: #1900 (QST, not a bug), #3117
- `compute-sanitizer` : 59 hits; re-fetch returned the same first 20 as pass 1, no new items read (remaining 39 still unread)
- CHANGELOG.md: second fetch covered chars 100000-154790 (from inside 3.6.0 down to 1.0). Summarizer found only: 3.6.0 synclog tool; 3.5.1 serial/parallel split-k for sparse; 3.4.0 NamedBarriers usability; 3.2.0 Hopper Stream-K (functional only); 3.1.0 Streamk GEMM with Broadcast; 2.11.0 Stream-K introduced; 2.9.0 profiler parallel splitk; 1.2.0 Split-K. No race/hang/fence/semaphore bug-fix bullets in 1.x-3.5 (result from a summarizing model over the text, not verified line by line).
- Not exhaustively read: later parts of every truncated result set above.

| # | URL | State | Fix commit/PR | Component | Summary | Arch | Sanitizer-found |
|---|---|---|---|---|---|---|---|
| 3721 | https://github.com/NVIDIA/cutlass/issues/3721 | open (created 2026-10-08) | PR #3724 (open) proposed | sm90_mma_multistage_gmma_{ss,rs}_warpspecialized.hpp (cp.async + GMMA) | No fence.proxy.async between generic-proxy cp.async smem writes and wgmma (async proxy) reads; latent, not observed on HW | sm90 | no (custom PTX checker) |
| 3724 | https://github.com/NVIDIA/cutlass/pull/3724 | open | n/a | same | Adds async-proxy fence before wgmma reads of cp.async-filled smem (consumer-side) | sm90 | no |
| 3799 | https://github.com/NVIDIA/cutlass/pull/3799 | open (2026-10-29) | none | sm100_mma_{cpasync,mixed_tma_cpasync,blockscaled_mixed_tma_cpasync}_warpspecialized.hpp | Adds fence_view_async_shared() in MMA warp after consumer_wait before tcgen05.mma; latent, found by PTX-ISA check, not run on GPU | sm100 | no |
| 2974 | https://github.com/NVIDIA/cutlass/issues/2974 | open | none | CuTe DSL fmha_bwd.py | Question: only fence_view_async_tmem (tcgen05.wait) used, no tcgen05.fence::before_thread_sync; 5 comments not read, maintainer answer unclear | sm100 | no |
| 3805 | https://github.com/NVIDIA/cutlass/issues/3805 | open | PR #3808 (open) proposed | CuTeDSL utils.gemm.sm100.epilogue | Accumulator released before tcgen05.ld completes (no tcgen05.wait::ld before arrive) | sm100 | unclear (fuzz-found) |
| 2687 | https://github.com/NVIDIA/cutlass/pull/2687 | open, unmerged | none | Example 77 fmha fwd mainloop | Adds 2 missing tmem store fences before producer_commit | sm100 | unclear |
| 3798 | https://github.com/NVIDIA/cutlass/pull/3798 | open | none | Example 77 fwd warpgroup | tcgen05.wait::ld before TMEM stats releases (title only) | sm100 | unclear |
| 2098 | https://github.com/NVIDIA/cutlass/issues/2098 | open | none | tcgen05.fence support in 3.8.0 | Title only: "Is tcgen05.fence supported"; details not read | sm100 | unclear |
| 2027 | https://github.com/NVIDIA/cutlass/issues/2027 | open (bot labels inactive-90d) | unclear: jackkosaian (2025-01-08) offered diff, hwu36 (2025-02-11) said "should be fixed now"; no commit/PR/version cited | sm90_tile_scheduler_stream_k.hpp (CUTLASS 3.x stream-K fixup) | Nondeterministic-reduction mode: non-final CTAs wait on previous CTA (as deterministic), final CTA waits only on initial CTA, so epilogue can run before all contributors reduced; wrong results; maintainer said logic corrupted in 3.4 | sm90 (H100) | no |
| 1781 | https://github.com/NVIDIA/cutlass/issues/1781 | closed 2024-09-04 (completed) | unclear (no commit cited) | include/cutlass/barrier.h check_barrier_in_range (NamedBarrier) | Inverted assert (idx >= MaxNumNamedBarriers) fails in debug builds with Stream-K + TMA cooperative; introduced 3.5.0 per commenter; assertion bug, not an ordering bug | sm90 | no |
| 1917 | https://github.com/NVIDIA/cutlass/issues/1917 | open | none (workaround) | Stream-K scheduler, example 55 | Hang because gemm.initialize() not called in profiling loop (stream-K needs it to set up inter-CTA reduction counters); also a numeric mismatch attributed to K-split accumulation order | sm90 | no |
| 1296 | https://github.com/NVIDIA/cutlass/issues/1296 | closed 2024-01-12 | n/a | cutlass/semaphore.h serial split-K | Wait deadlock on AMD hardware with modified PTX; works on NVIDIA; not a CUTLASS bug | non-NVIDIA | no |
| 3650 | https://github.com/NVIDIA/cutlass/pull/3650 | open (2026-09-21) | n/a (closes #3540) | epilogue_with_broadcast.h, gemm_universal_streamk_with_broadcast.h (2.x Stream-K separate reduction) | Single-source reduce() did not advance dest/tensor iterators by reduce_fragment_idx, so all blocks wrote fragment 0 (timing-dependent wrong output); addressing error, no sync change | any | no |
| 3733 / 3737 | https://github.com/NVIDIA/cutlass/issues/3733 , https://github.com/NVIDIA/cutlass/pull/3737 | open / open | PR #3737 proposed | SM120 GEMM | Hang when K = 0 (cause not read) | sm120 | unclear |
| 2775 | https://github.com/NVIDIA/cutlass/issues/2775 | closed 2026-09-14 (not_planned; no technical answer) | none | cutlass/semaphore.h release (serial split-K) | Question: no threadfence in semaphore.release; is visibility of prior writes guaranteed? Only bot comments, unanswered | any | no |
| 2535 | https://github.com/NVIDIA/cutlass/issues/2535 | closed 2025-08-24 | none | user split-K with TMA reduce-add | Random +-1/2 errors; thread converges on "TMA reductions are atomic, order nondeterministic, need semaphore"; no library bug | sm90 | no |
| 3117 | https://github.com/NVIDIA/cutlass/issues/3117 | closed 2026-07-20 | PR #3118 (open, unmerged, conflicts); XiaoSongXS said 2026-08-11 will port | CuTeDSL distributed_gemm_reduce_scatter_blackwell.py | Spin loop uses relaxed not acquire; maintainer first argued relaxed works (multimem.ld_reduce bypasses L1), later recommended release+acquire with correct scope | sm100 | no |
| 3118 | https://github.com/NVIDIA/cutlass/pull/3118 | open | n/a | same | "use acquire to prevent reordering" (1 line) | sm100 | no |
| 3282 | https://github.com/NVIDIA/cutlass/issues/3282 | closed 2026-07-22 | none | tma_reduce_add / atomicAdd | Question; maintainer: execution order not deterministic | any | no |
| 3787 | https://github.com/NVIDIA/cutlass/pull/3787 | open (2026-10-25) | n/a | sm90 coop, sm100 cpasync and mixed TMA/cpasync kernels | Five load warps lack wait_on_dependent_grids() under PDL; author reproducer showed mismatches before, none after | sm90, sm100 | no |
| 3788 | https://github.com/NVIDIA/cutlass/pull/3788 | open | none | legacy epilogue thread op | Build op after PDL wait (title only) | unclear | unclear |
| 1247 | https://github.com/NVIDIA/cutlass/issues/1247 | open | none | SM90 TMA warpspecialized ClusterBarrier::init | Illegal smem access at ClusterBarrier::init (title only) | sm90 | unclear |
| 2615 | https://github.com/NVIDIA/cutlass/pull/2615 | closed 2025-09-09 (merged status unclear) | unclear | wgmma_sm90.cu | "fix cp_async_wait number" (title only) | sm90 | unclear |

New rows: 23.

## Relevant to CUTLASS 2.x stream-K / Barrier / block_striped / semaphore

No issue or PR found reporting a memory-ordering bug (fence/acquire/release/volatile) in cutlass/barrier.h (Barrier::arrive_inc/wait_eq/wait_lt/wait_eq_reset/arrive_range_inc), gemm_universal_streamk.h, block_striped.h, or semaphore.h, and none fixing one. Searches were limited as listed above (many results unread).
- semaphore.h: #2775 asks why Semaphore::release has no threadfence; closed not_planned, never answered (unclear whether intentional). #1296 split-K semaphore deadlock was AMD hardware, not a bug.
- barrier.h: #1781 only an inverted debug assert in NamedBarrier check_barrier_in_range (3.5.0 regression per commenter); no fix commit cited. Nothing on GenericBarrier ordering.
- block_striped.h: only #1653/#1616 (bf16x2 atomics feature); no sync bug.
- 2.x stream-K (gemm_universal_streamk.h, with-broadcast variant): #3650 (open PR) separate-reduction broadcast epilogue iterators not offset by reduce_fragment_idx, wrong output; addressing, not ordering; not merged.
- 3.x stream-K (not the 2.x files, same algorithm): #2027 nondeterministic-reduction final CTA waited only on initial CTA, epilogue could run before all partials reduced (sm90_tile_scheduler_stream_k.hpp); maintainer-acknowledged, said fixed Feb 2025, no commit cited. #1917 hang when counters not initialized via initialize().
- Analogous (other code): #3117/#3118 spin-wait relaxed vs acquire in a CuTeDSL example, PR unmerged; #2535 concurrent TMA reduce-add needs a semaphore.

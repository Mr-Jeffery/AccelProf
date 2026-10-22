# T21b triage (fresh-context Opus, 2026-10-22)

Scope: the items of `eval/realworld/triage_queue.md` (at f182bb0) listed below; `amrex-1` and `hecbench-hungarian-1` (runs still going) and
the ~750 "other" reports (T21c's queue) are out of scope. Oracles read at `bc71082`, never edited; `recall.csv`, `REALWORLD.md` and the oracles
are not changed here (the T21b helper applies the outcomes). Open REVIEW.md labelling items are scored as committed and only noted.

Evidence sources: the ARC run store `/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10/<id>/` (kernel JSONs, no dump) and the ARC builds
`/mnt/beegfs/fzheng4/realworld_t21b/build/<target>/<variant>/`, both copied to the WSL box; SASS from `cuobjdump -xelf all` +
`nvdisasm -c --print-line-info-inline` (CUDA 13.3) of those builds; detector source at f551ca0 (paths relative to the cuVein tree);
GPU experiments on the **WSL triage build** (cuVein f551ca0 runtime on Jeffery's laptop, RTX 4060 Laptop sm_89), triage only, never scored.
Thread ids are `tid = block << 10 | warp << 5 | lane` (`python/hb_oracle.py:65`).

## Summary

| item | rows | verdict | row should become |
|---|---|---|---|
| 1 `cccl-1` fixed | vc, sc | **detector defect** (c): the trace records the converged-path `__syncwarp(0x3fffff)` with `sync_mask` 0xffffffff; every kernel trace of `cccl-1` (both builds, both modes) carries `tv_violation` | fixed: not a fixed-build report of the model; `STILL-REPORTED -> defect syncwarp-nop-full-mask` (clean on the corrected trace). Buggy: DETECTED holds on the corrected trace, but the scored run is TV-invalid: decision D-T1 |
| 2 `lit-fbgemm-1` buggy | vc, sc | **attribution defect** (harness, not a line-rule question): `rw_attribute.cubin_frames` overwrote every pc of `gemv_bf16` with a data section's frame | `DETECTED` (DR, vc: Race, a2 robust; sc: one point); the 1 "other" report per mode is this pair |
| 3 `opencv-2`, `lit-shoc-1` SC half | 4 rows | (a) race under PTX, SC at source level; reported DR because sm_89 SASS of volatile shared has no `.STRONG` token: model-boundary fact (D20 (i)) | unchanged: `DETECTED-AS-DR` |
| 4 residual rows | 9 rows | each reported pair is the residual its oracle names | unchanged: `RESIDUAL-AS-EXPECTED` (REVIEW item 2 labels still open for cccl-3, cmssw-1, dxtc2) |

Two defects, each with a minimal failing input: `eval/realworld/defects/syncwarp-nop-full-mask/` (detector, trace) and
`eval/realworld/defects/attrib-global-init-frames/` (harness).

## 1. cccl-1, fixed build, STILL-REPORTED in both modes: detector defect

**SASS of the fixed driver** (`_Z19block_reduce_kernelPKhPh`):

| pc | SASS | frame (innermost first) |
|---|---|---|
| 0x00f0 | `LDS.U8 R5, [R0]` | block_reduce_raking.cuh:222 <- :257 |
| 0x0130 / 0x0140 | `@!P0 LDS.U8 R2, [R0+0x1]` / `@!P1 LDS.U8 R4, [R0+0x2]` | block_reduce_raking.cuh:161 <- :224 |
| 0x00c0 | `UMOV UR6, 0x3fffff` (and `R7 = 0x3fffff` at 0x00d0) | |
| 0x0190 | `BRA.CONV UR6, .L_x_2` | sm_30_intrinsics.hpp:111 <- util_ptx.cuh:241 <- block_reduce_raking.cuh:231 (the fix's `WARP_SYNC`) |
| 0x01b0 | `CALL.REL.NOINC $__internal_0_$__cuda_sm70_warpsync` | same |
| 0x01d0 | `NOP` (label `.L_x_2`) | same |
| 0x0220 | `STS.U8 [R0], R5` | thread_store.cuh:284 <- warp_reduce_smem.cuh:160 <- block_reduce_raking.cuh:233 |
| 0x0270, 0x0300, ... 0x0700 | `NOP` after each further `BRA.CONV UR6 / CALL` pair | warp_reduce_smem.cuh:162/171 (`WARP_SYNC(member_mask)`, UR6 = 0x3fffff) |
| 0x0790 | `WARPSYNC R7` (body of the helper) | |

So the fix's barrier is there, as the oracle says. The warp-sync helper is the only `WARPSYNC`; it runs only when `BRA.CONV` falls through
(group not converged).

**What the trace holds** (WSL re-run of the ARC fixed driver, dump on): one `syncwarp` record per `NOP` (pcs 0x1d0, 0x270, ... 0x700),
each `sync_mask=0xffffffff active=0x3fffff`; no record at 0x790. Lanes 22..31 of warp 0 skipped the raking branch (`@P0 BRA .L_x_1` at 0x00a0)
and are alive at `BSYNC B0` (0x0710) until their exit at seq 35 (`exit pc 0x730 active 0xfffffffe`).

**Where it goes wrong.**
- Collector: the `SANITIZER_INSTRUCTION_SYNCWARP` callback (`nv-compute/src/compute_sanitizer.cpp:309`) fires at the fast-path `NOP` and its
  `mask` argument is 0xffffffff; `SyncwarpCallback` (`nv-compute/gpu_src/gpu_patch_pc_dependency.cu:254-256`) stores it as the record's
  `sync_mask`. The program's mask is 0x3fffff (UR6). This is the defect: the trace names the wrong participants.
- HbClock is correct given that record: `sw_expected` (`sanalyzer/src/tools/pc_dependency_analysis.cpp:999`) = 0xffffffff minus exited lanes
  (none yet), `on_syncwarp` (:1026) opens an instance that lanes 22..31 never join, so the lanes 0..21 never join each other; the W2 monitor
  (:1998) then fires `TV-syncwarp-completion-order: block 0 warp 0 lanes mask 4194303 issue a record at pc 544 while pending at a syncwarp`
  (pc 544 = 0x220). `python/hb_oracle.py` refuses the same trace (`ALIGNMENT FAILURE`).
- The ARC run shows the same: `tv_violation` is set in `cccl-1-fixed/{vector-clock,scalar-clock}/kernel_0.json` and in
  `cccl-1-buggy/{vector-clock,scalar-clock}/kernel_0.json` (pc 592 = 0x250 there). A scan of every kernel JSON in the store found
  `tv_violation` in these four files only. The harness does not read `tv_violation` (no match in `eval/realworld/harness/*.py`), so these
  verdicts were scored.

**Are the reports right?** No. With `sync_mask` set to 0x3fffff in every syncwarp record of the dumped trace, `python/hb_oracle.py`
gives 0 races on the fixed driver (30 as recorded, `YOSEMITE_HB_STRICT=0`) and 3 on the buggy one: `tid0@0x130`, `tid0@0x140`, `tid1@0xf0`
vs `tid1/2/3@0x1d0`, i.e. exactly the oracle pair (L222/L161 vs thread_store.cuh:284; in the buggy SASS the `STS.U8 [R4], R5` at 0x01d0
precedes the first `BRA.CONV` at 0x01e0, so no warp barrier separates it from the reads). The pairs of 0x220-0x2a0 etc. (ReduceStep store
vs the next step's load, separated by `WARP_SYNC(member_mask)`) are artifacts of the same record.

**Minimal failing input:** `eval/realworld/defects/syncwarp-nop-full-mask/` (`syncwarp_partial_mask.cu`; expected race-free; WSL triage
build reports 2 DR races in both modes plus the TV violation; the full-mask control is clean). Precondition: partial mask, lanes outside it
alive, converged group.

**Score effect.**
- `cccl-1,fixed,{vector-clock,scalar-clock}`: STILL-REPORTED is a detector defect, not a fixed-build report of the model; the oracle's
  `absent` is right. Record it as the defect (class (c)) and do not count it as a false report of the model.
- `cccl-1,buggy,{vector-clock,scalar-clock}` (DETECTED): the oracle pair is a true race and is reported on the corrected trace, but the
  scored run's kernel trace is TV-invalid ("verdict for this kernel is untrustworthy"). See D-T1.
- The 15 + 15 "other" reports per mode of `cccl-1` (buggy and fixed) are artifacts of this defect; 12 of the 15 matched buggy reports too
  (only the three pairs with STS 0x1d0 survive). They should leave T21c's queue.
- `hecbench-hungarian-1` (still running): its fix adds `__syncwarp` between reduction steps; check its kernel JSONs for `tv_violation`.

## 2. lit-fbgemm-1, MISSED in both modes: attribution defect; the row is DETECTED

**Reported pair** (ARC, both modes): `gemv_bf16`, a = 0x27d0 LDS, b = 0x2b00 STS, shared WAR, DR, vc: structural / a2 robust;
`hb_races`: `a_tid 31751` (block 31, warp 0, lane 7) at 0x27d0, `b_tid 31968` (block 31, warp 7, lane 0) at 0x2b00, shared addr 28
(= `warpLevelSums[0][7]`), count 448. This is the oracle's thread pattern: lane w of warp 0 reads `warpLevelSums[0][w]` (L145) in
iteration col, lane 0 of warp w writes it (L141) in iteration col + 1.

**SASS, checked independently** (buggy, `-c` listing; matches the oracle's `sass_notes`):

| copy | STS (L141) | BAR.SYNC (L142) | LDS (L145) |
|---|---|---|---|
| 1 | 0x27b0 `@!P0 STS [R11], R18` | 0x27c0 | 0x27d0 `@!P1 LDS R16, [R12]` |
| 2 | 0x2b00 `@!P0 STS [R11], R20` | 0x2b60 | 0x2b80 `@!P1 LDS R18, [R12]` |
| 3 | 0x2f50 `@!P0 STS [R11], R4` | 0x2f60 | 0x2f80 `@!P1 LDS R2, [R12]` |

Between 0x27d0 and 0x2b00 there is no `BAR`; the only sync is `WARPSYNC 0xffffffff` at 0x2a70 (warp scope, does not order warp 0 with
warp 7). No `.STRONG` on these accesses. Fixed driver: STS/BAR/LDS at 0x27c0/0x27d0/0x27e0, 0x2ba0/0x2bb0/0x2bc0, 0x2fc0/0x2fd0/0x2ff0
plus `@!P6 BAR.SYNC` 0x2b80, `@!P0 BAR.SYNC` 0x2ee0, `BAR.SYNC` 0x32b0, all as the oracle states.

**Frames.** `nvdisasm -c --print-line-info-inline` attributes 0x27d0 to fast_gemv.cu:145 and 0x2b00 to fast_gemv.cu:141 (no inlined
frame on either). The `sm_30_intrinsics.hpp:439 <- fast_gemv.cuh:65 <- fast_gemv.cu:149` frame of the queue is a harness artifact, not
nvdisasm's: `rw_attribute.py:46` runs nvdisasm without `-c`; `gemv_bf16` is the cubin's last `.text` section and is followed by
`.nv.global.init` (curand's `mrg32k3aM1SubSeq` tables, 13,628 `/*OFFSET*/ .byte` lines); `SECTION_RE` (:31) does not match that
`.section` line, so `fn` stays `gemv_bf16` and :62-64 overwrite every pc of the function (the data dump runs past its last pc) with the last `//##` group of the function
(the `SHFL.DOWN` slow path of `warpReduceSum`, fast_gemv.cuh:65 inlined at :149). Both a and b therefore got the same frames.
Reproduced with the harness parser copied verbatim: `eval/realworld/defects/attrib-global-init-frames/`.

**Verdict:** not a miss and not an inlined-frames rule question: an attribution (harness) defect. With correct frames the pair matches
the oracle's two sites exactly (±0 lines).

**Score effect.** `lit-fbgemm-1,buggy,vector-clock`: `DETECTED` at Race, a2 robust, DR (= expected_class), `miss_cause` empty.
`lit-fbgemm-1,buggy,scalar-clock`: `DETECTED` (one point). Fixed rows stay `CLEAN-FOR-PAIR`. The single "other" report of
`lit-fbgemm-1` buggy per mode is this pair and leaves T21c's queue. Re-run `rw_attribute.py` with the parser fixed for every target and diff
the frames: among the eight targets checked here only `lit-fbgemm-1` and `pytorch-4` have `.nv.global.init` after their last `.text`
section; for `pytorch-4` (`gatherKthValue` last, 43 offset lines, pcs 0x0000-0x02a0) every reported pc (0x1ea0, 0x2000, 0x2010, 0x20c0)
is outside the overwritten range, so its rows are unaffected. The other 20 targets were not checked.

## 3. The 4 DETECTED-AS-DR rows: (a) SC at source level, DR in SASS; model-boundary fact under D20 (i)

**opencv-2** (`canny::edgesHysteresisLocalKernel`, both modes): reported pcs 0x0af0 / 0x0d20 and 0x0af0 / 0x0fb0.
- 0x0af0 `LDS R4, [R10.X4+0x4]` canny.cu:285; 0x0d20 and 0x0fb0 `@P0 STS [R10.X4+0x4c], R5` canny.cu:297 (unrolled copies 1 and 2); the
  oracle's sites and pcs. The only `BAR.SYNC` of the kernel is at 0x0a60 (canny.cu:270), before both.
- Source: `__shared__ volatile int smem[18][18];` (canny.cu:247 at ce42593), so both accesses are volatile (strong) in PTX: SC.
- SASS: the kernel has 153 `LDS` and 25 `STS`, none with `.STRONG`; its only `.STRONG` token is `ATOMG.E.ADD.STRONG.GPU` (the global
  counter). Thread pairs from `hb_races`: tid 15386 vs 15370 (block 15, lanes 26 and 10 of warp 0, `dist warp`) and 15397 vs 15381
  (`dist block`) for 0x0af0/0x0d20; 4330 vs 4314 and 4341 vs 4325 for 0x0af0/0x0fb0.

**lit-shoc-1 SC half** (`bottom_scan<double,double4,256>`, both modes): reported pcs 0x0c70 / 0x0d40 and 0x0c70 / 0x0d70.
- 0x0c70 `LDS.64 R32, [R0.X8+0x808]` scan_kernel.h:198 <- :295; 0x0d40 `STS.64 [R0.X8+0x10], RZ` scan_kernel.h:147 <- :295; 0x0d70
  `STS.64 [R0.X8+0x810], R26` scan_kernel.h:152 <- :295: the oracle's extra pair (L198 vs L147/L152).
- Source: `scanLocalMem(const T val, volatile T* s_data)` (scan_kernel.h:143 at 785d9ee); both accesses through `volatile`: SC.
- SASS: the double kernel has 54 `LDS.64` and 34 `STS.64`, 51 `BAR.SYNC`, zero `.STRONG` tokens. Thread pairs: tid 31744 (block 31,
  thread 0) reads at 0x0c70 vs tid 31999 (thread 255, warp 7) clears at 0x0d40, addr 2056 = `[R0.X8+0x808]` for thread 0 (the oracle's
  "thread 255 clears s_data[255] which thread 0 returns from at L198"); 31841 vs 31840 (`dist warp`) and 31872 vs 31871 (`dist block`) for
  0x0c70/0x0d70.

**Verdict:** class (a), a race under PTX §8.7.1; its PTX class is SC (volatile vs volatile, unordered). The detector classes strength from
SASS, and sm_89 lowers `ld/st.volatile.shared` to plain `LDS`/`STS` with no `.STRONG` token, so the report's class is DR. This comes from the
compilation of volatile shared memory, not from the detector, and is a model-boundary fact for the paper (the same fact `cccl-1`'s oracle
records for its volatile store, and the reason the SC column cannot be reached for shared memory on sm_89).
**Score effect:** none; the four rows stay `DETECTED-AS-DR` under D20 (i), with the reason "volatile shared compiles to plain LDS/STS on
sm_89 (no .STRONG)".

## 4. The 9 RESIDUAL-AS-EXPECTED rows: all are the named residual

Reports that hit the residual's ranges (`recall_pairs.json` `fixed.residual`), with frames re-checked against the `-c` listing of the
fixed build:

| target (rows) | residual (oracle) | reported pcs and SASS (fixed build) | thread pair / note |
|---|---|---|---|
| `cccl-3` (vc main, sc main, vc certain) | merge atomicAdd vs volatile load (SC) | 4 pc pairs per mode, e.g. 0xaa70 `ATOMG.E.ADD.64.STRONG.GPU` (device_atomic_functions.hpp:226 <- agent_topk.cuh:441 <- :580) vs 0xadf0 `@!P2 LDG.E.64.STRONG.SYS` (block_load.cuh:379 <- :1097 <- agent_topk.cuh:589); class SC | same pairs in all three rows (8 reports each incl. both directions) |
| | merge atomicAdd vs init_histograms plain store (DR) | 0xaa70.. vs 0xbe50 `STG.E.64 [R6.64], RZ` (agent_topk.cuh:422 <- :683 <- :794); class DR | oracle residual_sites "same three sites" (L441-448, L589/block_load L379, L422-427) |
| `cmssw-1` (vc, sc) | co[i] += ws store (volatile) vs psum load (volatile, L175) | 0x0740 `STG.E.STRONG.SYS` prefixScan.h:77 <- :152 vs 0x09b0 `LDG.E.STRONG.SYS` prefixScan.h:175; SC | the oracle's residual_sites (0x0740 / 0x09b0) |
| | store L77 vs last block RMW (L182) | 0x06c0 `LDG.E.STRONG.SYS` / 0x0740 `STG.E.STRONG.SYS` (L77) vs 0x1090 `LDG.E.STRONG.SYS` / 0x10f0 `STG.E.STRONG.SYS` (L182); SC | named in the oracle's review notes ("expect this one too"); n_race 0, n_sc 8 |
| `hecbench-dxtc2-1` (vc, sc) | `colors[xrefs[idx]] = colors[idx]` scatter (L448) | 0x2b50/0x2b60/0x2b70 `LDS [R5+0x380..0x388]` vs 0x2b90/0x2ba0/0x2bb0 `STS [R7+0x380..0x388]`, all main.cu:448 (the float3's three words); DR | tid 59395 vs 59392 (block 58, lanes 3 and 0): two lanes, as the residual says |
| `pytorch-4` (vc, sc) | minIndexFound read (L77) vs atomicMin (L86) | 0x1ea0 `LDS R5, [0x80]` Sorting.cu:77 vs 0x20c0 `@P0 ATOMS.MIN.S32 RZ, [0x80], R0` (device_atomic_functions.hpp:142 <- Sorting.cu:86); DR | tid 0 vs 31 (`dist warp`) and 32 vs 31 (`dist block`); plain read vs atomic = DR |

**Score effect:** none; all nine rows stay `RESIDUAL-AS-EXPECTED`. REVIEW item 2 (residual vs absent labels for `cccl-3`, `cmssw-1`,
`hecbench-dxtc2-1`) is still open and is not decided here.

## Decisions for Jeffery

- **D-T1 (cccl-1 buggy, and any TV-invalid kernel).** The harness scores verdicts from kernels whose trace carries `tv_violation`; the
  HbClock banner calls such verdicts untrustworthy. Options: (i) keep `cccl-1` buggy DETECTED with a footnote (the corrected-trace replay,
  triage only, gives exactly the oracle pair); (ii) score kernels with `tv_violation` as unscoreable (an m4-like cause) until the defect is
  fixed. Either way the harness should surface `tv_violation` in `recall.csv`. Only the four `cccl-1` kernel JSONs carry one today.
- **D-T2 (attribution re-run).** Fix `rw_attribute.cubin_frames` (reset `fn` at every non-`.text` `.section`, or pass `-c`) and re-run
  attribution and scoring for every target, so that `lit-fbgemm-1` becomes DETECTED from the scored pipeline rather than from this note.
- **D-T3 (the syncwarp defect).** The runtime is frozen for T21b, so `cccl-1` is reported with the defect. Whether to fix it (the
  collector would have to take the mask from the SASS, e.g. the `UMOV URx` that feeds `BRA.CONV`, since the callback's mask is wrong) and
  re-run `cccl-1` on a new runtime is a decision for after T21b. It belongs in §"Defects".

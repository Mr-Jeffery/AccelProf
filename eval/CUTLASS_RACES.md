# X9: new races in CUTLASS (v4.8.1, sm_89)

Measurement and triage only. Every number below traces to a kernel JSON, a CSV under `eval/results/cutlass/`, or a
dossier under `eval/cutlass/findings/`. Modes: scalar-clock mode (the True half of `--both-barrier-orders`) and
collector-only mode (the False half). Nothing was filed upstream and nothing was pushed (D23).

**Result.** One race confirmed by the verifier: class (a), a data race (DR) in CUTLASS 2.x stream-K. `GenericBarrier::wait_eq_reset` has no acquire, so the finishing CTA's plain loads of peer partials are unordered under PTX. The race is formal-only on sm_89: no wrong output was produced, including under perturbation. Every other candidate is class (b) (ordered by a mechanism the detector does not model) or not a race (morally strong flag accesses).

## §1 Scope

- **Tag.** CUTLASS v4.8.1, commit `2c85f497547eb441f0fe80bfb0fb2e6f9add1719`.
- **Runtime.** cuVein f551ca0. Hashes, checked at the start of every job by `x9_env.sh`:
  - libsanalyzer `5a20fd14ab6c6806`
  - collector `b746b4dd23e90f46`
  - fatbin `a2d7368bc1c61986`
- **Branch.** `eval/cutlass-races`, cut from `eval/co-offline` at 763bc5c, because `--both-barrier-orders` exists only there. Step 0b green set: 340 passed, 4 skipped.
- **Hardware.** GeForce RTX 4060 Ti (sm 8.9, driver 580.82.07) for recording and racecheck. CPU `normal` nodes for analysis.
- **Build.** `x9_build.sh`, with cmake flags:
  ```
  -DCMAKE_BUILD_TYPE=Release -DCUTLASS_NVCC_ARCHS=89 -DCUTLASS_ENABLE_TESTS=ON -DCUTLASS_UNITY_BUILD_ENABLED=ON
  -DCMAKE_CUDA_FLAGS=-lineinfo -DCUTLASS_NVCC_EMBED_PTX=OFF
  ```
  - CUDA 13.3 and gcc 12.4, never `-G`.
  - All 40 in-scope sm_89 targets built with rc 0: the 39 test binaries below plus the aggregate `cutlass_test_unit_conv_device`.
  - They contain sm_89 SASS only, no PTX.
  - `-lineinfo` leaves the SASS identical (55,062 lines, no diff).
  - Not built: every sm_90a target (they need `sm_90a`); see the table below.
- **Families and binaries** (manifest `target` column; prefix `cutlass_test_unit_` omitted). Each family is followed by its binaries:
  - **conv-sm80:**
    - conv_device_tensorop_f16_sm80, f32_sm75, f32_sm80, f32_tf32_sm80
    - f8_sm89, s32, s32_interleaved
  - **epilogue-fusion:** gemm_device_broadcast, gemm_device_gemm_with_fused_epilogue_tensorop
  - **epilogue-unit:** epilogue_thread, epilogue_threadblock, epilogue_warp
  - **grouped-blas3:**
    - gemm_device_blas3, blas3_gaussian
    - grouped, grouped_blas3, grouped_rank_2k_scheduler, grouped_scheduler
  - **reduction:** reduction_device, reduction_kernel, reduction_thread
  - **simt:** conv_device_simt, gemm_device_simt, gemm_device_simt_3x
  - **simt-2stage:** the gate kernel of gemm_device_simt (`SM50_device_sgemm_nt.L0_64x64x8_64x32x1_8x8_8x4_1x2`)
  - **tensorop-multistage-cpasync:** the gate kernel of gemm_device_tensorop_f32_sm80 (`SM80_Device_Gemm_f16t_f16n_f32t_tensor_op_f32.128x256x32_64x64x32`)
  - **tensorop-sm70-sm75:** conv_device_tensorop_f32_sm70, gemm_device_tensorop_sm70, gemm_device_tensorop_sm75, gemm_device_wmma
  - **tensorop-sm80-multistage:**
    - gemm_device_tensorop_f16_sm80, f32_sm80, f32_sm80_3x, f32_tf32_sm80
    - f64, planar_complex, s32_sm80
  - **tensorop-sm80-variants:**
    - gemm_device_mixed_input_tensorop_sm80, sparse_tensorop_sm80
    - tensorop_sm89, tensorop_sm89_blockwise
- **sm_90a table** (not built on sm_89; `eval/cutlass/sm90a_table.tsv`): 103 test files, 79 in `gemm/device` and 24 in `conv/device_3x`. Each row gives the file, its TEST count and the kernel schedules it instantiates:
  - 49 files use the builder default schedule or are CUTLASS 2.x SM90 f64 tests.
  - 9 files use the `KernelCpAsyncWarpSpecialized` schedules (plain, Cooperative, Pingpong; 3 files each, 3 tests each).
  - The remaining 45 use `KernelTmaWarpSpecialized*` schedules or name another schedule; the per-file list is in the tsv.

  They are out of scope on this GPU. §6 lists what that leaves unverified.
- **Step 0c, the cp.async check.** Dump recording of the MmaMultistage kernel:
  - LDGSTS is recorded as 16-byte shared-memory writes with per-lane addresses (3072, 3088, …) and `hb_async=1`.
  - 40 commit and 24 wait records are present.
  - The async pc set equals the 18 LDGSTS pcs.
  - The alignment stage passes.
- **Recording.** `eval/cutlass/harness/x9_record.sh`, flavor `main`, with the X1b knobs (`BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16`):
  ```
  x9_collect.py collect --manifest eval/cutlass/manifest_cutlass.csv --id <id> --reps 1 \
      --timeout-floor 1200 --timeout-cap 1200
  ```
  - Timeouts were re-recorded by flavor `t5400` (floor and cap 5,400 s, store `traces/t5400`).
  - `x9_collect.py` binds `--timeout-floor` onto `parallel.collect_one`, which `parallel.py collect` otherwise ignores.
- **Analysis.** `eval/cutlass/harness/x9_analyze_split.sh` (`normal`):
  - `x9_split.py` splits each recording into one sub-store per kernel name (`<id>__kNNN`).
  - Per sub-id:
    ```
    parallel.py analyze --manifest <manifests_k/id.csv> --id <sid> --confirm --both-barrier-orders \
        --analysis-timeout 82800 --analysis-mem-gb 28
    ```
    then `x9_pairs.py` attributes pairs to file:line, using `nvdisasm --print-line-info` on the loaded cubin (inlined frames included).
  - The roll-up is `x9_summarize.py`, written to `eval/results/cutlass/summary/`. The class rules are applied by `x9_funnel.py`, written to `summary/groups_classified.tsv`.
  - `x9_csv.py` writes `eval/results/cutlass/x9.csv`; `x9_perbinary.py` writes `summary/per_binary.tsv`.
- **Racecheck.** On every binary with filter `*`, store `eval/cutlass/racecheck/`:
  ```
  compute-sanitizer --tool racecheck --racecheck-report all --print-limit 10000 <exe> --gtest_filter=*
  ```

## §2 The funnel

Per family. Sources: `summary/families.tsv` and `summary/groups_classified.tsv`.

- **Kernels** are analyzed kernel names, one sub-id each.
- **Collector-only pairs** are pc-level pairs that collector-only mode reports.
- **Candidates** are the deduplicated CONFIRMED pairs, keyed by (family, innermost CUTLASS frame of each access).

| family | kernels | collector-only pairs | CONFIRMED | BARRIER-ORDERED | RECLASSIFIED | ON-ONLY | candidates | (a) | (b) | not (a) | (c) | (d) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| conv-sm80 | 181 | 3,747 | 3,747 | 0 | 0 | 0 | 12 | 0 | 10 | 2 | 0 | 0 |
| epilogue-fusion | 16 | 70 | 70 | 0 | 0 | 0 | 4 | 0 | 2 | 2 | 0 | 0 |
| epilogue-unit | 146 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| grouped-blas3 | 350 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| reduction | 47 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| simt | 297 | 12,247 | 12,247 | 0 | 0 | 0 | 18 | 5 | 9 | 4 | 0 | 0 |
| simt-2stage | 1 | 64 | 64 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| tensorop-multistage-cpasync | 1 | 386 | 386 | 0 | 0 | 0 | 5 | 2 | 1 | 2 | 0 | 0 |
| tensorop-sm70-sm75 | 622 | 23,202 | 23,202 | 0 | 0 | 0 | 7 | 3 | 2 | 2 | 0 | 0 |
| tensorop-sm80-multistage | 585 | 48,315 | 48,315 | 0 | 0 | 0 | 15 | 6 | 5 | 4 | 0 | 0 |
| tensorop-sm80-variants | 100 | 3,267 | 3,267 | 0 | 0 | 0 | 12 | 4 | 4 | 4 | 0 | 0 |
| **total** | **2,346** | **91,298** | **91,298** | **0** | **0** | **0** | **74** | **21** | **33** | **20** | **0** | **0** |

The two sm70 binaries (conv_device_tensorop_f32_sm70, gemm_device_tensorop_sm70) were recorded and analyzed last (§5 item 7). They add 112 kernels (53 RACE, 59 CLEAN) and 4,239 pairs, all CONFIRMED, to tensorop-sm70-sm75. Every one of those pairs falls into the family's existing 7 groups; no new group and no UNCLASSIFIED group appeared (`summary/funnel.tsv`).

- **Subset check.** It holds on every kernel: ON-ONLY is 0, and scalar-clock mode's report set equals collector-only mode's on all 2,346 kernels. Kernel verdicts are identical in the two modes:
  - RACE: 711
  - CLEAN: 1,633
  - missing: 2 (reduction_device-c10 `__k000`/`__k001`, empty verdict CSV, see §6)
- **Not (a)** (20 groups: 12 on `semaphore.h`, 8 on `barrier.h`). Pairs on the synchronization words themselves: `semaphore.h:76/106` and `barrier.h:104/124/175`. Both accesses are morally strong (`.acquire`/`.release`/atomic, gpu scope), so by §8.7.1 they are not a data race. cuVein reports them as SC for information.
- **The 21 (a) candidates are one race.** They are 64,304 pc-level pairs, all of the S1b shape:
  - the stream-K finisher's or reduction block's plain read of peer partials (`functional.h:134/177/202`, `complex.h:202`, `block_striped.h:165`)
  - against the peers' stores or atomic reduces (`block_striped.h:194`, `functional.h:943/963/992`)
  - in `GemmUniversalStreamk` instantiations of 6 families.

  Deduplicated across families, that is one finding.
- **Verifier.** 1 of 1 dossier confirmed: class (a), DR (`eval/cutlass/findings/verdict_streamk-wait-eq-reset.md`).
- **Observable under perturbation.** 0. The reproducer passed 400/400 runs stock, fixed and perturbed.

**Two lines.**
- **Confirmed candidates per family:**
  - conv-sm80 12, epilogue-fusion 4, simt 18, simt-2stage 1, tensorop-multistage-cpasync 5
  - tensorop-sm70-sm75 7, tensorop-sm80-multistage 15, tensorop-sm80-variants 12
  - epilogue-unit, grouped-blas3 and reduction 0
  - Total 74. Of these, 21 are (a), all one mechanism.
- **Verifier:** confirmed 1 finding (stream-K `GenericBarrier::wait_eq_reset`), class (a), DR, formal-only.

## §3 Confirmed findings

| finding | kernel family | accesses (file:line at the tag) | class | thread relation | racecheck | already known? | status |
|---|---|---|---|---|---|---|---|
| streamk-wait-eq-reset | `GemmUniversalStreamk` (CUTLASS 2.x stream-K) in simt, simt-2stage, tensorop-multistage-cpasync, tensorop-sm70-sm75, tensorop-sm80-multistage, tensorop-sm80-variants | Cooperative finisher: peer `STG` `block_striped.h:194` ← `gemm_universal_streamk.h:772` (or peer `RED` `functional.h:943/963/992` ← SK:790) × finisher `LDG` `functional.h:134` ← `block_striped.h:181` ← SK:813, after `Barrier::wait_eq_reset` at SK:809 (`barrier.h:168-180`). Separate reduction: partial `STG` at SK:989 × reduction-block read (`block_striped.h:165` ← `epilogue_base_streamk.h:133/144`), after `wait_eq_reset` at SK:885 | DR | inter-CTA, from the source: the pair records carry no thread or CTA ids | 0 hazards (racecheck checks only shared memory; the pair is in global memory) | no (`known_fixes.md`; GitHub search for `wait_eq_reset`: 0 hits) | verifier CONFIRMED; formal-only on sm_89; upstream draft `eval/cutlass/upstream/streamk-wait-eq-reset.md`, not filed |

Mechanism:
- **Consumer side.** Thread 0 spins on `atomicCAS(flag, val, 0)`, a relaxed gpu-scope `atom.global.cas`, then `__syncthreads()`. No acquire pattern forms.
- **Producer side.** `arrive_inc` runs `__syncthreads()`, then thread 0 issues `fence.acq_rel.gpu; red.relaxed.gpu`, which is correct.
- **Why it is a race.** No synchronizes-with edge links the CTAs, so the weak load is not causality-ordered after the weak store.
- **SASS.** Stock is `ATOMG.E.CAS.STRONG.GPU; BRA; BAR.SYNC; LDG.E`. The sibling `wait_eq` uses `LDG.E.STRONG.GPU; CCTL.IVALL`.
- **Fix.** One `fence.acq_rel.gpu` after the CAS loop. It compiles to `MEMBAR.ALL.GPU; ERRBAR; CCTL.IVALL`.

Reproducer (`findings/streamk-wait-eq-reset/repro.cu`, 75 lines, job 325921):
- It reproduces the reported pairs: 112 pairs, all CONFIRMED, DR, RAW, matching the unit-test frames.
- The fixed reproducer is still reported with the same 112 pairs. Its hand-off has the elected-thread shape (S1a below) that the detector does not certify, so the brief's "clean run in both modes" cannot be met for this finding. The fix rests on the PTX argument and the SASS.

Call sites at the tag:
- `gemm_universal_streamk.h:809, :885`
- `gemm_streamk_with_fused_epilogue.h:813, :941, :1983, :2095`
- `gemm_universal_with_visitor_streamk.h:592, :639`

The CUTLASS 3.x sm90/sm100 stream-K schedulers use `wait_eq`/`wait_lt` and are not affected.

## §4 Class (b) and (c)

**(b): ordered by a mechanism the detector does not model.**

| cluster | candidates | mechanism | SASS construct | why the detector does not certify it |
|---|---|---|---|---|
| K: split-K serial epilogue under `cutlass::Semaphore` | `arch/memory.h:153×415`, `415×415`, `396×85`, `396×396`, `204×431`, `431×431`, `252×447`, `447×447`, `298×463`, `463×463`; `predicated_tile_iterator.h:447`; `epilogue_direct_store.h:260×268`, `268×268` 26 groups, 8,504 pc pairs: conv-sm80 10, epilogue-fusion 2, simt 8, tensorop-sm70-sm75 2, tensorop-sm80-multistage 2, tensorop-sm80-variants 2 | Slice k's epilogue writes D; slice k+1 reads D (beta source) and overwrites it. In between: `bar.sync` (`semaphore.h:102`), thread 0 `st.release.gpu` (:106); thread 0 of slice k+1 spins on `ld.acquire.gpu` (:76) inside `__syncthreads_and` (:92-93), then `__syncthreads` (:96). This is causality-ordered under PTX. | release: `BAR.SYNC; MEMBAR.ALL.GPU; ERRBAR; STG.E.STRONG.GPU`; acquire: `LDG.E.STRONG.GPU; CCTL.IVALL; BAR.RED.AND; BAR.SYNC` | R3 starts only from a PO-next RMW, and the Semaphore has no RMW (documented as assumption R3b, `instance_gate.md` §7). R1 is intra-CTA, and the barrier-only clock has no cross-CTA edge. |
| S1a: stream-K first peer's partials × later peers' atomic reduce | `block_striped.h:194 × functional.h:943/963/992` 7 groups, 17,616 pc pairs: simt 1, tensorop-multistage-cpasync 1, tensorop-sm80-multistage 3, tensorop-sm80-variants 2 | The first peer runs `__syncthreads`, then thread 0 runs `fence.acq_rel.gpu; red.relaxed.gpu` (`barrier.h:121-124`). The next peer's thread 0 spins on `ld.acquire.gpu` (`wait_eq`, :104/:161), then `__syncthreads` (:163). This is ordered under PTX. | `BAR.SYNC; MEMBAR.ALL.GPU; RED.E.ADD.STRONG.GPU` / `LDG.E.STRONG.GPU; CCTL.IVALL; BAR.SYNC` | A single elected thread releases and acquires for the CTA, and the acquire is a load, not an RMW. R3 finds no start or end point in the accessing threads, and `BAR.SYNC` is CTA-scope. |

The per-group class of each candidate is in `eval/results/cutlass/summary/groups_classified.tsv`. Triage write-ups:
- `eval/cutlass/triage/splitk.md` (K1–K5)
- `streamk.md` (S1a, S1b, S2)
- `new_groups.md` (the 18 groups that appeared after the first roll-up, all in the clusters above)

**(c): detector or harness defects producing a candidate.** None. Harness defects that cost runs but produced no candidate are listed in §5's departures.

## §5 Per binary

Source: `eval/results/cutlass/summary/per_binary.tsv`, from `x9.csv`. Column meanings:
- **recordings:** manifest ids recorded (main and t5400 flavors).
- **wall** and **peak:** of those recordings.
- **analysis s:** summed per-kernel analysis time of both halves.
- **superseded:** recordings that timed out at 1,200 s or 5,400 s and were re-recorded at 5,400 s or split.
- **final timeouts:** single tests that still exceed 5,400 s.
- **total** row: sums, except max peak MB, which is the maximum.

| binary | recordings | of them t5400 | wall s | max peak MB | kernels | launches | analysis s | superseded | final timeouts | no-kernel ids |
|---|---|---|---|---|---|---|---|---|---|---|
| conv_device_simt | 42 | 40 | 118,410 | 124,265 | 67 | 3,640 | 153,216 | 7 | 3 | 1 |
| conv_device_tensorop_f16_sm80 | 10 | 7 | 18,287 | 95,802 | 21 | 1,128 | 18,461 | 3 | 0 | 0 |
| conv_device_tensorop_f32_sm70 | 1 | 0 | 488 | 9,196 | 7 | 597 | 4,834 | 0 | 0 | 0 |
| conv_device_tensorop_f32_sm75 | 4 | 0 | 1,437 | 7,725 | 24 | 1,964 | 19,003 | 0 | 0 | 0 |
| conv_device_tensorop_f32_sm80 | 7 | 3 | 12,197 | 93,161 | 39 | 1,920 | 20,033 | 3 | 0 | 0 |
| conv_device_tensorop_f32_tf32_sm80 | 13 | 11 | 14,489 | 110,151 | 22 | 898 | 13,360 | 2 | 0 | 0 |
| conv_device_tensorop_f8_sm89 | 4 | 0 | 2,820 | 8,808 | 10 | 880 | 23,810 | 0 | 0 | 0 |
| conv_device_tensorop_s32 | 1 | 0 | 1,184 | 10,421 | 9 | 792 | 5,097 | 0 | 0 | 0 |
| conv_device_tensorop_s32_interleaved | 5 | 0 | 2,355 | 9,108 | 56 | 3,664 | 479,468 | 0 | 0 | 0 |
| epilogue_thread | 1 | 0 | 2 | 944 | 4 | 4 | 14 | 0 | 0 | 0 |
| epilogue_threadblock | 1 | 0 | 290 | 1,305 | 142 | 10,146 | 316,040 | 0 | 0 | 0 |
| epilogue_warp | 1 | 0 | 2 | 323 | 0 | 0 | 0 | 0 | 0 | 1 |
| gemm_device_blas3 | 9 | 6 | 17,516 | 5,261 | 278 | 5,490 | 346,955 | 3 | 0 | 0 |
| gemm_device_blas3_gaussian | 1 | 0 | 274 | 3,399 | 6 | 114 | 300 | 0 | 0 | 0 |
| gemm_device_broadcast | 1 | 0 | 150 | 2,148 | 3 | 3 | 21 | 0 | 0 | 0 |
| gemm_device_gemm_with_fused_epilogue_tensorop | 3 | 0 | 1,147 | 4,616 | 13 | 3,460 | 174,335 | 0 | 0 | 0 |
| gemm_device_grouped | 1 | 0 | 1,050 | 4,875 | 14 | 14 | 345 | 0 | 0 | 0 |
| gemm_device_grouped_blas3 | 22 | 21 | 11,541 | 4,828 | 20 | 20 | 3,093 | 2 | 0 | 0 |
| gemm_device_grouped_rank_2k_scheduler | 2 | 1 | 2,704 | 3,529 | 16 | 1,280 | 12,571 | 1 | 0 | 0 |
| gemm_device_grouped_scheduler | 1 | 0 | 811 | 3,328 | 16 | 1,280 | 5,436 | 0 | 0 | 0 |
| gemm_device_mixed_input_tensorop_sm80 | 1 | 0 | 441 | 7,671 | 37 | 824 | 50,614 | 0 | 0 | 0 |
| gemm_device_simt | 2 | 0 | 482 | 5,481 | 211 | 1,976 | 80,903 | 0 | 0 | 0 |
| gemm_device_simt_3x | 3 | 1 | 2,268 | 4,021 | 20 | 2,388 | 180,536 | 1 | 0 | 0 |
| gemm_device_sparse_tensorop_sm80 | 1 | 0 | 118 | 3,816 | 21 | 168 | 4,625 | 0 | 0 | 0 |
| gemm_device_tensorop_f16_sm80 | 1 | 0 | 30 | 2,338 | 4 | 48 | 110 | 0 | 0 | 0 |
| gemm_device_tensorop_f32_sm80 | 4 | 0 | 2,070 | 11,729 | 268 | 3,848 | 282,525 | 0 | 0 | 0 |
| gemm_device_tensorop_f32_sm80_3x | 12 | 11 | 12,303 | 36,226 | 9 | 1,161 | 87,132 | 2 | 1 | 0 |
| gemm_device_tensorop_f32_tf32_sm80 | 1 | 0 | 1,065 | 10,791 | 118 | 2,136 | 191,964 | 0 | 0 | 0 |
| gemm_device_tensorop_f64 | 2 | 1 | 2,505 | 10,337 | 51 | 830 | 38,313 | 1 | 0 | 0 |
| gemm_device_tensorop_planar_complex | 2 | 0 | 840 | 3,448 | 12 | 3,024 | 28,881 | 0 | 0 | 0 |
| gemm_device_tensorop_s32_sm80 | 1 | 0 | 399 | 7,425 | 124 | 1,440 | 38,618 | 0 | 0 | 0 |
| gemm_device_tensorop_sm70 | 1 | 0 | 106 | 1,849 | 105 | 1,068 | 69,034 | 0 | 0 | 0 |
| gemm_device_tensorop_sm75 | 2 | 0 | 340 | 1,915 | 234 | 3,391 | 69,809 | 0 | 0 | 0 |
| gemm_device_tensorop_sm89 | 1 | 0 | 113 | 3,537 | 40 | 312 | 5,912 | 0 | 0 | 0 |
| gemm_device_tensorop_sm89_blockwise | 1 | 0 | 2 | 975 | 2 | 2 | 3 | 0 | 0 | 0 |
| gemm_device_wmma | 1 | 0 | 365 | 3,337 | 276 | 3,244 | 212,375 | 0 | 0 | 0 |
| reduction_device | 13 | 0 | 1,525 | 4,174 | 40 | 11,756 | 583,037 | 0 | 0 | 0 |
| reduction_kernel | 1 | 0 | 3 | 968 | 4 | 60 | 114 | 0 | 0 | 0 |
| reduction_thread | 1 | 0 | 1 | 854 | 3 | 3 | 2 | 0 | 0 | 0 |
| **total** | **181** | **102** | **232,130** | **124,265** | **2,346** | **74,973** | **3,520,899** | **25** | **4** | **2** |

Final timeouts (TIMEOUT1). These single tests exceed 5,400 s under the tool and are not analyzed:
- `conv_device_simt`:
  - `SM80_Device_Conv2d_Fprop_Analytic_ImplicitGemm_f32nhwc_f32nhwc_f32nhwc_simt_f32.128x128_8x4_32x64x8`: 91 kernel launches recorded by 5,400 s; 17.7 s natively.
  - `SM80_Device_Conv2d_Fprop_With_Broadcast_Analytic_…_simt_f32.128x128_32…`: 136 launches; 15.2 s natively.
  - `SM80_Device_Conv2d_Fprop_With_Residual_Block_Plus_Analytic_…_simt_f32…`: 136 launches; 16.1 s natively.
- `gemm_device_tensorop_f32_sm80_3x`:
  - `SM80_Device_Gemm_tf32t_tf32n_f32n_tensor_op_f32.128x128x32_64x64x64_profiling`: 1 launch; 5.4 s natively.

No-kernel ids:
- `epilogue_warp-all`: 7 tests pass (natively and under racecheck); the tool records 0 kernel launches.
- `conv_device_simt-c00s03s01` (`SM60_Device_Depthwise_conv2d_Fprop_Direct_Conv_FixedStrideDilation_f16…simt_f16.64x64`): 0 kernels under the tool, rc 0 in 3.8 s, though it passes natively (2.5 s). This is an anomaly, not explained.

Departures from the brief, and losses:
1. **Chunking.**
   - Whole binaries that exceed 1,200 s were recorded as gtest chunks (`-cNN`, `x9_chunks.py`).
   - Timeouts were re-recorded at 5,400 s.
   - A multi-test chunk that timed out again was split into single tests (`x9_rechunk.py`, ids `<id>sNN`). 25 recordings were superseded this way.
   - A t5400 collect's wall includes about 73 min of per-id post-processing (atomic-scope sidecar) on top of the tool cap.
2. **grouped_blas3** was recorded as a suite sample: the first test of each of its 20 suites (`grouped_blas3_suite_firsts.txt`). It is not all 62 tests, because one launch took about 140 s under the tool. The other 42 tests are not recorded.
3. **epilogue_threadblock chunks c00–c08** duplicate `epilogue_threadblock-all` (169 tests, 10,146 launches, 142 kernel names). They are recorded but not analyzed (DUPLICATE in `x9.csv`).
4. **Harness defects fixed during the run.**
   - At the gate, `x9_record.sh` exported a shard knob that `blib` drops, so the serial sync pass ran. Fixed by `BASELINE_HB_SHARDS=16`; meta records the applied value.
   - The timeout-floor wrapper (above).
   - The dot pruning of unalignable CFG dots (`x9_prune_dots.py`). Unpruned equals pruned on both gate ids.
   - The reproducer at first linked cudart statically, so the collector could not resolve `cudaDeviceGetStreamPriorityRange`. It now links `-cudart shared`.
5. **Node time lost.**
   - **About 20.5 h idle (11-02 00:54 to 21:35).** My dispatcher restart sat behind a wait loop that matched its own command line, so nothing was submitted.
   - **32 analysis jobs failed within seconds (11-02/03)** on c14, c15, c35 and c36, which lack `/usr/local/cuda-13.3`. The dispatcher did not check analysis job states, so 99 recorded ids went unanalyzed until 11-03. They were then resubmitted, and all completed.
   - **Analysis job 324929** hit the 1-day limit and was resubmitted with SKIPDONE.
6. **Nodes.**
   - Excluded: the brief's list (c0–c2, c11–c13, c18, c21–c23, c34, c37, c46, c54) and c14, c15, c35, c36 (no CUDA 13.3).
   - From 11-03 17:15, c4–c47 (the Xeon Silver 4110 class, reserved for C6b by the coordinator), with an X9 ceiling of 7 nodes.
   - Recording and racecheck ran on GPU partitions `rtx4060ti16g,rtx4060ti8g`. The green set (0b) ran on a GPU node because it records GPU fixtures.
7. **The two sm70 binaries were not recorded with the rest** (an omission found at the end). They were recorded on 11-06 (jobs 328440 gemm_device_tensorop_sm70-all, 1,068 launches, 105 kernel names; 328441 conv_device_tensorop_f32_sm70-all, 597 launches, 7 kernel names) and analyzed by 328449 (c60, 2:44:28) and 328456 (c57, 0:36:26), both COMPLETED. Their results are in every table above.

## §6 What remains unverified

- **Thread and CTA identities.** For every candidate, "inter-CTA" comes from the source; the pair records carry no thread or CTA ids. A vector-clock run (not authorized) or the kept `hb_events` would settle it.
- **SASS of the reported unit-test cubins.** It was not dumped at the reported pcs. The SASS constructs above come from probes compiled from the tag's headers with the same CUDA 13.3 (`triage/streamk_bprobe.cu`, `triage/splitk_semprobe.cu`) and from the reproducer.
- **Observable impact of the finding.** None was observed on the RTX 4060 Ti: 400/400 runs, including a 20 µs `__nanosleep` before the release. Other GPUs and future compilers were not tested.
- **Fixed reproducer under the detector.** It cannot be shown clean in either mode (§3). racecheck was not run on the fixed reproducer, and perturbed runs per split were not done separately.
- **Not analyzed:**
  - the 4 TIMEOUT1 tests
  - the 42 grouped_blas3 tests outside the suite sample
  - `conv_device_simt-c00s03s01` (0 kernels under the tool)
- **reduction_device-c10 `__k000`/`__k001`.** Their verdict CSVs are empty, because the job was cut off while writing. Their pair files exist and show 0 pairs in both halves. The verdict column of `x9.csv` says `missing` for those 4 rows.
- **Launch counts.** For the 104 kernels with no pairs the pair file has no launch count. `x9.csv` takes it from the sub-store's `meta.json` (`x9_split.launches`, equal to its count of kernel JSONs on all 104; `summary/launches_from_substores.tsv`). No launch count is missing.
- **sm_90a kernels** (103 test files): not built, not run.
- **"Already known?" coverage.** Limited to the queries listed in `known_fixes.md` and the dossier §10. Some large GitHub result sets were only partly read.
- **The verifier did not re-run the GPU experiments.** It re-derived the source and PTX argument; the run results are as the dossier reports them.

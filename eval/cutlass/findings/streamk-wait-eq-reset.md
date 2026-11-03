# Finding S1b: stream-K partials are read with no acquire after `Barrier::wait_eq_reset` (CUTLASS v4.8.1, sm_89)

Triage cluster: S1b in `local/triage/streamk.md`, class (a), DR.
Abbreviations: `SK` = `include/cutlass/gemm/kernel/gemm_universal_streamk.h`, `BH` = `include/cutlass/barrier.h`, `BS` = `include/cutlass/block_striped.h`, `EBS` = `include/cutlass/epilogue/threadblock/epilogue_base_streamk.h`.
All line numbers are at tag `v4.8.1` (`git describe` = `v4.8.1`, WSL tree `/home/jeffery/x9-cutlass-v4.8.1`).
Results from runs that have not happened yet are written **pending run**. Facts that could not be obtained are written **missing**.

## 0. Verdict after re-checking

The claim survives. Under the PTX memory consistency model, the finishing CTA's plain loads of a peer's partials are not causality-ordered after the peer's stores. The pair is conflicting and not morally strong, so it is a data race (§8.7.1). Section 4 gives the derivation and section 11 the strongest objection.

On sm_89 hardware this is likely formal-only. The release side is correct. On the acquire side the SASS is missing only the L1 invalidate and the GPU-scope membar. In this access pattern the finisher CTA has no earlier L1 copy of the partials that could be stale. Section 9 covers this; no wrong output is expected.

## 1. The two accesses

### Path A: cooperative finisher (`reduction_blocks == 0` or atomic strategy; `SK:956-981`)

| role | file:line (innermost → kernel) | instruction (reported SASS) |
|---|---|---|
| write W (first peer) | `BS:194` (`BlockStriped::store`) ← `SK:772` (`share_accumulators`, `block_idx == first_block_idx`) ← `SK:968` | `STG.E` plain (also `.64`, `.U16` for other element types) |
| write W' (later peer, ≥3 peers only) | `functional.h:943` (`atomicAdd`) or `:992` (`red…f16x2`) ← `BS:229/260` ← `SK:790` | `RED…STRONG.GPU` |
| read R (finisher) | `functional.h:134/177/202` or `complex.h:202` (inlined `plus`) ← `BS:181` (`BlockStriped::load_add`) ← `SK:813` (`acquire_accumulators`) ← `SK:976` | `LDG.E` plain |

Synchronization between them:
- Producer: `SK:794` `Barrier::arrive_inc` → `BH:187` `__syncthreads()`. Then thread 0 runs `BH:191` `red_release`: `BH:123` `fence.acq_rel.gpu`, then `BH:124` `red.relaxed.gpu.global.add.s32`.
- Consumer: `SK:809` `Barrier::wait_eq_reset(…, first_block_idx, num_carry_in)`. Thread 0 spins at `BH:175` `while(atomicCAS(flag_ptr, val, 0) != val) {}`, then all threads reach `BH:178` `__syncthreads()`.

### Path B: separate reduction (kMixed strategy, `sk_blocks > 2*sk_tiles`, `sk_waves < sm_occupancy`; `SK:982-997`, `SK:867-928`)

| role | file:line | instruction |
|---|---|---|
| write W (every SK peer) | `BS:194` ← `EBS:181` (`EpilogueBaseStreamK::share`) ← `SK:989` | `STG.E.128` |
| read R (reduction block) | `BS:165` (`BlockStriped::load`) ← `EBS:133` (first peer) / `EBS:144` (other peers) ← `epilogue.h:332` ← `SK:920` (`epilogue.reduce`) ← `SK:1070` | `LDG.E.128` |

Synchronization between them:
- Producer: `SK:992` `Barrier::arrive_range_inc` → `BH:204` `__syncthreads()`. Then threads `< kAccumulatorFragments` each run `BH:208` `red_release`.
- Consumer: `SK:885-889` `Barrier::wait_eq_reset(…, tile*kAccumulatorFragments + frag, num_peers)`, i.e. `BH:175`, then `BH:178`.

## 2. Template instantiation and launch shape

### Reported kernels

The reports come from every `GemmUniversalStreamk` instantiation that the unit tests run. `test/unit/gemm/device/testbed.h:548-580` (`TestAllGemm`) re-wraps every `device::Gemm` under test as `GemmUniversalAdapter<GemmUniversalStreamk<Mma, Epilogue, ThreadblockSwizzleStreamK>>`. It then runs `TestAllGemmUniversal` (`testbed_universal.h:436-530`) in `kGemm` mode with `batch_count` ∈ {1, 2, 3, 5, 7}, which is the split-K override of the stream-K swizzle, on m, n ∈ {align, ~512} and three k values.

Representative reported kernel, id `cutlass-gemm_device_simt-SM50_device_sgemm_nt_L0_64x64x8_64x32x1_8x8_8x4_1x2`, cubin `simt_sgemm_nt_sm50.sm_89`:
`cutlass::Kernel2<cutlass::gemm::kernel::GemmUniversalStreamk<MmaPipelined<GemmShape<64,64,8>, …float, ColumnMajor… float, RowMajor…, MmaSimt<GemmShape<64,32,8>…>>, epilogue::threadblock::Epilogue<…LinearCombination<float,1,float,float>…>, ThreadblockSwizzleStreamK>>`.
- Block: `kThreadCount` = 64 threads (2 warps). Static shared memory: 8,192 B. `kAccumulatorFragments` = 8. `sizeof(AccumulatorTile)` = 256 B per thread. These values were printed by a host-only build of the same instantiation.
- Grid of the reported launches: **missing**. The pair records hold pcs, frames and SASS but no CTA or thread ids or launch dims. `hb_events` is on the cluster only.

### Reproducer instantiation (`repro.cu`)

`cutlass::gemm::device::GemmUniversal<float, ColumnMajor, float, RowMajor, float, RowMajor, float, OpClassSimt, Sm50, GemmShape<64,64,8>, GemmShape<64,32,8>, GemmShape<1,1,1>, LinearCombination<float,1,float,float>, ThreadblockSwizzleStreamK, 2>`.
- Through `DefaultGemmUniversal`'s `SelectBase<Swizzle, Swizzle::StreamkFeature>` (`kernel/default_gemm_universal.h:253-259, and :378-384 for complex`), this selects `GemmUniversalStreamk` with the same Mma, Epilogue and swizzle as the test's adaptor.
- The kernel's mangled name is `Kernel2<DefaultGemmUniversal<…>>`, a class derived from `GemmUniversalStreamk`, not `Kernel2<GemmUniversalStreamk<…>>`. The device code is the same `GemmUniversalStreamk::operator()`. In the local SASS, the stock finisher sequence is `ATOMG.E.CAS.STRONG.GPU; @P0 BRA; WARPSYNC; BAR.SYNC; LDG.E R0, [R68.64+0x3f00]`. The reported pair's read is `LDG.E R0, [R68.64+0x3f00]`, the same operand.
- Problem: M = N = 128, K = 256. That gives 2×2 tiles of 64×64, `iters_per_tile` = 32, beta = 0, and small-integer inputs, so the expected error is exactly 0.
- `split=2`: 8 SK blocks, 4 regions × 2 blocks, `reduction_blocks` = 0, so Path A. Each tile has one first peer (stores) and one finisher (`wait_eq_reset` + `load_add`).
- `split=3`: 12 SK blocks, 4 regions × 3 blocks. 12 > 2·4, so `reduction_blocks` = 4·8 = 32, provided `sk_waves` (1) < `sm_occupancy`, so Path B.
- The grid is padded to `avail_sms` SK slots plus the reduction blocks. A host-only computation with an assumed 142 SMs and occupancy 8 gave 142 blocks for split 2 and 174 for split 3. The binary prints the real composition from a host copy of the swizzle on the run GPU (RTX 4060 Ti): split=2 → 34 blocks, 4 SK regions × 2 SK blocks, 0 reduction blocks; split=3 → 66 blocks, 4 regions × 3, 32 reduction blocks.
- Not exercised: the ≥3-peer cooperative turnstile, where the writer is the RED at `SK:790` (rows `functional.h:943/992 × 134/177`). It occurs only with real stream-K (split = 1, unaligned) or the atomic strategy. The consumer side is identical (`SK:809`).

## 3. Concrete thread pair (reproducer, `split=2`, tile 0)

`get_block_idx()` (`threadblock_swizzle_streamk.h:704-728`) maps `blockIdx.x` to a linear block as `region*2 + block_in_region`, where `div_mod_sk_regions(block_in_region, region, blockIdx.x)`. `remap_block_indices` is false here: 8 active blocks is not more than 2·SMs.
- Tile 0 is region 0, with iterations 0-31.
  - Linear block 0 (`blockIdx.x = 0`) runs iterations 0-15. It is the tile's first block and does not finish, so it calls `share_accumulators` → `BS:194` store into `partials_workspace + 0*kThreadCount` (in units of `AccumulatorTile`).
  - Linear block 1 (`blockIdx.x = 4`) runs iterations 16-31 and finishes. `!tile_started`, so it calls `acquire_accumulators` with `first_block_idx = 0`, `num_carry_in = 1`.
- `BlockStriped` uses the same index `(BlockThreads*i) + thread_idx` in `store` (`BS:194`) and `load_add` (`BS:181`).
- **Pair:** (CTA `blockIdx.x=0`, thread j) `STG` of stripe i at `BS:194` × (CTA `blockIdx.x=4`, thread j) `LDG` of the same stripe at `BS:181`/`functional.h:134`, for any j in 1..63 and any stripe i. Thread j = 0 of the consumer is also unordered; its program order has the CAS but no acquire.
- Path B (`split=3`, tile 0): SK peer CTA thread j `STG.E.128` (`BS:194` via `EBS:181`) × reduction CTA (linear index `dp_start + sk_blocks…`, reduce_idx 0..7) thread j `LDG.E.128` (`BS:165` via `EBS:133/144`). Both sides use `this->thread_idx` with `kBlockThreads` striping.
- That the reported pairs are inter-CTA is established from the source, not from the records (see section 2).

## 4. Why nothing orders them (PTX ISA, Memory Consistency Model)

Section names are from the current PTX ISA (docs.nvidia.com/cuda/parallel-thread-execution), read on 2026-11-03.

1. **Consumer instructions.**
   - `BH:175`'s `atomicCAS` lowers to `atom.global.cas.b32` with no `.sem` and no `.scope`. Shown in the probe: `probe/bprobe.ptx:141` `atom.global.cas.b32`, `:146` `bar.sync 0`, `:150` `ld.global.f32`.
   - Per the `atom` instruction description, an absent `.sem` means `.relaxed` and an absent `.scope` means `.gpu`. I took this from the ISA text but could not re-fetch it in this session because the page fetch truncated. It is strong (relaxed) at gpu scope, but it is not an acquire.
2. **"Release and Acquire Patterns" (§8.8).** An acquire pattern on M is one of:
   - an acquire operation on M;
   - a strong read on M followed in program order by an acquire operation on M;
   - a strong read on M followed in program order by an acquire memory fence;
   - observing completion of an async strong read followed by an acquire fence.

   Thread 0's CAS is a strong read on the flag. What follows it in program order is the loop branch, then `bar.sync`. Neither is an acquire operation or an acquire fence on M, so **no acquire pattern exists.**
3. **Producer side is a correct release pattern.** In thread 0, `fence.acq_rel.gpu` (`BH:123`) is followed by a strong write `red.relaxed.gpu` (`BH:124`) on the flag. That is "a release or acquire-release memory fence followed by a strong write on M in program order".
   - Other threads' stores reach it through `bar.sync` (`BH:187`). "Memory synchronization" (§8.9.4) item 2: `bar{.cta}.sync` synchronizes with `bar{.cta}.sync` on the same barrier. Then program order.
   - So each producer `STG` precedes the `red` in base causality order.
4. **"Memory synchronization" (§8.9.4), item 4.** "A release pattern X synchronizes with an acquire pattern Y, if a write operation in X precedes a read operation in Y in observation order, and the first operation in X and the last operation in Y are morally strong." The consumer has no Y, so the flag hand-off creates **no synchronizes-with edge** across CTAs.
5. **"Causality Order" (§8.9.5).** X precedes Y in causality order if:
   - X precedes Y in (proxy-preserved) base causality order, or
   - for some Z, X precedes Z in observation order and Z precedes Y in base causality order.

   Take X = producer `STG` and Y = finisher `LDG`:
   - Base causality order would need a program-order, synchronizes-with or transitive path from X to Y. The only cross-CTA link would be the missing synchronizes-with (point 4). `bar.sync` synchronizes only within the CTA.
   - The observation-order clause needs X to precede some Z in observation order. "Observation Order" (§8.9.2) is defined from a write W to a read R that is morally strong with W and reads its value, closed through atomics. The weak `STG` is morally strong with nothing, and it is not on the flag's location. So that clause does not apply.

   **X and Y are not related in causality order.**
6. **"Conflict and Data-races" (§8.7.1).** "Two conflicting memory operations are said to be in a data-race if they are not related in causality order and they are not morally strong."
   - W and R overlap and W is a write, so they conflict.
   - R is a plain `ld.global` with no `.relaxed` or `.acquire` qualifier, so it is not strong. The pair is therefore not morally strong ("Morally strong operations", §8.7).
   - **Data race.** The same holds when W is the RED at `SK:790`, which is strong, because R is still weak.
7. **`bar.sync` as a fence does not help.** Suppose `bar.sync` were read as a CTA-scope acq_rel fence after the CAS. The resulting acquire pattern's last operation would have CTA scope, which does not include the producer thread in another CTA. It would not be morally strong with the producer's gpu-scope release, so item 4 still yields nothing.
8. **The fix restores the pattern.** Adding `fence.acq_rel.gpu` in thread 0 after the CAS loop gives "a strong read on M followed by an acquire memory fence", which is an acquire pattern. The CAS reads the value of a release-pattern write chain (observation order through the RMWs), so release synchronizes with acquire. Then `fence → bar.sync → LDG` is base causality order within the CTA, giving `STG <causality LDG`. This is the same shape the producer comment at `BH:121-122` relies on, mirrored. Section 7 shows the fix in SASS.

**Separate reduction path.** Same analysis, with `arrive_range_inc` (`BH:204` `bar.sync`, then `BH:208` per-flag `fence.acq_rel.gpu; red.relaxed.gpu`) and `wait_eq_reset` at `SK:885`. Also a DR.

**Every caller of `wait_eq_reset` at the tag** (`grep -rn wait_eq_reset include/`):
- Definition: `BH:168`. Forwarding wrappers: `BH:260` and `BH:297` (`NamedBarrierManager::wait_eq_reset` / `wait_eq_helper<true>`), and `BH:356-357` (`SyncManager::wait_eq_reset`). No caller of either wrapper exists in `include/`.
- 2.x stream-K kernels, all `cutlass::Barrier` = `GenericBarrier<SyncthreadsSync>`. All in scope for sm_89:
  - `gemm/kernel/gemm_universal_streamk.h:809` (finisher), `:885` (reduction block)
  - `gemm/kernel/gemm_streamk_with_fused_epilogue.h:813`, `:941`, `:1983`, `:2095` (two kernel variants)
  - `gemm/kernel/gemm_universal_with_visitor_streamk.h:592`, `:639`
- CUTLASS 3.x stream-K (out of the sm_89 scope; for the upstream note):
  - `gemm/kernel/sm90_tile_scheduler_stream_k.hpp` uses `NamedBarrierManager::wait_eq` (`:504`, `:520`, `:546`) and `wait_lt` (`:528`), both with `ld.global.acquire.gpu` (`BH:104`). It never uses `wait_eq_reset`.
  - `sm100_tile_scheduler_stream_k.hpp` (`:720`, `:949`) delegates to the sm90 `fixup_helper`.
  - **3.x is not affected by this defect.**

**History** (GitHub, read-only).
- The `wait_eq_reset` loop `while(atomicCAS(flag_ptr, val, 0) != val) {}` with no fence is in the 2.11 release commit `c975e2c` (2022-11-19) and unchanged on `main` today.
- In `c975e2c`, `wait_eq`/`wait_lt` used `ld.global.relaxed.gpu` and `red_release` used `red.release.gpu`.
- By `764b840` (2023-01-10, "streamk example and performance tuning", #760), `wait_eq`/`wait_lt` had been changed to `ld.global.acquire.gpu` and `red_release` to `fence.acq_rel.gpu` + `red.relaxed.gpu`, with the cumulativity comment. `wait_eq_reset` was left as is.
- So two of the three acquires were upgraded; this one was not.

## 5. The report's evidence

Source: `local/summary/groups.tsv`, plus a scan of all `wt-x9/eval/results/cutlass/pairs/main/*.json`. In every pair the kernel contains `GemmUniversalStreamk` and one innermost frame is an S1b read site.

| writer stack (innermost 3) | reader stack (innermost 3) | pairs | id\|cubin |
|---|---|---|---|
| `BS:194 > SK:772 > SK:968` | `functional.h:134 > BS:181 > SK:813` | 32,496 | 392 |
| `atomicAdd (sm_20_atomic_functions.hpp:84) > functional.h:943 > BS:229` | `functional.h:134 > BS:181 > SK:813` | 13,504 | 169 |
| `BS:194 > SK:772 > SK:968` | `functional.h:202 > BS:181 > SK:813` | 4,992 | 46 |
| `device_atomic_functions.hpp:107 > functional.h:943 > BS:229` | `functional.h:134 > BS:181 > SK:813` | 2,176 | 24 |
| `BS:194 > EBS:181 > SK:989` | `BS:165 > EBS:144 > epilogue.h:332` | 816 | 34 |
| `BS:194 > SK:772 > SK:968` | `complex.h:202 > complex.h:262 > functional.h:134` | 768 | 16 |
| `BS:194 > EBS:181 > SK:989` | `BS:165 > EBS:133 > epilogue.h:332` | 408 | 34 |
| **total, `pairs/main`** | | **55,160** | **454 ids** |

The triage counted 59,448 across `main` and `t5400`. Every pair is `status=CONFIRMED`. Both analysis halves (`on` = `CUVEIN_BARRIER_ORDER=1`, `off` = `=0`, per `x9_pairs.py:74`) give `verdicts=[RACE]`, `hb=[None]`, `conflict=[DR]`, `rt=[RAW]`, `syncs=[]`.

Representative records:
- Path A: `cutlass-gemm_device_simt-SM50_device_sgemm_nt_L0_64x64x8_64x32x1_8x8_8x4_1x2`, StreamK kernel.
  - a: pc 28704, `STG.E [R68.64+0x3f00], R67` (`BS:194 > SK:772 > SK:968 > SK:1081 > SK:1155 > SK:1127 > device_kernel.h:99`)
  - b: pc 29120, `LDG.E R0, [R68.64+0x3f00]` (`functional.h:134 > BS:181 > SK:813 > SK:976 > …`)
  - n = 4 per half. Same file: pc 27696 × 29136, n = 4.
- Path B: `cutlass-gemm_device_simt-all__k194`.
  - pc 4016 `LDG.E.128 R4, [R2.64+-0x20000]` (`BS:165 > EBS:144 > epilogue.h:332`) × pc 37328 `STG.E.128 [R132.64], R4` (`BS:194 > EBS:181 > SK:989`), n = 3
  - pc 3504 `LDG.E.128 R16, [R2.64]` (`EBS:133`) × the same store, n = 3
- The flag accesses themselves (`BH:104 × BH:124/175`) are reported as `SC` (informational). Not part of this finding (triage S2).

Detector model: CLAUDE.md D11, "consumer spins on the flag with no fence after it", is the same shape as the D11 cases `reduction-norace` and `norace_*fence*`. Policy: report and footnote.

## 6. Reproducer

Files: `local/findings/repro.cu` (**75 lines**, `wc -l`), `build.sh`. The device code is only the CUTLASS instantiation. The host code checks against a double-precision reference, prints `PASS`/`FAIL` with the max error, and returns 1 on FAIL (2 on CUDA or CUTLASS error).
- Usage: `repro [reps=1] [split …]`. Default splits `2 3`, i.e. Path A then Path B.
- D is pre-filled with NaN each rep, so an element that is never written counts as an error.

Local compile (no run): WSL, `nvcc` 13.3 (V13.3.73, `cuda_13.3.r13.3/compiler.38244171_0`), `-arch=sm_89 -lineinfo -std=c++17 -O3`, against `/home/jeffery/x9-cutlass-v4.8.1`.
- All three binaries build, with CUTLASS header warnings only.
- `build.sh`'s SASS check:

```
repro          ATOMG.CAS=2  CAS->MEMBAR.ALL.GPU within 6 instrs (12 dump lines)=0  NANOSLEEP=0
repro_fixed    ATOMG.CAS=2  CAS->MEMBAR.ALL.GPU within 6 instrs (12 dump lines)=2  NANOSLEEP=0
repro_perturb  ATOMG.CAS=2  CAS->MEMBAR.ALL.GPU within 6 instrs (12 dump lines)=0  NANOSLEEP=40
```

The two CAS sites are the reduction block (`0x07a0`) and the finisher (`0x7170`). Stock finisher:

```
/*7170*/ ATOMG.E.CAS.STRONG.GPU PT, R3, [R70], R2, R3 ;
/*7180*/ ISETP.NE.AND P0, PT, R3, R2, PT ;
/*7190*/ @P0 BRA 0x7150 ;
/*71a0*/ WARPSYNC 0xffffffff ;
/*71b0*/ BAR.SYNC.DEFER_BLOCKING 0x0 ;
/*71c0*/ LDG.E R0, [R68.64+0x3f00] ;          <- the partials load; no MEMBAR, no CCTL.IVALL
```

Run on ARC (sm_89 GPU job): `bash build.sh`, then the commands below.

| run | command | result |
|---|---|---|
| native output, stock | `./repro 200` | PASS: 0/400 runs wrong, max_err=0 (job 325921, RTX 4060 Ti, sm 8.9, driver 580.82.07; `runs/native_repro.txt`) |
| path composition printed | (first lines of the above) | split=2: blocks=34, sk_tiles=4, sk_regions=4, sk_blocks/region=2, dp_blocks=0, reduction_blocks=0 (cooperative finisher, SK:809/813); split=3: blocks=66, sk_regions=4, sk_blocks/region=3, reduction_blocks=32 (separate reduction, SK:885/920) |
| scalar-clock verdict, stock | detector on `./repro 1` | 1 kernel, 2 launches, 112 pairs, all RACE, conflict DR, RAW, `hb` None, no syncs (`eval/results/cutlass/pairs/repro/x9repro-streamk-repro.json`). By frames: 64 × (`BS:194` ← SK:772 ← SK:968) vs (`functional.h:134` ← `BS:181` ← SK:813); 32 + 16 × (`BS:165` ← `epilogue_base_streamk.h:144`/`:133` ← `epilogue.h:332`) vs (`BS:194` ← `epilogue_base_streamk.h:181` ← SK:989) — both S1b paths |
| collector-only verdict, stock | detector on `./repro 1` | the same 112 pairs, RACE / DR / RAW; status CONFIRMED for all 112 (scalar-clock ⊆ collector-only holds) |
| racecheck, stock | `compute-sanitizer --tool racecheck --racecheck-report all ./repro 1` | exit 0, "RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)" (`runs/racecheck_repro.txt`); racecheck checks shared memory only, so this says nothing about the global-memory pair |

Build note: the first job (325917) built with nvcc's default static cudart; the collector then failed to resolve `cudaDeviceGetStreamPriorityRange` (app rc 1 under the tool, 0 kernels recorded). `build.sh` now links `-cudart shared`, as the CUTLASS test binaries do; the results above are from that build (job 325921).

## 7. Minimal fix and the fixed reproducer

`local/findings/fix.patch`: a unified diff against `include/cutlass/barrier.h` at the tag. It adds one fence in thread 0 after the CAS spin, so that `atom (strong read) ; fence.acq_rel.gpu` forms an acquire pattern before the CTA barrier:

```diff
         while(atomicCAS(flag_ptr, val, 0) != val) {}
+#if (__CUDA_ARCH__ >= 700)
+        // Acquire pattern: the strong (relaxed) atom read above followed by an acq_rel fence.  (The fence
+        // also acquires for the other threads of the group, which read the data after the sync below)
+        asm volatile ("fence.acq_rel.gpu;" ::: "memory");
+#else
+        __threadfence();
+#endif
```

- Alternative with the same effect: `atom.acquire.gpu.global.cas.b32` via inline asm, or `cuda::atomic_ref<int, cuda::thread_scope_device>::compare_exchange_strong(…, cuda::memory_order_acquire)`. The fence form is chosen because it mirrors `red_release` and fixes all eight call sites, including those in `gemm_streamk_with_fused_epilogue.h` and `gemm_universal_with_visitor_streamk.h`.
- Fixed SASS (local compile): `ATOMG.E.CAS.STRONG.GPU ; @P0 BRA ; BSYNC ; MEMBAR.ALL.GPU ; ERRBAR ; CCTL.IVALL ; … BAR.SYNC ; LDG.E`, at both sites (`0x07b0` and `0x71d0`). The `CCTL.IVALL` (L1 invalidate) is what `wait_eq` already gets from `ld.acquire` (triage probe), and what stock `wait_eq_reset` lacks.
- Cost: one `MEMBAR.GPU` per finishing tile or reduction fragment, in one thread.

| run | command | result |
|---|---|---|
| native output, fixed | `./repro_fixed 200` | PASS: 0/400 runs wrong, max_err=0 |
| SASS check, fixed | `build.sh` sanity line | `MEMBAR.ALL.GPU` within 6 instructions after both `ATOMG.E.CAS` sites (2/2); stock 0/2 |
| scalar-clock verdict, fixed | detector on `./repro_fixed 1` | **still reported**: the same 112 pairs, RACE / DR / RAW, `hb` None |
| collector-only verdict, fixed | detector on `./repro_fixed 1` | the same 112 pairs, CONFIRMED |
| racecheck, fixed | `compute-sanitizer --tool racecheck ./repro_fixed 1` | not run (racecheck sees shared memory only; the stock run is clean) |

**Result: the brief's "fixed reproducer's clean run in both modes" is not met.** The fixed binary is reported exactly as the stock one. This is what the caution below predicted: the fixed hand-off is the S1a shape, which this detector does not certify. The fix's correctness therefore rests on the PTX argument (section 4) and the SASS, not on a clean detector run.

Caution for reading the fixed verdicts (written before the run): the fixed hand-off has exactly the elected-thread shape of triage S1a. The release reaches threads ≠ 0 through `BAR.SYNC` fan-in, and the acquire reaches them through `BAR.SYNC` fan-out. The triage explains why R3 and the barrier-only clock cannot certify S1a: no RMW on threads ≠ 0, and `BAR.SYNC` is CTA-scope. If the fixed binary is still reported, that is the S1a limitation (class (b)), not evidence that the fix is wrong. Then "clean run in both modes" cannot be met by this detector, and the dossier should say so.

## 8. racecheck

Stock `repro`: 0 hazards (exit 0). `repro_fixed`: not run. Expectation, stated before the run: `compute-sanitizer --tool racecheck` analyses shared-memory accesses only. Both accesses here are global memory, so no racecheck report is expected for either binary.

## 9. Perturbation test

`local/findings/perturb.patch` (applied alone on stock `barrier.h`): in `arrive_inc` (`BH:189-192`) and `arrive_range_inc` (`BH:207-209`), each releasing thread waits about 20 µs with `__nanosleep` after the CTA barrier and before `red_release`.

Why this side: the race window is between the producer's partials becoming visible and the consumer's plain loads.
- Delaying the producer's *stores* relative to the flag is not possible without breaking CUTLASS's correct release side. The stores precede `bar.sync`, which precedes `MEMBAR.ALL.GPU`, which precedes `RED`.
- Delaying the release makes sure the consumer CTA is already spinning when the flag flips. Its `LDG`s then issue right after the successful CAS, with no `MEMBAR` or `CCTL.IVALL`. That is the tightest window the hardware allows.
- Delaying the consumer would only widen the gap and make a stale read less likely.

| run | command | result |
|---|---|---|
| native output, perturbed | `./repro_perturb 200` (both splits, 400 runs; the separate `… 2` / `… 3` runs were not done) | PASS: 0/400 runs wrong, max_err=0; `NANOSLEEP` ×40 in the SASS |

**Result: no wrong output was produced. The finding is formal-only on this GPU.**

**Plain statement.** I cannot construct a mechanism by which wrong output follows on sm_89 while CUTLASS's own synchronization is kept.
- The `RED`/`ATOMG` are performed at L2.
- The consumer's `LDG.E` issues after `BAR.SYNC`, which issues after the CAS returns, so there is no early load to reorder.
- The only stale source would be an L1 line in the finisher's SM that holds the partials' address from before the producer wrote them. In this kernel, each workspace slot is read once per launch by one CTA, and no earlier access by that SM brings it into L1 within the launch.

So a PASS from the perturbed binary is expected. If it passes, the finding is **formal-only**: a PTX data race with no observed wrong output. Nothing in this material establishes whether a future architecture or compiler would turn it into wrong output.

## 10. Already known?

- `local/docs/eval/cutlass/known_fixes.md` and the side-session web notes (`x9-known-fixes-web.md`, same content), section "Relevant to CUTLASS 2.x stream-K / Barrier / block_striped / semaphore": no issue or PR reports or fixes a memory-ordering bug in `barrier.h` `GenericBarrier` (`wait_eq_reset` included), `gemm_universal_streamk.h`, or `block_striped.h`. Nearest items:
  - #1781: inverted assert in `NamedBarrier::check_barrier_in_range`; not ordering.
  - #3650: separate-reduction broadcast iterator addressing; not ordering.
  - #2775: question on `semaphore.h` release without fence; unanswered, closed not_planned.
  - #3117/#3118: relaxed spin in a CuTeDSL example; a different file.
  - #2027: 3.x nondeterministic stream-K wait-count logic; a different defect.
- New searches this session (2026-11-03, GitHub search API via WebFetch, read-only):
  - `repo:NVIDIA/cutlass wait_eq_reset`: **0 hits** (issues and PRs).
  - `repo:NVIDIA/cutlass atomicCAS acquire`: 2 hits, #3763 (open PR) and #3764 (open issue). Both are about Example 77's MLA fused split-KV reduction. #3763 changes only `examples/77_blackwell_fmha/kernel/sm100_fmha_mla_tma_warpspecialized.hpp`: it replaces a hand-written `atomicAdd` + `atomicCAS` spin with `GenericBarrier::arrive_inc`/`wait_lt`, and mentions stream-K only as a user of the same pair. It does not touch `barrier.h` or `wait_eq_reset`.
  - `repo:NVIDIA/cutlass "barrier.h" fence`: 3 hits (#2098, #3763, #2081), none relevant.
  - `repo:NVIDIA/cutlass streamk acquire`: 1 hit (#3763).
  - Web search `cutlass "wait_eq_reset" atomicCAS acquire fence stream-k barrier`: no CUTLASS discussion found.
  - Commits touching `include/cutlass/barrier.h` on `main`: the latest is `0d2b201` (v4.3.5, 2026-01-08). `main`'s `wait_eq_reset` still has no fence (raw file read 2026-11-03).
- **Result: not known.** No issue, PR or commit found. Coverage is limited to the queries listed here and in known_fixes.md, where some large result sets were only partly read.

## 11. The skeptic's strongest objection and the PTX answer

**Objection.** "It is synchronized. The CAS is a gpu-scope strong RMW that reads the value written by the producer's release-pattern `red`. Causality order explicitly allows an observation-order step followed by base causality order. So `red →obs CAS →po bar.sync →sw bar.sync →po LDG` puts the release before the load, and the producer's stores precede the `red`. On hardware the `ATOMG` completes at L2 before `BAR.SYNC` lets the `LDG` issue, and nothing in L1 can be stale. Stream-K has passed CUTLASS's tests on every GPU since 2.11."

**PTX answer.**
1. The observation-order clause of "Causality Order" (§8.9.5) is `X →obs Z →bco Y`, where X is the observation-order source. It orders the `red` itself before the `LDG`, which the finding does not dispute.
   - The racing write is the producer's weak `STG`. For it, we need `STG →causality LDG`.
   - `STG →bco red` holds, but causality order is "base causality order combined with some non-transitive relations". The definition does not admit `bco ; obs ; bco` as a path. Base causality order crosses threads only through "synchronizes with" (§8.9.4), which needs an acquire pattern ("Release and Acquire Patterns", §8.8), and the consumer has none.
   - That is exactly what the producer side's `fence.acq_rel.gpu` provides on its side. Without the mirrored fence, the cumulativity that carries the other threads' stores (`BH:121-122`'s own comment) has nothing to synchronize with.
   - **By the letter of §8.7.1, the pair is a data race.**
2. The hardware argument is accepted as far as the evidence goes: the result is expected to be formal-only (section 9). It is not a PTX argument. The compiler emits `CCTL.IVALL` + `MEMBAR` only when acquire semantics are requested: compare `wait_eq`, the fixed binary, and the stock binary. The stock code relies on there being no stale L1 line, a microarchitectural property that PTX does not promise.
3. The tests passing is consistent with a formal-only race. The 2023 change to `wait_eq`/`wait_lt` (relaxed → acquire, section 4 History) shows the same file was moved to the PTX-correct pattern for the other two waits.

## 12. Notes for an upstream report

- Affected: the eight `wait_eq_reset` call sites listed in section 4, all 2.x stream-K kernels (sm70+).
- Unaffected: the 3.x sm90/sm100 stream-K schedulers, which use `wait_eq`/`wait_lt` (acquire).
- One-line fix in `GenericBarrier::wait_eq_reset` (section 7). Expected impact: none on results today, one `MEMBAR.GPU` per finishing tile.
- Frame it as a memory-model conformance fix with no observed wrong output (the perturbation run passed 400/400). Nothing is posted (D23).

## 13. Missing / pending

- Runs done in job 325921 (sections 6–9). Not done: racecheck on `repro_fixed`; perturbed runs per split.
- A clean detector run of the fixed reproducer cannot be produced (section 7).
- **Missing:**
  - grid and CTA ids of the reported launches (records hold no ids; `hb_events` is cluster-only)
  - `cuobjdump -sass` of the reported unit-test cubin, to confirm that the instructions between CAS and `LDG` in the reported kernel match the local reproducer SASS (the triage notes the CAS at pc 25088 and the `LDG` at 25184 in `tensorop_f16_sm80-all__k002`)
  - the verbatim PTX `atom` text for the `.sem`/`.scope` defaults (stated from the ISA, not re-fetched this session)

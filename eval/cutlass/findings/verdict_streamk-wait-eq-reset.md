# Verdict: S1b, stream-K `Barrier::wait_eq_reset` has no acquire (CUTLASS v4.8.1)

**CONFIRMED. Class (a): data race (DR) under the PTX memory consistency model. Formal-only on sm_89: no wrong output has been observed and no hardware mechanism is known.**

I checked the source independently in `/home/jeffery/x9-cutlass-v4.8.1`, where `git describe --tags` reports `v4.8.1`. I modified no files. I did not re-run the GPU experiments. The run results quoted in the dossier (sections 6-9) are taken as reported.

## Source check (every cited line matches the tag)

- `include/cutlass/barrier.h`
  - `:50-55`: `SyncthreadsSync::sync()` is `__syncthreads()`. `:213`: `using Barrier = GenericBarrier<detail::SyncthreadsSync>`.
  - `:117-125`: `red_release` is `fence.acq_rel.gpu` then `red.relaxed.gpu.global.add.s32`. The comment at `:121-122` says the fence also releases data weakly written by other threads before the last syncthreads.
  - `:96-105`: `ld_acquire` is `ld.global.acquire.gpu.b32`. It is used by `wait_lt` (`:143-155`) and `wait_eq` (`:158-170`).
  - `:168-179`: `wait_eq_reset`. Thread 0 spins on `while(atomicCAS(flag_ptr, val, 0) != val) {}` (`:175`), then `Sync::sync()` (`:178`). **No fence and no acquire.**
  - `:183-193` `arrive_inc` and `:197-210` `arrive_range_inc`: `__syncthreads()` first, then `red_release`.
- `include/cutlass/gemm/kernel/gemm_universal_streamk.h`
  - `:772`: the first peer does a `BlockStripedReduceT::store` of its partials.
  - `:794`: `arrive_inc`.
  - `:809`: the finisher calls `wait_eq_reset`, then `:813` `load_add` from the same workspace offset.
  - `:885-889`: `wait_eq_reset` on the reduction-block path.
  - `:982-997`: separate-reduction producer, `epilogue.share` then `arrive_range_inc`.
- `include/cutlass/block_striped.h`
  - `:165` `load`, `:181` `load_add`, `:194` `store`.
  - All three are plain C++ dereferences (weak `ld.global`/`st.global`) with the same index `(BlockThreads*i)+thread_idx`.
- `epilogue_base_streamk.h`
  - `:133` and `:144`: plain `BlockStripedT::load` on the reduce side.
  - `:181`: plain `BlockStripedT::store` on the share side.
- `grep -rn wait_eq_reset include/` gives exactly the dossier's list:
  - the definition at `:168`
  - the wrappers at `:260`, `:297` and `:356-357`
  - eight call sites: `gemm_universal_streamk.h:809,885`, `gemm_streamk_with_fused_epilogue.h:813,941,1983,2095`, `gemm_universal_with_visitor_streamk.h:592,639`

## PTX memory-model argument (re-derived)

Section numbers differ between ISA versions. The relation names below are those of the PTX ISA chapter "Memory Consistency Model".

1. **Consumer.** CUDA's `atomicCAS` lowers to `atom.global.cas.b32` with no `.sem` and no `.scope`. Per the `atom` instruction description, that defaults to `.relaxed` and `.gpu`. The CAS is therefore a strong read of the flag, but it is not an acquire.
   - The next instruction in program order is `bar.sync` (`__syncthreads`).
   - "Release and Acquire Patterns" defines an acquire pattern on M as one of: an acquire operation; a strong read followed by an acquire operation; or a strong read followed by an acquire fence. The CAS followed by `bar.sync` matches none of these.
2. **`bar.sync` does not stand in for the fence.** In "Memory synchronization", `bar{.cta}.sync` synchronizes only with `bar{.cta}.sync` of the same CTA.
   - Even if it is treated as a fence, it has CTA scope.
   - "Morally strong" requires each operation's scope to include the other's thread. A CTA-scope operation in the consumer does not include the producer thread in another CTA.
   - The synchronizes-with rule needs "the first operation in X and the last operation in Y are morally strong", so it is not met.
3. **Producer.** `fence.acq_rel.gpu ; red.relaxed.gpu` is a valid release pattern. The other threads' `STG`s reach it through `bar.sync` (synchronizes-with) and program order. So `STG ->bco red` holds.
4. **Causality order.** X precedes Y in causality order if X precedes Y in base causality order, or X precedes some Z in observation order and Z precedes Y in base causality order. Take X = the weak `STG` and Y = the weak `LDG`:
   - **Base causality order.** A path from X to Y needs a cross-CTA synchronizes-with edge. None exists, by points 1 and 2.
   - **Observation-order clause.** It needs X itself to be the source of an observation-order edge. Observation order is built from morally strong write/read pairs and RMW chains. A weak `STG` is morally strong with nothing.
   - The chain `red ->obs CAS ->bco LDG` orders the `red` before the `LDG`. That is not the racing write, and the definition does not compose `bco ; obs ; bco`. The dossier's section 11 answer is correct on this point.
5. **"Conflict and Data-races".** W (the `STG`, or the strong `RED` from a later peer on the 3+-peer path) overlaps R (the weak `LDG`), and at least one is a write, so they conflict. They are not related in causality order, and they are not morally strong because R is weak. **The pair is a data race.** This holds on both Path A (`SK:772 -> SK:813`) and Path B (`EBS:181 -> EBS:133/144`).
6. **The fix is sound.** Adding `fence.acq_rel.gpu` after the CAS loop in thread 0 forms "a strong read followed by an acquire fence", which is an acquire pattern.
   - The CAS reads the release write, or a later write in its RMW chain, so release synchronizes with acquire.
   - The rest of the path is base causality order: `fence ->po bar.sync ->sw bar.sync(thread j) ->po LDG`.
   - This mirrors the producer side, and it matches what `wait_eq`/`wait_lt` already get from `ld.acquire.gpu`. An `atom.acquire.gpu.cas` would work equally well.

## On the dossier's other claims

- **Classification.** Formal-only is the right call.
  - Reported results: stock, fixed and perturbed binaries each passed 400/400 runs with max_err 0.
  - Mechanism: `ATOMG` and `RED` are performed at L2, and the `LDG` issues only after the CAS returns and `BAR.SYNC` completes. The only stale source would be an L1 line, and in this access pattern no earlier read in the launch brings the partials into L1.
  - The missing `CCTL.IVALL`/`MEMBAR.GPU` is a reliance on microarchitecture that PTX does not guarantee, not an observed failure.
- **3.x not affected.** The 3.x schedulers use `wait_eq`/`wait_lt`, which use `ld.acquire`. This is consistent with the grep: there are no 3.x call sites of `wait_eq_reset`. I did not re-read the sm90/sm100 scheduler lines.
- **History and novelty** (dossier sections 4 and 10). Not re-verified; I did no GitHub queries. These claims do not bear on whether the race exists.
- **Caveats the dossier already states correctly:**
  - The fixed binary is still flagged by the detector, which is the S1a limitation (class (b)). It does not count against the fix.
  - The `atom` default-qualifier text was cited from memory, not re-fetched. Its content matches my understanding of the ISA.
  - The grid and CTA ids of the reported launches are missing.

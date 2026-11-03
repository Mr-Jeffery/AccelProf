# Stream-K triage (`cutlass::gemm::kernel::GemmUniversalStreamk`, CUTLASS v4.8.1, sm_89)

Source: `/home/jeffery/x9-cutlass-v4.8.1` (`git describe` = `v4.8.1`). `SK` = `include/cutlass/gemm/kernel/gemm_universal_streamk.h`.
Pair data: every stream-K pair in `wt-x9/eval/results/cutlass/pairs/{main,t5400}/*.json` was scanned (514 files, 77,046 pairs, all CONFIRMED, no same-pc pair). Every pair has one of the 11 call-stack shapes listed below. No other stack shape occurs.

## Verdict

| sub-cluster | pairs | pcs (innermost × innermost) | class |
|---|---|---|---|
| **S1a** first-peer store → later peer's atomic reduce | 17,152 | `block_striped.h:194` (SK:772) × `functional.h:943` / `:992` (SK:790) | **(b)**: ordered under PTX by a CTA-cumulative release/acquire hand-off the detector does not model |
| **S1b** partials (store or atomic reduce) → finisher's / reduction block's plain load | 59,448 | `194`(SK:772) × `functional.h:134/177/202`, `complex.h:202` (SK:813); `functional.h:943/992`(SK:790) × `134/177`(SK:813); `block_striped.h:194`(SK:989) × `block_striped.h:165`(SK:920) | **(a) DR**: there is no acquire after `wait_eq_reset`'s relaxed `atomicCAS` |
| **S2** flag word accesses | 446 | `barrier.h:104` × `barrier.h:124` (223), × `barrier.h:175` (223) | **not (a)**: all accesses are morally strong. This is the detector's informational SC output (D12/D2), not a finding |

Per-pair stacks (frames inside CUTLASS; `SK:1081 > 1155 > 1127` omitted, and present on every cooperative and separate-share stack):

```
32496  194 > SK:772 > 968           | 134 > SK:813 > 976        S1b
15680  194 > SK:772 > 968           | 943 > SK:790 > 968        S1a
15680  134 > SK:813 > 976           | 943 > SK:790 > 968        S1b
 4992  194 > SK:772 > 968           | 202 > SK:813 > 976        S1b
 2816  194 > SK:772 > 968           | 177 > SK:813 > 976        S1b
 1472  194 > SK:772 > 968           | 992 > SK:790 > 968        S1a
 1472  177 > SK:813 > 976           | 992 > SK:790 > 968        S1b
 1224  165 > SK:920 > 1070          | 194 > SK:989              S1b (separate reduction)
  768  194 > SK:772 > 968           | complex.h:202 > SK:813    S1b
  223  barrier.h:104 > SK:786       | barrier.h:124 > SK:794    S2
  223  barrier.h:104 > SK:786       | barrier.h:175 > SK:809    S2
```

## The code (all lines at v4.8.1)

The 2.x stream-K kernel uses `cutlass::Barrier = GenericBarrier<detail::SyncthreadsSync>` (`barrier.h:213`), not `cutlass::Semaphore`.

- Release, `arrive_inc` (`barrier.h:183-193`): all threads run `__syncthreads()` (:187). Then **thread 0** runs `red_release` (:191), which issues `fence.acq_rel.gpu` (:123) and then `red.relaxed.gpu.global.add.s32` (:124). `arrive_range_inc` (:198-210) does the same, except that threads `< count` each release one flag (:207-208).
- Acquire A, `wait_eq` / `wait_lt` (:153-164 / :137-149): **thread 0** spins on `ld.global.acquire.gpu.b32` (:104, called from :161 / :145). Then `__syncthreads()` (:163 / :148).
- Acquire B, `wait_eq_reset` (:168-179): **thread 0** spins on `atomicCAS(flag, val, 0)` (:175). Then `__syncthreads()` (:178). The fence is the question here. In PTX this is `atom.global.cas.b32`, which has no `.sem` (so relaxed) and no scope (so `.gpu`), and **no fence follows it**.
- Stream-K use, cooperative path (`SK:956-981`):
  - `share_accumulators` (:760-795): the first peer `store`s its partials (:772 → `block_striped.h:194`, plain `st.global`). Each later peer runs `wait_eq(..., first_block_idx, block_idx-first_block_idx)` (:786, turnstile) or `wait_lt(...,1)` (:780, atomic strategy), and then `reduce`s (:790 → `block_striped.h:229/260` → `functional.h:943` `atomicAdd` / `:992` `red.gpu.global.add.noftz.f16x2`). Every contributor then runs `arrive_inc` (:794).
  - `acquire_accumulators` (:800-814): the finishing CTA runs `wait_eq_reset(..., num_carry_in)` (:809), then `load_add` (:813 → `block_striped.h:181`; the plain load is attributed to the inlined `plus` at `functional.h:134/177/202` or `complex.h:202/262`).
- Separate reduction (`SK:982-997`, `:867-928`): an SK peer runs `epilogue.share` (:989 → `epilogue_base_streamk.h:181` → `block_striped.h:194`), then `arrive_range_inc` (:992). The reduction block (:1066-1070) runs `wait_eq_reset` (:885), then `epilogue.reduce` (:920 → `epilogue.h:332` → `epilogue_base_streamk.h:133` → `block_striped.h:165`).

The lowering was checked by compiling a probe that calls these exact `barrier.h` functions (`scratchpad/probe/bprobe.cu`, CUDA 13.3, `-arch=sm_89`):

```
arrive_inc:     STG.E ; BAR.SYNC.DEFER_BLOCKING ; @P0 EXIT ; MEMBAR.ALL.GPU ; ERRBAR ; CCTL.IVALL ; RED.E.ADD.S32.STRONG.GPU
wait_eq:        LDG.E.STRONG.GPU ; CCTL.IVALL ; @P0 BRA <spin> ; BAR.SYNC.DEFER_BLOCKING ; RED.E.ADD.F32.FTZ.RN.STRONG.GPU
wait_eq_reset:  ATOMG.E.CAS.STRONG.GPU ; @P0 BRA <spin> ; BAR.SYNC.DEFER_BLOCKING ; LDG.E      <- no CCTL.IVALL / MEMBAR
PTX:            atom.global.cas.b32 ; bar.sync 0 ; ld.global.f32
```

The reported SASS matches these opcodes: `LDG.E.STRONG.GPU` at :104, `RED.E.ADD.S32.STRONG.GPU` at :124, `ATOMG.E.CAS.STRONG.GPU` at :175, plain `STG.E` / `LDG.E` / `RED…STRONG.GPU` for the partials. I did not have the unit-test cubins locally, so the instructions *between* the CAS and the `LDG` in the real kernels are not shown here. In rep `tensorop_f16_sm80-all__k002`, the CAS is at pc 25088 and the `LDG` at 25184, which is 6 instruction slots. A `cuobjdump -sass` of that cubin (on the cluster) would confirm the probe for the real kernel.

## S1a: STG (SK:772) × RED (SK:790). Class (b)

**Accesses.** `block_striped.h:194` is a plain `STG.E` by every thread of the *first* peer CTA into workspace slot `first_block_idx`. `functional.h:943/992` is a `RED…STRONG.GPU` by every thread of a *later* peer CTA on the same element. They conflict (WAW), and one of them is weak.

**Ordering under PTX.** Write j for any thread of the first CTA, 0/0' for the thread-0s, and k for any thread of the peer:
`STG(j) –po→ bar.sync(:187)` and bar.sync synchronizes-with bar.sync at thread 0. Then `–po→ fence.acq_rel.gpu(:123); red.relaxed.gpu(:124)`, which is a release pattern. The peer's `ld.acquire.gpu(:104)` reads the flag value produced by an RMW chain that contains that `red`. That is observation order through atomic RMWs, both sides at gpu scope, so the accesses are morally strong. The release pattern therefore synchronizes-with the acquire operation. Then `–po→ bar.sync(:163)`, which synchronizes-with thread k's bar.sync, and `–po→ RED(k)`.
Each link is program order, barrier synchronizes-with, or release/acquire synchronizes-with. So `STG` precedes `RED` in base causality order, which makes it causality order. Fence cumulativity is what lets thread 0's fence carry the other threads' stores (CUTLASS's own comment at :121-122). **The pair is ordered, so it is not a §8.7.1 race.**

**Why it was not certified** (scalar-clock: `hb` = `None` in both halves; ORDERED would need R1, R3 or the barrier-only clock):
- R1 and the barrier-only clock fail. The pair is inter-CTA, and `BAR.SYNC` is a cta-scope fence (instance_gate.md §2). The barrier-only clock has no (ATOM) edges (§6).
- R3 fails, from `hb_proof.tex` §5 "R3 as implemented":
  - Release: the chain starts at "the PO-next RMW of u's thread … an instance with none has no release point: χ fails". Threads ≠ 0 of the first CTA execute no RMW after `:772`, because only thread 0 runs `red_release`. Their stores reach the release only through `BAR.SYNC`, and R3 has no barrier step before the first hop (only "program order to a later atomic of that thread").
  - Acquire: the chain "must land … on the PO-previous RMW q of v's thread". Peer threads ≠ 0 execute no RMW before `:790`. The only acquire is thread 0's `ld.acquire` (`LDG.E.STRONG.GPU; CCTL.IVALL`). That is a load, not an RMW, so it is not a chain node: Definition "Gate, chain" and (ATOM) are RMW→RMW only.
- I cannot tell from the docs what collector-only mode does. `sum_local.py` names only the two halves, and CLAUDE.md does not define "collector-only". By the proof's Definition "Happens-before", (ATOM) is RMW→RMW, so a vector-clock run would not join through an acquire *load* either.

**Named mechanism.** A CTA-cumulative release/acquire hand-off. Elected-thread release: `BAR.SYNC` fan-in, then thread 0 runs `MEMBAR.ALL.GPU; ERRBAR; CCTL.IVALL; RED.E.ADD.S32.STRONG.GPU`. Elected-thread acquire by a strong load: thread 0 spins on `LDG.E.STRONG.GPU; CCTL.IVALL`, then `BAR.SYNC` fan-out. Two parts are unmodeled: (i) a release point reached through a barrier and another thread's fenced RMW, and (ii) an acquire point that is an `ld.acquire` (non-RMW). If the evaluation instead treats (ii) as a PTX pattern the detector must support, this becomes (c). The minimal failing input is then the probe's `producer` + `peer` kernels: 2 CTAs, each with `STG`→`arrive_inc` and `wait_eq`→`atomicAdd`.

## S1b: partials → finisher / reduction-block load. Class (a), DR

**Accesses.**
- Writers: the first peer's plain `STG` (SK:772, `block_striped.h:194`), or a later peer's `RED…STRONG.GPU` (SK:790, `functional.h:943/992`), or, in separate reduction, an SK peer's plain `STG.E.128` (SK:989).
- Reader: every thread of the finishing CTA (SK:813), or of the reduction block (SK:920), with a plain `LDG.E`.
- The writer is strong in some pairs, but the reader is always weak, so no pair is morally strong.

**Ordering under PTX.** The writer side is a correct release pattern, the same chain as S1a up to the `red` at `:124` (or `arrive_range_inc` :204/:208). The consumer is thread 0's `atom.global.cas.b32` (relaxed, gpu), then `bar.sync` (:178), then a weak `ld`.
- An acquire pattern needs an acquire operation, or a strong read followed by a `fence.acq_rel`/`fence.sc` (or `fence.acquire`) in program order. Neither is present.
- `bar.sync` is not a fence. Even read as a cta-scope fence, it is not morally strong with a gpu-scope release by a thread of another CTA.
- So no synchronizes-with edge leaves the producer CTA. Observation order (`red` → CAS) enters causality order only at its start, and it is not followed here by a base-causality path from a release. No causality order relates writer and reader.
- The pair is conflicting, unordered and not morally strong, so **it is a data race under PTX §8.7.1**. This is the D11 shape: "consumer spins on the flag with no fence after it — no acquire under PTX" (CLAUDE.md, D11 and T12 notes; same as `reduction-norace`).
- SASS: `ATOMG.E.CAS.STRONG.GPU` with no `CCTL.IVALL`. Compare `wait_eq`, which emits `LDG.E.STRONG.GPU; CCTL.IVALL`. Inside `barrier.h`, the spin in `wait_eq_reset` is the only acquire with no acquire semantics.
- A `fence.acq_rel.gpu` (or `__threadfence()`) in thread 0 after the spin at :175 and before :178 would make it an acquire pattern. This follows from the PTX definitions above and was not tested.
- Whether stale data is observable on hardware is not decided by this material. The `LDG.E` is L1-cacheable and is not preceded by an L1 invalidate.
- Known fixes: neither known-fixes list has an issue or PR on `GenericBarrier` ordering (known_fixes.md "Relevant to CUTLASS 2.x stream-K").

**Why the detector reported it:** consistent with the model, since nothing could certify it (no acquire, and R3 fails as in S1a). Under D11 it should be reported and footnoted, not relabelled.

## S2: flag word `barrier.h:104` × `:124` / `:175`. Not (a)

**Accesses** (all on the 32-bit flag `barrier_workspace[first_block_idx]`):
- :104 is thread 0 of a later peer CTA polling in `wait_eq` (SK:786): `ld.global.acquire.gpu.b32`, `LDG.E.STRONG.GPU`.
- :124 is thread 0 of another contributor in `arrive_inc` (SK:794): `red.relaxed.gpu.global.add.s32`, `RED.E.ADD.S32.STRONG.GPU`.
- :175 is thread 0 of the finishing CTA in `wait_eq_reset` (SK:809): relaxed gpu `atom.cas`, `ATOMG.E.CAS.STRONG.GPU`.

**PTX §8.7.1.** All three are strong at gpu scope on the same, fully overlapping 4-byte location, inside one GPU. Each scope therefore includes the other thread, so every pair is **morally strong**. Morally strong conflicting accesses are not a data race, whether or not they are causally ordered. **S2 is not (a).** These are the synchronization variable's own polls and updates, racing by design.
- Some instances are causally ordered. Peer k's poll precedes peer k+1's `red` through k's `arrive_inc` and k+1's `wait_eq`.
- Others are genuinely concurrent: a poll that misses an earlier peer's `red`, or the finisher's CAS spin against peers' polls.

**Detector.** R2 gives class SC. D12 says scalar-clock mode "reports every barrier-unordered strong–strong pair R3 cannot certify as `sc` (informational)". D2 adds that it is counted as neither TP nor FP and that the column "also holds strong–strong pairs an atomic hand-off ordered (it cannot tell)". So the SC report is the documented output.
- Not (b): no ordering is needed for correctness.
- Not (c): this is the specified behaviour.
- Not (d): it is decidable from the source.

Record S2 as expected SC-informational. It is not a race finding.

## Uncovered-access check (S1)

- All 76,600 S1 pairs have one of the 9 stacks above. Every one goes through the hand-off paths: `share_accumulators` (SK:968), `acquire_accumulators` (SK:976), `epilogue.share` (SK:989) or `separate_reduction` (SK:920/1070).
- None goes through `do_epilogue` (SK:979), the DP-block branch (SK:1026-1053), or the tile-advance code (SK:1094-1108).
- No same-role pair occurs (no 194×194, no 134×134).

On the questions raised in the brief:
- **Own CTA reading its own partials.** By the source this cannot happen. The finisher reads slot `first_block_idx * kThreadCount` (:812) only when `!tile_started()` (:973), so `first_block_idx ≠ block_idx`. A CTA writes only the slot of a tile it started and did not finish. Because its iteration range is contiguous (`get_iter_extents`, :1058), that is at most its last tile, which it processes first: tiles are walked backwards, :1105-1107.
- **Slot or flag reuse across tiles in one launch.** None. Each block is the "first, not finishing" peer of at most one tile. The flag is reset to 0 by the CAS (:175).
- **Data-parallel tail.** DP blocks never touch the workspace (DP tiles finish inside the block, giving the `do_epilogue` path).
- **Limit of this check.** The pair records hold pcs, frames and SASS but no thread or CTA ids. "Inter-CTA" is established from the source, not from the records. The stored `hb_events` would decide it directly, and those exist only on the cluster.

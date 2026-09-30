# T12: the instance gate (I4) and R3's release point from the trace

Branch `feat/instance-gate` (base `cuVein` f61c389). Design note: `design/instance_gate.md`. Proof:
`design/proof/hb_proof.tex` (Definition "Gate" O2 sentence, §5 R3 amendments, §6 containment
paragraph, §7 I4 row). Hardware: RTX 4060 Ti (sm_89, driver 580.82.07, CUDA 13.3) on
`rtx4060ti16g` for every GPU step; CPU re-scores on `normal`. Python: `.env/bin/python`.

## Headline

- **Implemented** in `sync_dominance.py` (the predicate `fenced`, the fence inventory, R3),
  `atomic_scope_sidecar.py` (the gate table the engine reads), `hb_oracle.py` and `HbEngine` (the
  gated (ATOM) generator with the deferred acquire), `design/algorithms_check.py` (the direct-evaluation
  reference). Default: the instance gate; `YOSEMITE_HB_GATE=trusting` / `--gate trusting` /
  `CUVEIN_GATE=trusting` keep the pre-T12 behaviour; a dump without `hb_gate` (every pre-T12 dump)
  replays under the trusting gate unless told otherwise.
- **O2 answered:** a `cta`-scope acquire RMW emits nothing (identical SASS to relaxed, sm_89 and
  sm_86); the gate then requires an explicit fence after it. Everything else of the inventory
  confirmed (§1).
- **Correctness evidence:** oracle under the trusting gate = the 32 recorded ScoR dumps' `hb_races`
  exactly; oracle (deferred acquire, as the engine) = Detect with the gate evaluated directly on
  32/32 litmus traces; engine = oracle on the whole green set recorded under the instance gate
  (297 passed, 2 skipped, 0 xfail), including a new kernel that exercises the held-conflict path in
  both directions; the default tool path is byte-identical up to device addresses (§3).
- **Re-score of the kept stores (464 programs with an RMW, no GPU; §4):** no pc pair lost, 9 new DR
  and 377 new SC pairs, all explained. The **8 ScoR fence/scope races** move from `latent-sc` to `sc`
  (reported in this run; SC because ScoR's data is `volatile`, T10) -- the brief's "latent ->
  structural" in T10's vocabulary. `race_interblock_none-lock_rtraw` stays unreported by the gate
  (its hand-off is fully fenced). `matrix-multiplication-norace`: unchanged clean, and its two
  scalar-clock `sc` reports are now `ordered` (the success-edge fence). `reduction-norace` becomes a
  Race-alone report through the ticket idiom (D11, iGUARD agrees) -- as predicted. New and not
  predicted: the five ScoR `norace_*fence*` kernels whose consumers spin without a fence become
  reported (four SC, one DR: `hrd-indirect`, D11, no baseline agrees).
- **R3:** the trace release point alone certified none of the 23 `no-release-point` pairs; the
  acquire side failed the same region test. With the acquire point also taken from the trace and a
  covering rule (both beyond the brief's step 3, said so in §5) all 20 rule-110 pairs are `ordered`;
  the 3 reduction pairs are the ticket idiom (not ordered, correctly).
- **Memory (T5a's three programs, `HB_STATS`, §6):** Indigo3 CC push 1296n: trusting gate 118.5 GB
  peak and killed (rc 1) in its first big kernel; instance gate 14.4 GB, all 5 kernels, 159 s.
  reduction-large 7.1 -> 1.9 GB, 17 -> 6 s. tiled_gemm (no atomics) unchanged. What is left in CC
  push is barrier-join `vc` (13.8 GB) -- T5b's.

## 1. The fence inventory (O2)

Probe `eval/instance_gate/o2_probe.cu` (24 kernels: relaxed/acquire/release/acq_rel/seq_cst RMWs
and CAS loops at block/device/system scope, the libcu++ fences, the legacy `__threadfence*`, the
legacy CAS locks, a shared-memory block-scope RMW), compiled on node c39:

```
PATH=/usr/local/cuda-13.3/bin:$PATH nvcc -std=c++17 -arch=sm_89 -cubin -O3 -o probe_sm_89.cubin o2_probe.cu
cuobjdump -sass probe_sm_89.cubin        # likewise sm_86; listing: eval/instance_gate/o2_probe.sm_89.sass.txt
```

sm_86 and sm_89 give the same opcode sequence per kernel (hash of the ATOM/MEMBAR/CCTL/ERRBAR/BAR
lines, registers stripped: identical). The table is in `design/instance_gate.md` §2. The facts the
gate rests on:

| PTX | SASS (sm_89 = sm_86) |
|---|---|
| `fence.sc.cta` | `MEMBAR.SC.CTA` |
| `fence.{acquire,release,acq_rel}.cta` | `MEMBAR.ALL.CTA` |
| `fence.sc.gpu` / `.sys` | `MEMBAR.SC.{GPU,SYS}; ERRBAR; CCTL.IVALL` |
| `fence.{acquire,release,acq_rel}.gpu` | `MEMBAR.ALL.GPU; ERRBAR; CCTL.IVALL` |
| `atom.release.{gpu,sys}` | `MEMBAR.ALL.{GPU,SYS}; ERRBAR; ATOM` |
| `atom.acquire.{gpu,sys}` | `ATOM; CCTL.IVALL` |
| `atom.release.cta`, `atom.acq_rel.cta` | `MEMBAR.ALL.CTA; ATOM` |
| **`atom.acquire.cta`, `atom.relaxed.cta`** (and the CAS forms) | **`ATOM…STRONG.SM`, nothing else** |

Inventory used (`sync_dominance.fence_scope`): release side `MEMBAR.{SC,ALL}.{CTA -> block,
GPU/SYS -> grid}` and `BAR.SYNC/BAR.RED` (block); acquire side the same plus `CCTL.IVALL` (grid);
a guarded (`@P`) instruction never counts. A path that starts or ends at a barrier arrival crosses
it (design note §1: a barrier record has no memory effect of its own, and `bar.sync` has cta-fence
ordering at the arrival).

## 2. What changed

| file | change |
|---|---|
| `python/sync_dominance.py` | `_Ins` (guard kept by the parser), `fence_scope`, `gate_mode`/`dump_gate`, `HBGraph`: instruction graph, `fenced(p, q, s, side)`, `record_pcs`, `gate_table`; R3: `release_fence`, trace release/acquire points (`trace_rmw_points`), covering rule, `_cs_fenced` on `fenced(c, x, d, acq)`, `_before_acquire` (write-before-lock); ablations `CUVEIN_R3_TRACE_RELEASE`, `CUVEIN_R3_TRACE_ACQUIRE`, `CUVEIN_R3_BEFORE_ACQUIRE` |
| `python/atomic_scope_sidecar.py` | `# gate-kernel` / `# gate <rmw> rel|acq <kernel> <pcs>` lines (fenced pcs; intersected over cubins), `--gate` |
| `python/hb_oracle.py` | `gate=`; chain clock as a join, no publish when `rel = 0`, acquire deferred to the thread's next record with the held conflicts, T14's possible clock following the gate; `summary.gate` counters |
| `sanalyzer/src/tools/pc_dependency_analysis.cpp` | the same in `HbEngine` (gate table parsing, per-lane last pc, the gate state in the T14 window, `Released.has_clk`, `hb_gate` marker); the trusting path is the pre-T12 code |
| `design/algorithms_check.py` | the instance gate evaluated directly (look-ahead), `--gate=` |
| tests | `python/test_instance_gate.py` (new: 6 CFG unit tests, dump-gate, 32 deferral-vs-direct, 6 sidecar round trips, 2 GPU held-conflict engine==oracle); `test_relaxed_handoff_should_race` is a plain test (was the strict xfail); `test_sync_dominance.py` `_PTX_UNFENCED_NORACE` (the five kernels of §4.3 must be reported in vector-clock mode) |
| `python/testdata/gate_held.cu` | the held-conflict kernel (fenced / unfenced CAS after an acquire) |

## 3. Correctness checks

| check | result |
|---|---|
| oracle `--gate trusting` vs the recorded `hb_races` of the 32 ScoR dumps (main checkout) | 32/32 identical (`count`, `a2_uncertain` included) |
| `design/algorithms_check.py --gate=instance` (Detect, direct gate) vs oracle (deferred) | 32/32 equal (vector clock and barrier clock) |
| `design/algorithms_check.py --gate=trusting` | 32/32 equal |
| green set (worktree runtime, collector 5c503aa1, libsanalyzer d6cb4c7b; job 294255, c-node rtx4060ti16g) | **297 passed, 2 skipped** (the two ScoR-parametrised tests of `test_instance_gate.py`, collected before the artifacts existed; run afterwards on the login node: 47/47 passed) |
| `test_held_conflict_engine_matches_oracle[fenced|unfenced]` | pass: held >= 1; fenced: 0 reported; unfenced: the plain-store/CAS pair reported, engine == oracle |
| default tool path (no `YOSEMITE_HB_TRACE`), main vs T12 runtime, two ScoR programs (job 294134) | identical up to device addresses and dist histograms |

The green-set count: 287 + 1 (the former xfail) + 9 new = 297. Expected-with-reason changes in
the green set: `test_scor_microbenchmark` now requires a report on the five kernels of §4.3.

Commands:

```
sbatch -p normal eval/baselines/setup/t12_build.sh                        # private runtime
W=<wt> SKIP_DEFAULT=1 sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t12_check.sh
.env/bin/python design/algorithms_check.py --gate=instance ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_instance_gate.py
```

## 4. Re-score of the kept stores (no GPU)

Base: T10's `t10-after` store (evcand + full-2026-09-22, T10's selection; its vector-clock dumps
carry the T10 oracle's trusting-gate `hb_races`). `t12_rescore.py prepare` marks a program affected
iff some kernel of some dot has an RMW pc: 464 of 598 (P1 305, P2 41, P3 54, P4 28, P5 33, P9 3);
4 skipped (no `t10-after` dir: T9's oracle-OOM P1 1296n programs). The gated oracle re-scored all
464 without error (job 293648, 16 shards, 4-21 min each). Three analyses of the same programs
(`p_t12_analyze.sh`): **before** (t10-after, the three R3 switches off = the pre-T12 verdict layer
by construction), **r3only** (t10-after, R3 amendments on, trusting `hb_races`), **after**
(t12-after, both). Tables: `eval/results/t12-rescore/T12_RESCORE_TABLES.md`.

```
.env/bin/python eval/baselines/t12_rescore.py prepare                            (normal node)
W=<wt> sbatch --array=0-15 --exclusive eval/baselines/setup/p_t12_rescore.sh
W=<wt> WHICH=before|r3only|after IDFILE=eval/results/t12-rescore/ids_affected.txt \
    sbatch --array=0-31 eval/baselines/setup/p_t12_analyze.sh
.env/bin/python eval/baselines/t12_rescore.py tables
```

Not in the verdict comparison: `P9-mr-cuda` and `P9-fpc-cuda` (analysis still running / over the
4 h cap at the time of writing, as in T9/T10).

### 4.1 The gate on the race sets

Over the 464 programs: 35,812,519 RMW lane records, of which `rel = 0` 31,274,027 (87 %) and
`acq = 0` 27,640,820 (77 %) -- spin-loop retries (a retried CAS's previous and next record are the
same CAS) and counters with no fence (Indigo, reduction). **No conflict was ever held** by the
deferred acquire on the corpus (0 of 0): the held path is exercised only by `gate_held.cu`.
pc pairs: 8,904 -> 9,290; **0 lost, 9 new DR, 377 new SC, no class change** of an existing pair.

| program | new DR | new SC | why |
|---|---|---|---|
| P4 graph-connectivity-racy-small | 2 | 0 | unfenced RMW hand-offs (labelled racy) |
| P4 reduction-norace-{small,large} | 1 each | 2 / 1 | the ticket `atomicInc`: no fence between it and the next record (the shared store `amLast`) -- D11 |
| P4 reduction-racy-{small,large} | 1 each | 4 / 3 | the same idiom |
| P4 rule-110-racy-large | 0 | 346 | its planted fence omission: unfenced `EXCH`/`ADD` hand-offs on volatile data |
| P5, the 8 fence/scope races | 0 | 1 each | the planted fence/scope bug (T9-0 §3) |
| P5, 5 `norace_*fence*` kernels | 3 (hrd-indirect) | 1, 10, 1, 1 | the consumer spins without a fence (§4.3) |

### 4.2 Verdicts

before -> r3only (R3 alone): **no verdict moves in either mode**; class changes only (e.g. scalar-clock
`matrix-multiplication-norace-{small,large}` `sc` 2/3 -> none; `rule-110-norace-{small,large}`
scalar `sc` 2/18 -> none, vector `latent-sc` 2/18 -> `sc` 1/5; 4 P3 CC Pull programs scalar `sc` 4 ->
none; `uts-{norace,racy}-small` scalar +7 `sc`). The `latent-sc -> sc` of rule-110-norace is a
reporting artifact, not a new report: the same pc pair is in `hb_races` (SC) in some launches of the
program and was `latent-sc` in kernel_0; the program-level dedup keeps the first kernel's record,
which R3 now orders, so a later launch's SC record surfaces (checked kernel by kernel on the dump).

r3only -> after (the gate): Race u Latent: 1 new FP (`P5-norace_interwarp-block_fence-atom_hrd-indirect`,
vector-clock); Race alone: 2 TPs gained (`reduction-racy-{small,large}`), 3 new FPs
(`reduction-norace-{small,large}`, `hrd-indirect`), no TP lost. Scalar-clock: no change (the gate
does not exist there). Per suite (affected, labelled), vector-clock, Race u Latent / Race alone:

| pset | before | after |
|---|---|---|
| P1 | 93/0/0/169, 93/0/0/169 | unchanged |
| P2 | 8/5/0/26, 8/5/0/26 | unchanged |
| P3 | 0/0/12/36, 0/0/12/36 | unchanged |
| P4 | 9/0/2/7, 7/2/0/9 | 9/0/2/7, **9/0/2/7** |
| P5 | 3/16/0/12, 3/16/0/12 (sc 17/0) | 3/16/**1**/11, 3/16/**1**/11 (sc 17/**4**) |

(TP/FN/FP/TN over the affected programs with a label; sc = programs with an SC report, labelled
RACE / CLEAN.) Under ScoRD's notion (D2 amended: DR ∪ SC are reports) the 8 fence races are
detected with a report of this run instead of `latent-sc`, and the 4 SC `norace_*fence*` kernels
are reports.

### 4.3 Against the brief's expectations

| expected (brief step 4) | observed |
|---|---|
| the 8 ScoR fence races latent -> structural | `latent-sc` -> `sc` in all 8 (T10 made their volatile data strong; `structural` is the DR name, `sc` the SC one) |
| `race_interblock_none-lock_rtraw` stays latent | its race set is unchanged (fully fenced hand-off; genuinely ordered in the recorded schedule) |
| `matrix-multiplication-norace` clean | clean in both modes; its scalar-clock `sc` pairs are `ordered` now (success-edge fence counted by `fenced`) |
| `reduction-norace` reported through the ticket idiom (D11, iGUARD agrees) | yes: `structural` 1 (was `latent` 1) in both sizes; iGUARD RACE on both |
| `test_relaxed_handoff_should_race` passes | yes; strict xfail removed |
| every other move listed | §4.1: graph-connectivity-racy, reduction-racy, rule-110-racy (labelled racy), and the **five `norace_*fence*` kernels** (not predicted) |

The five (D11 candidates; footnote (9) in `make_tables.py`): `norace_interblock_fence_raw`,
`norace_interwarp_fence_raw`, `norace_interwarp_blkfence_raw` (SC), `norace_interwarp-block_fence_hrf-indirect`
(SC) -- a consumer `while (atomicExch(&flag, 0) == 0) {}` / `while (atomicAdd(&flag, 0) != k) {}` with no
fence before it reads `data`: no acquire pattern under PTX §8.7.1; the data is volatile, so the pair
is an unordered strong conflict. `norace_interwarp-block_fence-atom_hrd-indirect` (DR): the same spin,
then `atomicExch_block(&data[0], 3)` -- a block-scope RMW against the other block's device-scope RMW
on `data`, not morally strong, unordered: a data race by the letter. ScoR's HRF-indirect model orders
all five through the spin's dependency. No baseline reports them (racecheck, iGUARD, memcheck,
synccheck, initcheck: CLEAN). Scalar-clock mode stays silent on them (R3's acquire side is the
dependency reading).

## 5. R3

- **Release point from the trace** (`trace_rmw_points`): the PO-next RMW of each instance's thread;
  release-fenced iff `fenced(u, a, d, rel)`.
- **Acquire point from the trace** -- added, not in the brief. On `rule-110-norace-small` the release
  side of 0x1050 -> 0x1970 was certified (starts 0x1140 grid, 0x1190 block) but `po(n, 0x1970)` was
  false for every atomic: the reader is under a loop too, and the census's `no-release-point` was only
  the first gate those pairs failed. The chain now lands on the PO-previous RMW of each instance of
  `v` (0x1220 or 0x1310 there).
- **Covering rule** (release starts x acquire points): every start reaches some acquire point and every
  acquire point is reached; the cross product rejected rule-110's correct pairing (border threads hand
  off 0x1140 -> 0x1310 at grid scope, inner threads 0x1190 -> 0x1220 at block scope).
- **Write-before-lock decline** (`_before_acquire`): implemented; it moved no verdict on the corpus
  (not exercised, as the census predicted).
- `_cs_fenced` on `fenced(c, x, d, acq)`: the success-edge idiom is certified (matrix-multiplication).
- Result: all 20 rule-110 pairs `ordered` (18 large + 2 small; they were `latent-sc` after T10); the 3
  reduction pairs stay reported (the ticket idiom is acquire-unfenced).

## 6. Memory (`YOSEMITE_HB_STATS`, T5a's three programs)

Job 294289, node c73 (125 GB), T12 runtime, same helper as T5a/T9 (`t5a_stats.py`), instance gate
vs `YOSEMITE_HB_GATE=trusting`. Files: `eval/results/t12-stats/`.

| program | gate | rc | wall s | peak RSS | vc entries (bytes) | released entries |
|---|---|---|---|---|---|---|
| tiled_gemm N=256 (no atomics) | instance | 0 | 84.3 | 4.55 GB | 67.1 M (2.73 GB) | 0 |
| | trusting | 0 | 83.8 | 4.54 GB | 67.1 M (2.73 GB) | 0 |
| reduction-norace-large | instance | 0 | 5.9 | 1.85 GB | 7.9 M (0.32 GB) | 3.46 M |
| | trusting | 0 | 17.1 | 7.13 GB | 121.9 M (5.35 GB) | 6.78 M |
| Indigo3 CC push 1296n (300 s cap) | instance | 0 | 158.8 | 14.4 GB | kernel_1: 339.7 M (13.8 GB) | 0 (1,297 records, none published) |
| | trusting | **1** | 178.9 | **118.5 GB** | 1.38 G (60.7 GB) at record 16,000 of kernel_1 | 1.83 M |

The trusting run of CC push was killed in kernel_1 (the 125 GB node; the process exits rc 1 with no
further kernels); under the instance gate every RMW of that code has `rel = 0` (no fence), so no
chain clock is published or joined, and the kernel's remaining 13.8 GB is `vc` from barrier joins
(`sync_group` copies) -- T5b's regime. For the atomics-heavy engine-timeout programs the gate
removes the RMW-join growth; the barrier-only ones are untouched (tiled_gemm).

## 7. P4/P5 GPU sweep, both modes

<!-- filled from job 294290 -->

## 8. Latent census after T12

<!-- filled from the t12-census collect -->

## What remains unverified

- The containment paragraph (§6 of the proof) is an argument relative to the inventory: that every
  counted instruction lowers from a PTX fence (or the fence half of an acquire/release qualifier) of
  at least that scope is checked on the 24-kernel probe, not proved, and only for sm_86/sm_89.
- The held-conflict path of the engine is exercised by one purpose-built kernel only; the corpus
  never holds a conflict.
- T14's flag under the gate: when the other endpoint's RMW window closes between `r` and `t`'s next
  record, the decision is taken on `t`'s window alone (a possible under-flag relative to T14's
  definition; not measured, 0 held conflicts on the corpus means the case needs a pending acquire,
  which is exactly the held path).
- R3's acquire point and covering rule are pc-level: they assume the observed hand-offs are the ones
  each instance used (the pre-T12 rule assumed more: any one chain).
- A `thread_scope_block` libcu++ acquire without an explicit fence is reported (the binary cannot
  show the acquire); none such is known in the corpus (the measurement above found no
  program where only this rule moved a verdict), but it was not searched for separately.
- `P9-mr-cuda`, `P9-fpc-cuda`: not in the verdict comparison.
- Merge: `HbEngine` also changed in T5b (`perf/shared-base-clock`, unmerged); the gate's state lives in
  the T14 window and `released`, T5b's in `vc` -- expect a textual conflict in `process()`'s RMW
  block, not a semantic one; engine == oracle must be re-run after the rebase.

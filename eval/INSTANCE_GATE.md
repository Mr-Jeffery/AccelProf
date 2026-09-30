# T12: the instance gate (I4) and R3's release point from the trace

Branch `feat/instance-gate`, **rebased onto `cuVein` b3bfdf3 (T5b merged) on 2026-09-30**
(originally based on f61c389). Design note: `design/instance_gate.md`. Proof:
`design/proof/hb_proof.tex` (Definition "Gate" O2 sentence, §5 "R3 as implemented" and the verdict
matrix, fact (iv), §6 containment paragraph, §7 I4 row). Hardware: RTX 4060 Ti (sm_89, driver
580.82.07, CUDA 13.3) on `rtx4060ti16g` for every GPU step; CPU re-scores on `normal`. Python:
`.env/bin/python`.

## State after the rebase onto T5b and the review (2026-09-30; details in §9)

- **Engine on T5b's clock layout.** The gate's state (chain clock, held acquire `J`) is T5b's
  `VClock` (shared base + delta); T12's copy-on-write commit is dropped (T5b's representation
  makes the held `J` an O(delta) copy). Library `e527875d` (collector unchanged, `5c503aa1`).
  matrix-multiplication-small: **11.1 s instance vs 10.1 s trusting** (same node; 62 s pre-T5b).
- **Engine == oracle:** green set **305 passed, 2 skipped** (the 297 of §3 plus 8 new tests:
  R3 on hand-built CFGs, `write_before_lock.cu` on a real trace, R1's same-pc rule, the
  annotation); `gate_held.cu` re-recorded, held path both ways; Detect == oracle 32/32 under both
  gates; 55/55 gate tests on the fresh artifacts; T5b's parity set: **60 of 60 programs, 412 kernels, 7,497,797 records, 0 mismatches, 0 `tv_violation`** (recorded under the instance gate; the other 5 of the 65 ids exceed the 120 s floor, as in T5b's run).
- **R3 review (§9.3):** the rule is stated in `hb_proof.tex` §5 with its assumptions (R3a–R3c);
  write-before-lock and rtraw are declined (unit tests with each decline switched off, and real
  traces). The review found a hole older than T12: with many threads on the same pcs the chain
  can land directly on the reader's own unlock and `_past_release` (CAS acquires only) certified
  the rtraw race; closed (`CUVEIN_R3_LANDING=0` restores the old rule).
- **R1 and `model_bug` (§9.4):** R1 certifies no same-pc pair (the code's cycle form over-claimed
  pairs inside one barrier segment); `model_bug` is an annotation on the class's verdict.
  **uts-norace-small: CLEAN in both modes** (the 0x470 pair is `sc`, no annotation); it was RACE
  through the `model_bug` row in §7's sweep.
- **Re-score (§9.5), all 594 kept programs, no GPU:** the review's changes (R1's same-pc fix, the
  landing decline, the `model_bug` annotation) move **no verdict** in either mode at either
  operating point; class changes only in uts (scalar-clock: norace `sc` 7 -> 8, racy `race` 10 -> 11,
  `sc` 7 -> 8). The only `model_bug` annotations left are crs-cuda's old pre-T3b dump (142; a
  fresh recording is CLEAN, T3b).
- **P4/P5 GPU sweep with the rebased runtime (§9.6):** <<SWEEP>>
- **Memory on T5b's clocks (§9.2):** Indigo3 CC push 1296n 6.9 GB / 9.9 s trusting vs **1.3 GB /
  5.7 s instance** (`vc` 179 M -> 1.3 M entries, `released` 60 M -> 1.3 K); reduction-large and
  tiled_gemm equal under both gates.

## Headline (pre-rebase, 2026-09-29/30; superseded where §9 says so)

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
- **GPU sweep P4/P5, both modes, fresh recordings (§7):** 5 vector-clock TIMEOUTs now finish
  (graph-coloring/connectivity large, uts small), matrix-multiplication-small 62 -> 24 s;
  scalar-clock verdicts unchanged. One new vector-clock FP besides `hrd-indirect`:
  `uts-norace-small` (was TIMEOUT) is RACE through one `model_bug` on an SC pair -- R1's cycle form
  over-claims a same-pc pair inside one barrier segment, a pre-existing R1 defect the gate exposed
  (not fixed here). A 2x engine slowdown on spin locks found in the first sweep was fixed
  (copy-on-write chain clock, §7.1).
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
| green set (worktree runtime, collector 5c503aa1, final libsanalyzer dca547a5; job 294473, rtx4060ti16g; also job 294255 with d6cb4c7b, same result) | **297 passed, 2 skipped** (the two ScoR-parametrised tests of `test_instance_gate.py`, collected before the artifacts existed; run afterwards on the login node: 47/47 passed) |
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

`P9-mr-cuda` and `P9-fpc-cuda` hit the 4 h analysis cap or failed identically in all three analyses
(vector-clock TIMEOUT / ERROR), as in T9/T10; they compare equal and carry no information.

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
| P1 | 106/0/0/176, 106/0/0/176 | unchanged |
| P2 | 8/5/0/28, 8/5/0/28 | unchanged |
| P3 | 0/0/14/38, 0/0/14/38 | unchanged |
| P4 | 9/0/2/7, 7/2/0/9 | 9/0/2/7, **9/0/2/7** |
| P5 | 3/16/0/14, 3/16/0/14 (sc 17/0) | 3/16/**1**/13, 3/16/**1**/13 (sc 17/**4**) |
| P9 | no vector-clock verdict (fpc ERROR, mr TIMEOUT in all three analyses) | unchanged |

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
- **Write-before-lock decline** (`_before_acquire`): implemented; the three R3 amendments together
  moved no verdict on the corpus (before -> r3only, §4.2); whether the decline alone fired on any
  pair was not measured separately.
- `_cs_fenced` on `fenced(c, x, d, acq)`: the success-edge idiom is certified (matrix-multiplication).
- Result: all 20 rule-110 pairs `ordered` (18 large + 2 small; they were `latent-sc` after T10); the 3
  reduction pairs stay reported (the ticket idiom is acquire-unfenced).

## 6. Memory (`YOSEMITE_HB_STATS`, T5a's three programs)

Job 294475 (re-run with the final library dca547a5; the first run, job 294289 with d6cb4c7b, agreed within 1 %), node c73 (125 GB), T12 runtime, same helper as T5a/T9 (`t5a_stats.py`), instance gate
vs `YOSEMITE_HB_GATE=trusting`. Files: `eval/results/t12-stats/`.

| program | gate | rc | wall s | peak RSS | vc entries (bytes) | released entries |
|---|---|---|---|---|---|---|
| tiled_gemm N=256 (no atomics) | instance | 0 | 84.3 | 4.55 GB | 67.1 M (2.73 GB) | 0 |
| | trusting | 0 | 83.8 | 4.54 GB | 67.1 M (2.73 GB) | 0 |
| reduction-norace-large | instance | 0 | 5.0 | 1.85 GB | 7.9 M (0.32 GB) | 3.46 M |
| | trusting | 0 | 17.7 | 7.17 GB | 121.9 M (5.35 GB) | 6.78 M |
| Indigo3 CC push 1296n (300 s cap) | instance | 0 | 158.8 | 14.4 GB | kernel_1: 339.7 M (13.8 GB) | 0 (1,297 records, none published) |
| | trusting | **1** | 178.9 | **118.5 GB** | 1.38 G (60.7 GB) at record 16,000 of kernel_1 | 1.83 M |

The trusting run of CC push was killed in kernel_1 (the 125 GB node; the process exits rc 1 with no
further kernels); under the instance gate every RMW of that code has `rel = 0` (no fence), so no
chain clock is published or joined, and the kernel's remaining 13.8 GB is `vc` from barrier joins
(`sync_group` copies) -- T5b's regime. For the atomics-heavy engine-timeout programs the gate
removes the RMW-join growth; the barrier-only ones are untouched (tiled_gemm).

## 7. P4/P5 GPU sweep, both modes

One rep, the harness's 120 s cap, the 61 P4/P5 programs in both modes, fresh recordings
(`eval/baselines/setup/t12_eval.sh`, results `eval/results/t12-eval-{main,t12}/`, traces on BeeGFS
`t12-eval-{main,t12}`): the main runtime (cuVein f61c389's python, installed collector 7bafac9f and
libsanalyzer) in job 294290 on c53; the T12 runtime with the final library (collector 5c503aa1,
libsanalyzer dca547a5) in job 294481 on c1 (both rtx4060ti16g, same hardware; a first T12 run on
c53 with the pre-copy-on-write library d6cb4c7b is superseded, §7.1). 122 (id, mode) rows, **11
differ**; 9 are vector-clock rows, the 2 scalar-clock ones keep their verdict and differ in report
ids only (separate recordings, schedule differences):

| program | label | main | T12 | note |
|---|---|---|---|---|
| graph-coloring-norace-large | CLEAN | TIMEOUT (120 s, 3.2 GB) | CLEAN (19 s, 0.9 GB) | finishes |
| graph-coloring-racy-large | RACE | TIMEOUT | RACE (27 s), structural 14 | finishes |
| graph-coloring-racy-small | RACE | RACE (109 s), structural 12 | RACE (15 s), structural 13 | +1 pair, faster |
| graph-connectivity-norace-large | CLEAN | TIMEOUT (5.9 GB) | CLEAN (27 s, 1.1 GB) | finishes |
| graph-connectivity-racy-large | RACE | TIMEOUT | RACE (27 s), structural 9 | finishes |
| graph-connectivity-racy-small | RACE | RACE (17 s), structural 8 | RACE (2.4 s), structural 9 | +1 pair (re-score: 2 unfenced hand-offs) |
| uts-norace-small | CLEAN | TIMEOUT (12.5 GB) | **RACE (20 s)**: model_bug 1, sc 17 | finishes; new FP, see below |
| uts-racy-small | RACE | TIMEOUT (13.0 GB) | RACE (27 s): model_bug 2, structural 10, sc 17 | finishes |
| graph-coloring-racy-small (scalar-clock) | RACE | RACE | RACE | report ids differ (schedule) |
| uts-racy-small (scalar-clock) | RACE | RACE, race 10 | RACE, race 11 + sc 7 | report ids differ (schedule) |
| norace_interwarp-block_fence-atom_hrd-indirect | CLEAN | CLEAN | RACE, structural 3 | D11, §4.3 |

Every other row is identical, including all 8 ScoR fence races (`sc` 1 in both runs: in these fresh
recordings the pair is already reported under the trusting gate) and the four SC `norace_*fence*`
kernels (clean in both runs; the stored evcand traces of §4 are where the gate reports them; why
these recordings differ was not investigated).

**uts-norace-small (new Race verdict).** The one `model_bug` is an SC pair: two `volatile` stores
(`STG.E.STRONG.SYS`, pc 0x470) to one address by warps 5 and 6 of block 45, recorded at seq 4,212
and 19,625, both before the block's first barrier arrival (the same barrier segment). The gate
removed the ordering the unfenced `atomicAdd` hand-offs gave them; R1's cycle form
(`loop_scope(0x470)` = block, barrier 0x3cb0 on every cycle) claims them ordered, which is false
for two instances in one segment. So `model_bug` did its job -- it exposed a pre-existing R1
over-claim for same-pc pairs within one segment -- but `CLASS_VERDICT` maps `model_bug` to RACE
although the pair's class is SC. Not changed in T12 (verdict layer; a follow-up: R1's cycle form must
not claim a same-pc pair whose instances lie in one segment, and `model_bug` on an SC pair should
not count as a race). Under the trusting gate this program timed out, so the defect was invisible.

Not in the table because their verdict is unchanged: `matrix-multiplication-{norace,racy}-small`
now take 24 s / 8 s (main: 62 s / 65 s); `matrix-multiplication-*-large` and `uts-*-large` time out
in both.

### 7.1 A performance regression found and fixed

The first T12 run (library d6cb4c7b) turned `matrix-multiplication-{norace,racy}-small` into
TIMEOUTs (main: 62 s / 65 s). Profiled on c23 (`perf record`, job 294464): 223 s under the instance
gate vs 117 s under the trusting gate, 56 % of the time in clock hash-map copies/joins and
`malloc`/`free`. The gated path copied the full chain clock at every RMW (the held `J`) and built
each release record from two further copies; on a spin lock every failed CAS paid that. Fix
(c03d256): the chain clock is shared copy-on-write (`Released::clk` a `shared_ptr`, `Win::J` a
pointer to it), copied only while a snapshot still holds it. Same node, same binary: 24 s instance
vs 62 s trusting (job 294472). Green set with the fixed library: 297 passed, 2 skipped; Detect ==
oracle 32/32 (job 294473); the 47 ScoR-parametrised gate tests pass.

## 8. Latent census after T12

`latent_census.py collect --stores t12-after` (jobs 294291/294292, `normal`, the census's own caps)
then `tables --out eval/results/t12-census` (generated files there; `detail/` not committed, as in
T9-0). 554 programs with a vector-clock verdict (scalar-clock 593); `P9-mr-cuda` (scalar-clock, 113 GB) hit
the 4 h analysis cap, as in T9-0, and is not in them.

| | T9-0 (evcand, 3331d35) | after T12 (t12-after) |
|---|---|---|
| `latent` (DR) pc pairs | 50 on 20 programs | **0** |
| latent-only TPs | 10 (all P5) | 0 |
| latent FPs on race-free programs | 25 on 5 P4 programs | 0 |

Where the ten latent-only races of T9-0 went: 8 fence/scope races -> reported in the run (`sc`,
§4.3); `race_interblock_fence_rtraw` -> reported since T9 (I1); `race_interblock_none-lock_rtraw`
-> `latent-sc` (T10 made its data strong; its fenced hand-off orders it in the recorded schedule, so
it stays the one "ordered in this run only" case D8 describes). The 25 latent FPs: rule-110's 20 ->
`ordered` (R3, §5), matrix-multiplication's 2 -> `ordered` (the success-edge fence), reduction's 3
-> reported (`structural` 1 per size + SC; the ticket idiom, D11). This census version counts the DR
class only (`latent`); `latent-sc` (T10) is not one of its columns, and its TP/FP totals include the
effects of T9 and T10 as well as T12.

## 9. Rebase onto T5b and review (2026-09-30)

### 9.1 The rebase

`git rebase origin/cuVein` (b3bfdf3 = T5b merged; T5b changed only `HbEngine`, no Python). Two T12
commits touched the engine and conflicted:

- `02bed31` (was 6eb9c6a), the gate in `HbEngine`: resolved on T5b's file with T12's semantics
  re-applied in T5b's terms -- `Released` holds `VClock`s plus `has_clk` (⊥), the held acquire `J`
  and its possible-clock part are `VClock` copies (O(delta)), the close joins with `join_vc`, the
  gated publish builds the chain clock as a join (`join_vc` into a copy of the previous one, or
  `V(t)` when there is none), the trusting path is T5b's code unchanged.
- `cc8449f` (was c03d256), the copy-on-write chain clock: its engine change is dropped (T5b's
  `VClock` gives the same effect); the commit keeps its report and script changes.

The oracle, predicate, sidecar and verdict layer replayed without conflict. Rebased library
`e527875d` (GCC 12.4, `eval/baselines/setup/t12_build.sh`; the collector is unchanged).

### 9.2 Verification on the rebased engine

| check | result |
|---|---|
| green set + `test_instance_gate.py` (job 294732, all traces re-recorded incl. `gate_held`, `write_before_lock`) | **305 passed, 2 skipped** (the two ScoR-parametrised tests, collected before their artifacts; 55/55 afterwards on the login node) |
| `design/algorithms_check.py --gate=instance` / `--gate=trusting` (same job) | 32/32 / 32/32 |
| T5b's parity set (`setup/t5b_parity_ids.txt`, 65 ids, recorded with the rebased runtime, job 294662, 120 s floor; compared on CPU, job 294670) | **60 of 60 programs, 412 kernels, 7,497,797 records, 0 mismatches, 0 `tv_violation`** (P1 10, P3 10, P4 10, P5 10, P6 9, P7 1, PI 10; the green set's keys incl. `count` and `a2_uncertain`, `hb_races_sync_only`, the coherence profile, TV behaviour); the other 5 ids left no dump within the floor, the same 5 as T5b's run |
| matrix-multiplication-small wall (job 294671, c-node rtx4060ti16g, `perf` off) | instance **11.1 s**, trusting 10.1 s (pre-T5b: trusting 62 s; T12 before copy-on-write 223 s under `perf`, after 24 s) |

`HB_STATS` on T5a's three programs with the rebased library (job 294734, node c55, 125 GB;
`eval/results/t12-stats-rebased/`):

| program | gate | wall s | peak RSS | largest kernel: `vc` entries (bytes) | `released` entries |
|---|---|---|---|---|---|
| tiled_gemm N=256 (no atomics) | instance / trusting | 10.6 / 9.9 | 1.94 / 1.94 GB | 131 K (0.01 GB), 64 bases / same | 0 / 0 |
| reduction-norace-large | instance / trusting | 1.7 / 1.7 | 1.29 / 1.30 GB | 31 K / 254 K | 41.6 K / 52.8 K |
| Indigo3 CC push 1296n | instance / trusting | **5.7 / 9.9** | **1.33 / 6.93 GB** | **1.33 M (0.09 GB) / 179.3 M (3.05 GB)** | **1.3 K / 60.2 M (963 MB)** |

On T5b's representation the gate still removes nearly all of CC push's clock state (its RMWs
are unfenced, so they neither publish nor join); T5b alone takes the trusting run from
OOM to 6.9 GB.

### 9.3 R3: the review

The rule as implemented is stated in `hb_proof.tex` §5 ("R3 as implemented (T12)"): release
points and acquire points from the trace, release-fenced by `fenced`, hops, the covering rule, the
two declines, the CAS-section fence, and three assumptions -- (R3a) instances of a pc are ordered
alike (the observed hand-offs are the ones used; distances meet scopes only at the first hop),
(R3b) locks are CAS-acquired and released by another RMW on the same location, (R3c) the RMWs
around the observed instances are the same in every schedule.

What the review checked, on hand-built CFGs (`python/test_instance_gate.py`, `test_r3_*`) where
the trace facts are given exactly:

| shape | result | the decline that matters (switched off: certified) |
|---|---|---|
| lock hand-off (write in one section, read in the next) | certified | -- |
| write-before-lock, no fence before the lock | declined | no release point (scope none) |
| write-before-lock, fence before the lock | declined | `_before_acquire` (`CUVEIN_R3_BEFORE_ACQUIRE=0` certifies) |
| rtraw, two threads | declined | `_past_release`, CAS case (`CUVEIN_R3_PAST_RELEASE=0` certifies) |
| rtraw, many threads on the same pcs (a failed CAS hops to another thread's unlock) | declined | `_past_release`, landing case -- **new**: the pre-T12 `_past_release` certifies it (`[0xa0, 0x30, 0xa0]`) |
| fenced flag hand-off (no CAS on the location) | certified | -- |

And on real traces: `write_before_lock.cu` (new; block 0 writes, fences, locks; block 1, delayed,
locks and reads): vector-clock `latent`, scalar-clock RACE, `hb_chain` none; with
`CUVEIN_R3_BEFORE_ACQUIRE=0` both ORDERED with a chain -- passed in job 294732 (the schedule was
reached). The ScoR rtraw kernel keeps `test_write_after_unlock_is_event_candidate` green.

The hole: before T12 the acquire side was region dominance (`po(n, v)`), and the landing atomic
`n` could be the reader's own unlock reached by a hop, so the rtraw race was certified whenever
the aggregated edges held a failed-CAS -> unlock hop (any lock with more than two contenders on
shared pcs). T12's acquire point did not change that; `_past_release` now also fires when the
landing atomic is a non-CAS RMW on a CAS-acquired location and precedes `v`. The verdict moves
it causes are in §9.5.

### 9.4 R1 and the `model_bug` annotation

`uts-norace-small`'s `model_bug` (§7): R1's cycle form (`loop_scope`) certified a same-pc pair
because a barrier lies on every cycle through the pc's region -- which separates the pc's
instances in *different* iterations only. The two conflicting stores (warps 5 and 6 of block 45,
seq 4,212 and 19,625) were both before the block's first barrier arrival. The proof's R1 never
certifies a same-pc pair (one region; the empty path crosses no barrier), so the code now matches
it (`CUVEIN_R1_LOOP_SCOPE=1` restores the old form; unset = the fixed behaviour, the default); a
cross-iteration instance is ordered by the barrier-only clock where it runs. Named in the proof's
fact (iv) as a closed deviation.

`model_bug` is now an annotation: `_hb_class` returns the class (`structural` / `sc`), `judge`
sets `model_bug` on the verdict, the verdict is the class's (an SC pair with it is a Strong
conflict), `run_cuvein` writes `model_bug=<n>` beside `classes=`, `make_tables.py` shows it as an
informational column (rows written before keep the old `model_bug` class and their RACE);
`latent_census`, `classify_fp_causes`, `aggregate` read the annotation.

uts after the fix, from the §7 sweep's own dumps (`t12-eval-t12`, `run_cuvein._analyze_reports`):

| program | mode | R1 cycle form (CUVEIN_R1_LOOP_SCOPE=1) | R1 fixed (default) |
|---|---|---|---|
| uts-norace-small | vector-clock | CLEAN, `model_bug=1` (the 0x470 pair, `sc`) | **CLEAN**, `sc` 18, no annotation |
| uts-norace-small | scalar-clock | CLEAN (0x470 R1-ordered), `sc` 7 | CLEAN, `sc` 8 (0x470 reported `sc`) |
| uts-racy-small | vector-clock | RACE (structural 11), `model_bug=2` | RACE (structural 11) |
| uts-racy-small | scalar-clock | RACE (race 11, `sc` 7) | RACE (race 11, `sc` 8) |

### 9.5 Re-score of the kept stores

Store `t12-after` (the gated oracle's `hb_races`; the oracle is unchanged by the rebase, T5b
touched only the engine). Three analyses, all with this branch's verdict layer
(`p_t12_analyze.sh`, jobs 294682/294683 over all 594 programs, 32 shards; the 36 programs queued
behind P9 fpc-cuda and mr-cuda in shards 15 and 17 re-run separately, jobs 294836/294837, because
`parallel.py analyze` flushes a shard's CSV only at its end): `after` (§4's run, the pre-rebase
detector, 464 programs with an RMW), `r1old` (`CUVEIN_R1_LOOP_SCOPE=1 CUVEIN_R3_LANDING=0`: the
annotation alone), `final` (defaults). Tables: `eval/results/t12-rescore/T12_REVIEW_TABLES.md`
(`t12_rescore.py review`).

| step | programs | verdict moves (either mode, Race u Latent and Race alone) | class moves |
|---|---|---|---|
| `after` -> `r1old` (`model_bug` becomes an annotation) | 464 | none | none |
| `r1old` -> `final` (R1 certifies no same-pc pair; R3 declines a landing on the unlock) | 594 | none | uts-norace-small scalar-clock `sc` 7 -> 8; uts-racy-small scalar-clock `race` 10 -> 11, `sc` 7 -> 8 |

P9 fpc-cuda and mr-cuda: 4 h analysis cap / error in every analysis, as in T9/T10 (not compared).
The `model_bug` annotations left in `final`: P9 crs-cuda vector-clock, 142 -- its kept dump
predates T3b (no exit records), so its barrier segments never complete; recorded afresh it is
CLEAN in both modes (T3b). The landing decline moved nothing on the corpus: no judged pair of a kept program changed class
between `r1old` and `final` other than uts's same-pc pairs, so no certificate there rested on a
landing on an unlock; the decline is a soundness guard, pinned by the unit test.

### 9.6 P4/P5 GPU sweep with the rebased runtime

<<SWEEP_DETAIL>>

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
- R3 is a pc-level certificate under three assumptions stated in `hb_proof.tex` §5 (R3a instances
  ordered alike / observed hand-offs are the ones used; R3b CAS-acquired locks -- a test-and-set lock
  built from `EXCH` alone is not recognised; R3c the RMWs around the instances are the same in every
  schedule). None of them is checked; vector-clock mode vetoes an over-ordering R3 on a trace where
  an instance is unordered, scalar-clock mode cannot.
- The landing decline (§9.3) is exercised only by the hand-built unit test: no kept program's
  verdict or class depended on it.
- `write_before_lock.cu` forces block 0 first by a delay (no memory access); the test skips when the
  schedule is not reached. It was reached in job 294732.
- A `thread_scope_block` libcu++ acquire without an explicit fence is reported (the binary cannot
  show the acquire); none such is known in the corpus (the measurement above found no
  program where only this rule moved a verdict), but it was not searched for separately.
- `P9-mr-cuda`, `P9-fpc-cuda`: no vector-clock verdict in any analysis (4 h cap / error).
- The T5b merge is done (§9.1); engine == oracle re-checked on the green set and T5b's parity set.
  The five parity programs that exceed the 120 s floor (as in T5b's own run) are not compared.
- The re-score reads kept dumps: the gated oracle's `hb_races` there come from the oracle, not from
  the rebased engine; the engine's own `hb_races` are checked against the oracle only on the
  green-set and parity recordings.

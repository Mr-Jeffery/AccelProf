# T16 — The certain clock: a sound operating point without values

Branch `feat/certain-clock`, based on `cuVein` 3c7eefd (T19 `perf/flat-buckets` merged; the
installed runtime was rebuilt from that merge on 2026-10-11: libsanalyzer `a37ad29a`, collector
`619b788b`). Decision D16 (CLAUDE.md B3) taken: yes. Written 2026-10-11. Commits: e1832e5 (the implementation, amended with the tables fix) and the results commit that adds this report.
Hardware: RTX 4060 Ti 16 GB (sm_89, driver 580.82.07 / 580.95.05, CUDA 13.3) nodes of
`rtx4060ti16g` for every GPU run; `normal` nodes for the re-score. Private runtime of the branch
(nothing installed): libsanalyzer `adb1df48b81cddf6` (`sanalyzer/wt_install`, GCC 12.4.0,
`-g -O3 -mtune=znver4`), collector `bcd69d3f0e9e1d88` relinked from the d67ed41 install's objects
(T16 changes no collector or device source) with RPATH to that library.
Labels: **proved-in-effect** (an invariant checked over N real traces), **tested** (a specific
verdict asserted), **unverified**.

## Summary (the sentence for the paper)

**The sentence.** The certain clock is sound with respect to the execution under A2w — an RMW
has taken effect by its thread's next instrumented record — with the collector as it is: it
takes a happens-before edge between two RMWs only when the first one's issue window closed
before the second was issued, so every edge it takes is an edge of the execution's own
happens-before and, by monotonicity, every race of the execution is among its reports; what it
gives up is completeness on contended hand-offs, whose critical sections it reports as the
`a2_uncertain` population.

**The numbers.** On the kept vector-clock dumps of 594 + 97 programs (5,110 kernels) the certain
clock refuses 80 % of the 29.8 M chain edges of the evcand corpus (42.2 % are cross-warp
overlaps — `eval/A2_WINDOWS.md`'s 42 % — the rest the lanes of one warp instruction, which
always overlap) and 82 % of the 41.0 M on the exit-record dumps; its reports are a superset of
the recorded clock's on every kernel (the invariant, 0 violations), the recorded clock itself is
unchanged (parity 5,110 / 5,110), and what it adds is exactly the flagged population: 449 + 459
SC pc pairs on the ScoR applications' volatile data (`reduction`, `rule-110`,
`matrix-multiplication`), three SC pairs and one DR pair on the ScoR litmus — the rtraw race the
recorded lock hand-off had ordered — and nothing on P1, P2, P3, P6, P9 or PI. Under PTX
counting the Race (sound) column therefore equals Race alone on every program but
`race_interblock_none-lock_rtraw`, which it turns from Latent into a Race (a TP gained); no
verdict is lost. A certain run costs what a recorded run costs (four P7/P9 programs, ±1 %), so
the sound column on the realistic suites is a second run per program at the same price.

## 1. What it is

Three clocks can be computed from one trace. They differ only in which (ATOM) edges between two
RMWs `r -> q` on one location — `q` the next RMW on that location in the trace, `r` and `q`
morally strong — they accept:

| clock | accepts the edge `r -> q` | where |
|---|---|---|
| recorded (today's default) | always, in the trace's order | `HbClock`, `hb_oracle.py` |
| possible (the `a2_uncertain` flag, T14) | in every order the issue windows allow | the `pd` delta next to `vc` |
| **certain** (T16) | only when the windows do not overlap: `nx(r) <= pos(q)`, `nx(r)` the position of the next record of `r`'s thread (an exit record included) | `YOSEMITE_HB_GATE_POLICY=certain`, `--gate-policy certain` |

The decision at `q` is online: when `q` is processed, `r`'s thread has either produced a later
record (accept) or not (refuse). A refused edge is refused in both directions; the chain clock
`Ch_loc` breaks at `q`, which publishes its own clock and not `r`'s.

**One refinement, needed for the soundness argument.** Under A2w ("an RMW has taken effect by
its thread's next record") the windows decide only the order of `r` and `q`. An RMW `z` whose
window reaches `r`'s issue, or which is issued inside `q`'s window, may lie *between* `r` and `q`
in the execution's coherence order; the model's chain (`hb_proof.tex` Definition "Gate, chain")
steps only between morally strong RMWs, so such a `z` that is not morally strong with `r` and `q`
would break the execution's chain `r ~> q` while the certain clock had taken the edge. The edge is
therefore accepted only if every such `z` is pairwise morally strong with `r`, `q` and the other
such `z` — true at once when the location's RMWs all carry one scope (a lock word, a counter:
every `atomicX` is `.gpu`), false when a none-scope or a block-scope RMW of another block mixes
in. Because `z` may be issued inside `q`'s window, the decision is taken when `q`'s window
closes, exactly where the instance gate (T12) takes its acquire: the acquire `J` is held in `q`'s
window, the conflicts `J` would order are held with it and reported iff the edge is refused, and
`r`'s chain clock is attached to `q`'s publish iff the edge is accepted (no RMW issued inside
`q`'s window can accept an edge from `q`, their windows overlap, so none reads the chain part
early). The refused edges are counted by cause: `uncertain` (windows overlap; `open` of them:
the releaser's window never closed before the kernel's end — on a dump without exit records,
every thread's last RMW), `unsafe` (disjoint windows, a non-ms intermediate).

**Sub-relation (the argument, `hb_proof.tex` §7 "The certain clock").** Under A1, A2w and A3
every edge the certain clock takes is an edge of the execution's own happens-before: the
windows give `r <co q`, the RMWs co-between them are among the `z` above, and pairwise moral
strength makes them a chain of morally strong co-successors. The other generators do not depend
on the order of RMWs. Hence `->certain ⊆ ->hb(co)` and, by Lemma "Monotonicity",
`Rep_certain ⊇ Rep(co)`: no race of the execution is missed — sound with the collector as it is
— at the price of completeness on contended hand-offs. The same argument with `co = seq` gives
`->certain ⊆ ->recorded`, hence the invariant asserted on every re-scored kernel:
**`Rep_certain ⊇ Rep_recorded`** (a violation is a bug, not a result). The added instances are
those the recorded order ordered through a refused edge, which the possible clock flags: the
`a2_uncertain` flag is computed under the recorded join in both policies (the `pd` channel of a
publish carries what the recorded clock would publish), so what the certain clock adds is the
flagged population, and the unflagged instances are the same under both policies (**tested**,
§4).

The sync instance (`barrier_only_pairs`, `hb_races_sync_only`, scalar-clock mode) has no (ATOM)
edge and is untouched; `ms`, the buckets, publish-then-tick and the flag are untouched.

## 2. What was built

- `python/sync_dominance.py`: `GATE_POLICIES = ("recorded", "certain")`, `gate_policy_mode()`,
  `dump_gate_policy(trace, policy)` (explicit > `$CUVEIN_GATE_POLICY` > the dump's
  `hb_gate_policy` / its records' `gate_policy` > `recorded`, so a pre-T16 dump re-scores as it
  was recorded), `dump_policy_of(trace)`; `analyze()` returns `gate_policy`.
- `python/hb_oracle.py` (the specification): `analyze(..., gate_policy=None)`, `--gate-policy`.
  Under `certain` every RMW's acquire is deferred to its window close (as under the instance
  gate; under the trusting gate too), `rel_rmw[loc]` remembers who published a location's chain
  clock (thread, epoch, isolated), the per-location moral-strength summary lives in `_Clu`
  (`ms_note` / `ms_pairwise`), the window carries the edge state (`[edge, closed, members at
  issue, isolated, r isolated, refusals]`), `close_win` decides, joins, reports, attaches. The
  race records carry `gate_policy`; the report carries `gate_policy` and the kernel's `chain`
  counters (`edges`, `uncertain`, `unsafe`, `refused`, `open`), computed under both policies.
- `sanalyzer/src/tools/pc_dependency_analysis.cpp` (`HbClock`, 1:1 with the oracle):
  `YOSEMITE_HB_GATE_POLICY` read once (`hb_gate_policy_certain()`, a warning on any other
  value); `Released` gets `tid`, `ep`, `isolated`; `Win` the edge state; `Clu` the ms summary;
  `a2_open` / `a2_close` / `process` as the oracle. Emitted in vector-clock mode, with or without
  the dump (no-dump mode runs `HbClock` for both modes, so the policy is a runtime parameter
  there as step 0 asks): `hb_gate_policy`, `hb_chain`, and `gate_policy` on every `hb_races`
  record; `HB_STATS` gets `gate_policy` and `chain`. Zero cost when unset: the counters are
  integers on paths the recorded clock already walks; the deferral under the trusting gate
  exists only under `certain`.
- Verdict layer: `eval/baselines/run_cuvein.py` notes `gate_policy=certain` in a row's `notes`
  when the dumps' `hb_races` were computed under it (`classes_note`); `make_tables.py` loads such
  rows as tool `cuvein-certain` (`--certain-results <dir or glob>`, repeatable) and adds the
  columns `Race (sound) FP / TP` (Race alone under the certain clock), `R u L (sound) FP / TP`
  and `n (sound)` to the operating-points table; `latent`, `sc`, `a2` are unchanged.
- Re-score: `eval/baselines/t16_rescore.py` (`prepare` / `oracle --set main|exits --shard` /
  `tables`), `setup/p_t16_rescore.sh`, `setup/p_t16_analyze.sh`; GPU checks:
  `setup/t16_build.sh`, `setup/t16_check.sh`, `setup/t16_parity.py`, `setup/t16_time.sh`.
- Tests (`python/test_hb_substitutions.py`, T16 section): the hand-made hand-offs (overlapping:
  refused, reported, flagged; closed by an exit: taken; open-ended without exit records; the
  non-ms intermediate: `unsafe`), 200 random traces (the invariant at the aggregate key, equal
  sync pairs, equal unflagged counts, the flag sound under both policies against every
  window-consistent order), the 16-warp lock (`lock_contention_a2.cu`): the certain clock
  reports the critical sections the recorded clock orders through overlapping hand-offs, every
  added instance flagged; a second recording of the lock under `YOSEMITE_HB_GATE_POLICY=certain`
  with `HbClock` == oracle under it. The hand-made dump helper now writes exit records
  (`_EXIT`, `hb_exits: 1`).
- Docs: `eval/README.md` (the knob), `design/proof/hb_proof.tex` §7 (the paragraph; `pdflatex`
  twice, no undefined reference, no `Overfull`, the same seven pre-existing font-shape warnings
  as before), order-of-work item (8) updated.

## 3. Checks on the private runtime

Runtime of the branch: libsanalyzer `3514c25c74163534` (`setup/t16_build.sh`, job 311008, GCC
12.4.0; the collector `bcd69d3f0e9e1d88` relinked from the d67ed41 install's objects, unchanged
by T16). Checks `setup/t16_check.sh`, job 311009, node c74 (RTX 4060 Ti, sm_89, driver
580.82.07, CUDA 13.3), every trace re-recorded with the worktree runtime, no
`YOSEMITE_HB_GATE_POLICY` in the environment:

- **Green set** (CLAUDE.md A4 files + `test_instance_gate.py`) + `test_no_dump.py` under the
  default policy: **339 passed, 2 skipped**, 0 failed (6:01). Before T16: 332 + 2; the seven new
  tests are the T16 section of `test_hb_substitutions.py` (five on hand-made traces, two on the
  16-warp lock); the two skips are the gate suite's empty parameter sets, as before.
- **Parity under both policies** (`setup/t16_parity.py`; the 33 ScoR litmus, the project's
  litmus kernels `lock_contention_a2` 4×4 and 1×4 warps, `write_after_unlock_other_schedule`,
  `atomic_mm_handoff`, `gate_held`, `strong_store_strong_load`, `write_before_lock`, each
  recorded under `recorded` and under `certain`): per kernel dump `HbClock`'s `hb_races` ==
  the oracle's under the dump's policy at the parity key (pc pair, kind, class, space, dist,
  async, count, `a2_uncertain`), `hb_races_sync_only` equal, `hb_chain` == the oracle's
  `chain`, the dump's `hb_gate_policy` and every record's `gate_policy` right, and on every
  recorded dump the oracle under `certain` ⊇ the oracle under `recorded` (aggregate key with
  counts, equal sync pairs): **129 rows, 0 problems** (**tested**). An earlier run of the same
  checks on the binary before the `xwarp` counter (job 310898, c52) gave the same 339 + 2 and
  129 / 0.
- The lock litmus in that run (`kcontend`, 16 warps × 32 critical sections): recorded 393
  instances in 351 records, all flagged; certain 22,101 instances in 3,690 records, all flagged;
  21,215 of 21,229 hand-off edges refused (the re-run of the same kernel under `certain`
  recorded 20,970 edges, 20,938 refused). `kcontrol`'s genuine race: 1 instance, unflagged,
  under both. `race_interblock_none-lock_rtraw`: 0 → 2 instances (the rtraw race the recorded
  lock hand-off orders), `norace_interblock_lock_waw`: 0 → 1 SC instance, every addition
  flagged; `race_interblock_blklock_waw`: 2 of 2 edges `unsafe` (block-scope RMWs of different
  blocks), the race reported under both.
- Default-path byte identity was not re-checked here: T16 touches `HbClock` only, which runs
  under `YOSEMITE_HB_TRACE` (the default tool path never constructs it); the green set's
  `test_no_dump.py` and the gate suite cover the no-dump and gated paths.
- `make_tables.py` without `--certain-results` writes `eval/BASELINES.md` and
  `eval/BASELINES_SUMMARY.md` byte-identical to HEAD's `make_tables.py` on the committed
  `eval/results` (**tested**, login node).

## 4. Hand-made and randomized traces (no GPU, **tested**)

- Overlapping hand-off (`B: write x; CAS` / `A: CAS` while B's window is open / `B: exit` /
  `A: read x`): recorded `{}`, certain `{(write, read): RAW DR, 1 instance, flagged}`; chain
  `edges 1, uncertain 1, refused 1`.
- The same with B's exit before A's CAS: both `{}`; `uncertain 0`.
- Without exit records: B's last RMW keeps its window open to the end of the kernel — refused,
  `open 1`.
- A block-scope RMW of another block issued inside `q`'s window: `unsafe 1`, the edge refused,
  the pair (A's write, B's read) and the non-ms RMW pair reported, both flagged; at grid scope
  the intermediate is morally strong and the edge is taken.
- 200 random traces (2–4 threads, 1–2 blocks, grid/block/none-scope RMWs on two words, plain and
  strong accesses): `Rep_certain ⊇ Rep_recorded` at the aggregate key with counts, equal sync
  pairs, equal unflagged instances, and no instance ordered by some window-consistent order left
  unflagged under either policy; 65 of 300 traces of the development smoke added reports under
  `certain`.

## 5. Re-score of the kept stores (no GPU)

`eval/baselines/t16_rescore.py` (`prepare` on a `normal` node; `oracle` as `setup/p_t16_rescore.sh`,
24 + 8 shards, jobs 310967 / 310966; `parallel.py analyze` of both stores as `setup/p_t16_analyze.sh`,
jobs 311038 / 311039 and 311156 / 311157; `tables` on the login node →
`eval/results/t16-rescore/T16_RESCORE_TABLES.md`, the full per-program lists). Two sets of
dumped programs, the oracle run twice on every vector-clock kernel dump (`--gate-policy
recorded`, then `certain`; `strong-ldst token`, the dump's gate):

- **main** — T12's selection as re-oracled under the instance gate (store `t12-after`): 594
  programs (P1 384, P2 58, P3 58, P4 28, P5 33, P6 28, P7 1, P9 4), 464 with an RMW pc
  (re-scored; the other 130 cannot differ, the policy governs (ATOM) edges only), 4,571 kernels,
  233 GB of dumps, 0 oracle failures. These are the evcand / full-2026-09-22 recordings of
  2026-09-20/22, **without exit records** (T3b came later): a thread's last RMW keeps its
  window open to the kernel's end.
- **exits** — the dumps `HbClock` recorded after T3b, the only kept stores with exit records:
  `t19-parity` (59 programs, the d67ed41 runtime, 2026-10-05) and `t12-eval-t12rb` (ScoR
  P4/P5, 38 programs not in the former, the T12 runtime, 2026-09-30): 97 programs, 77 with an
  RMW pc, 539 kernels, 9.1 GB, 0 failures. Here the stored `hb_races` are `HbClock`'s own.

**Parity of the default policy (proved-in-effect).** `oracle(recorded)` equals the stored
`hb_races` at the parity key on **4,571 of 4,571** main kernels (T12's oracle) and **539 of 539**
exits kernels (`HbClock`, two runtimes): the recorded clock did not change value.

**The invariant (proved-in-effect).** `Rep_certain ⊇ Rep_recorded` (aggregate key with counts;
equal sync pairs) on **5,110 of 5,110** kernels. No violation.

**Chain edges refused, per suite.** Chain edges = morally strong successor pairs `r -> q` (what
the recorded clock takes); `uncertain` = `r`'s window open at `q`; `cross-warp` = the uncertain
edges between RMWs of different warps, the quantity `eval/A2_WINDOWS.md` reports as 12.6 M of
29.9 M successor edges (42 %) over the evcand dumps; `open-ended` = the releaser's window never
closed before the kernel's end; `unsafe` = disjoint windows but a non-ms possible intermediate.

| set | pset | kernels | chain edges | uncertain | % | cross-warp | % | open-ended | unsafe | refused % |
|---|---|---|---|---|---|---|---|---|---|---|
| main | P1 | 3,608 | 5,920,046 | 5,008,094 | 84.6 % | 2,865,232 | 48.4 % | 1,620,156 | 0 | 84.6 % |
| main | P2 | 41 | 569 | 215 | 37.8 % | 211 | 37.1 % | 144 | 0 | 37.8 % |
| main | P3 | 631 | 787,071 | 752,728 | 95.6 % | 106,749 | 13.6 % | 368,983 | 0 | 95.6 % |
| main | P4 | 258 | 23,125,522 | 18,181,495 | 78.6 % | 9,615,277 | 41.6 % | 35,026 | 4,476 | 78.6 % |
| main | P5 | 33 | 114 | 70 | 61.4 % | 70 | 61.4 % | 26 | 2 | 63.2 % |
| main | **all** | 4,571 | **29,833,322** | 23,942,602 | **80.3 %** | **12,587,539** | **42.2 %** | 2,024,335 | 4,478 | 80.3 % |
| exits | P1 | 64 | 13,809 | 9,341 | 67.6 % | 6,497 | 47.0 % | 0 | 0 | 67.6 % |
| exits | P3 | 104 | 170,832 | 165,497 | 96.9 % | 17,652 | 10.3 % | 0 | 0 | 96.9 % |
| exits | P4 | 333 | 40,847,840 | 33,366,389 | 81.7 % | 19,790,221 | 48.4 % | 0 | 8,959 | 81.7 % |
| exits | P5 | 33 | 114 | 64 | 56.1 % | 64 | 56.1 % | 0 | 2 | 57.9 % |
| exits | PI | 5 | 16 | 7 | 43.8 % | 7 | 43.8 % | 0 | 0 | 43.8 % |
| exits | **all** | 539 | **41,032,611** | 33,541,298 | **81.7 %** | 19,814,441 | **48.3 %** | **0** | 8,961 | 81.8 % |

Reading it: the main set's 29.83 M chain edges and 12.59 M cross-warp uncertain edges (42.2 %)
are `eval/A2_WINDOWS.md`'s 29.9 M and 12.6 M (42 %) — the same quantity, counted by the clock
itself. The certain clock refuses far more than the census's figure because the lanes of one
warp instruction overlap by construction (an RMW's window is open until the lane's *thread*
issues its next record, which is after the whole instruction): 80 % of all chain edges on the
dumped corpus, 85 % on P1, 96 % on P3 (graph kernels whose atomics are counters issued by
thousands of threads in a burst), 57–63 % on the litmus. On the exit-less dumps 8.5 % of the
uncertain edges (2.0 M) are open-ended — a thread's last RMW — which exit records remove
entirely (0 of 33.5 M in the exits set). `unsafe` edges exist only in programs mixing
block-scope and grid-scope RMWs on one word: the ScoR `graph-coloring-racy` /
`graph-connectivity-racy` (the injected scope bug) and `race_interblock_blklock_waw`.

**What the refusals add (race sets, both sets):** in every case an **SC** pair (two strong
accesses — the volatile data of the ScoR applications and litmus — left unordered) or the one
rtraw race, and **every added instance carries `a2_uncertain`** (the recorded order is one
coherence order the windows allow, so the possible clock orders it):

| set | new DR pc pairs | new SC pc pairs | added instances | flagged | programs |
|---|---|---|---|---|---|
| main | 1 | 449 | 4,377,810 | 100 % | P4 `reduction-{norace,racy}-{small,large}`, `rule-110-norace-{small,large}` (SC); P5 `norace_interblock_lock_waw`, `norace_interwarp_blklock_waw`, `norace_interwarp_dev-blklock_waw` (SC), `race_interblock_none-lock_rtraw` (1 DR + 1 SC) |
| exits | 1 | 459 | 4,389,009 | 100 % | P4 `matrix-multiplication-norace-small` (4.1 M SC instances: T9's A2 case, SC since T10), `reduction-*`, `rule-110-*` (SC); P5 `norace_interblock_lock_waw` (SC), `race_interblock_none-lock_rtraw` (1 DR + 1 SC) |

Not one program of P1, P2, P3, P6, P9 or PI gains a report: their RMWs (counters, flags
ordered by barriers) order nothing that is otherwise unordered, so refusing 85–96 % of their
chain edges changes nothing. The ScoR applications' hand-offs are what the certain clock
cannot certify: their critical sections become SC reports (informational under PTX counting,
D2; under ScoRD's notion they are reports on race-free programs — `reduction-norace`,
`rule-110-norace`, `matrix-multiplication-norace`: the completeness price on contended
hand-offs, exactly the flagged population).

**Verdicts (the "Race (sound)" column).** `parallel.py analyze` with this checkout on the recorded
store and on the certain store, both modes (scalar-clock mode is unaffected and is the control:
its rows are identical). FP / TP = labelled-CLEAN programs reported / labelled-RACE programs
reported, over the programs with a labelled, non-ERROR row under both policies (`P9-fpc-cuda`
and `P9-mr-cuda` are not in the table: their analysis exceeds the 4 h cap under both policies, as
in T9-0 and T12; 40 rows per policy are ERROR/TIMEOUT for the same programs — no trace
collected, or the cap).

Main set (the evcand / full-2026-09-22 dumps, no exit records):

| pset | mode | R u L FP / TP (recorded) | R u L FP / TP (certain) | Race alone FP / TP (recorded) | **Race (sound)** FP / TP | labelled CLEAN / RACE |
| P1 | cuVein-SC | 0 / 196 | 0 / 196 | 0 / 196 | **0 / 196** | 188 / 196 |
| P1 | cuVein-VC | 0 / 174 | 0 / 174 | 0 / 174 | **0 / 174** | 187 / 174 |
| P2 | cuVein-SC | 0 / 25 | 0 / 25 | 0 / 25 | **0 / 25** | 28 / 30 |
| P2 | cuVein-VC | 0 / 25 | 0 / 25 | 0 / 25 | **0 / 25** | 28 / 30 |
| P3 | cuVein-SC | 16 / 0 | 16 / 0 | 16 / 0 | **16 / 0** | 58 / 0 |
| P3 | cuVein-VC | 14 / 0 | 14 / 0 | 14 / 0 | **14 / 0** | 56 / 0 |
| P4 | cuVein-SC | 2 / 14 | 2 / 14 | 2 / 14 | **2 / 14** | 14 / 14 |
| P4 | cuVein-VC | 2 / 9 | 2 / 9 | 2 / 9 | **2 / 9** | 9 / 9 |
| P5 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 14 / 19 |
| P5 | cuVein-VC | 1 / 3 | 1 / 4 | 1 / 3 | **1 / 4** | 14 / 19 |
| P6 | cuVein-SC | 0 / 5 | 0 / 5 | 0 / 5 | **0 / 5** | 17 / 11 |
| P6 | cuVein-VC | 0 / 5 | 0 / 5 | 0 / 5 | **0 / 5** | 17 / 10 |
| P9 | cuVein-SC | 1 / 0 | 1 / 0 | 1 / 0 | **1 / 0** | 2 / 0 |
| P9 | cuVein-VC | 1 / 0 | 1 / 0 | 1 / 0 | **1 / 0** | 1 / 0 |

Exit-record set (`t19-parity` + `t12-eval-t12rb`):

| pset | mode | R u L FP / TP (recorded) | R u L FP / TP (certain) | Race alone FP / TP (recorded) | **Race (sound)** FP / TP | labelled CLEAN / RACE |
| P1 | cuVein-SC | 0 / 7 | 0 / 7 | 0 / 7 | **0 / 7** | 2 / 7 |
| P1 | cuVein-VC | 0 / 7 | 0 / 7 | 0 / 7 | **0 / 7** | 2 / 7 |
| P3 | cuVein-SC | 2 / 0 | 2 / 0 | 2 / 0 | **2 / 0** | 10 / 0 |
| P3 | cuVein-VC | 2 / 0 | 2 / 0 | 2 / 0 | **2 / 0** | 10 / 0 |
| P4 | cuVein-SC | 2 / 12 | 2 / 12 | 2 / 12 | **2 / 12** | 13 / 12 |
| P4 | cuVein-VC | 2 / 12 | 2 / 12 | 2 / 12 | **2 / 12** | 13 / 12 |
| P5 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 14 / 19 |
| P5 | cuVein-VC | 1 / 3 | 1 / 4 | 1 / 3 | **1 / 4** | 14 / 19 |
| P6 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 6 / 3 |
| P6 | cuVein-VC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 6 / 3 |
| PI | cuVein-SC | 0 / 4 | 0 / 4 | 0 / 4 | **0 / 4** | 3 / 5 |
| PI | cuVein-VC | 0 / 4 | 0 / 4 | 0 / 4 | **0 / 4** | 3 / 5 |

**One program moves, in both sets and in vector-clock mode only:** `race_interblock_none-lock_rtraw`
(ScoR, labelled RACE) goes from CLEAN (its one report `latent-sc`: the rtraw pair ordered in that
recording by the lock hand-off, SC under T10's token rule) to RACE at both operating points — the
certain clock refuses the overlapping hand-off and reports the rtraw pair as a `structural` DR
plus an SC pair, both flagged. That is the race T9-0 found latent-only and D8 made a case study:
under the certain clock it is a race of this run. Nothing else moves: the 449 / 459 added SC pairs
sit on programs already counted as `sc` or already RACE, and no DR verdict is lost (the invariant).
So on the dumped corpus **Race (sound) = Race alone + 1 TP**, FP for FP; the exposure of the sound
operating point is confined to the `sc` column (and to ScoR under ScoRD's DR ∪ SC notion, where
`reduction-norace`, `rule-110-norace` and `matrix-multiplication-norace` gain reports — the
contended hand-offs the certain clock cannot certify).

## 6. The cost of a second run (step 5)

`setup/t16_time.sh`, job 311010, node c73 (RTX 4060 Ti 16 GB, EPYC 7302P host, 125 GB), the
worktree runtime, no-dump mode (`YOSEMITE_HB_DUMP=0`, `HB_STATS` at kernel end), the four P7/P9
programs that finish in both modes under no-dump (`eval/NO_DUMP.md`), vector-clock mode under
`recorded` and `certain` twice each, interleaved on the one node, scalar-clock mode once. Wall =
`/usr/bin/time`; RSS = max over the run.

| program | kernels | chain edges (uncertain / cross-warp) | VC recorded (2 reps) | VC certain (2 reps) | SC recorded | verdicts rec / cert / SC |
|---|---|---|---|---|---|---|
| P9-crs-cuda | 50 | 0 | 163.4 s, 163.1 s (1.24 GB) | 163.2 s, 162.1 s (1.25 GB) | 138.7 s | CLEAN / CLEAN / CLEAN |
| P9-overlap-cuda | 20 | 0 | 150.6 s, 151.7 s (3.02 GB) | 149.9 s, 151.5 s (3.02 GB) | 101.4 s | CLEAN / CLEAN / CLEAN |
| P9-gpp-cuda | 10 | 24,575,940 (99.99 % / 3.1 %) | 177.2 s, 178.9 s (2.00 GB) | 179.7 s, 179.6 s (2.00 GB) | 107.9 s | CLEAN / CLEAN / CLEAN |
| P7-backprop-cuda | 2 | 0 | 14.5 s, 14.5 s (1.53 GB) | 14.5 s, 14.4 s (1.53 GB) | 10.9 s | CLEAN / CLEAN / CLEAN |

The certain run costs what the recorded run costs: the largest difference is gpp's +1.4 %
(179.7 against 177.2–178.9 s), within the rep-to-rep spread of the recorded runs; RSS is equal
to within 0.5 %. gpp is the one program here with chain edges — 24.6 M, of which the certain
clock refuses 24.57 M (99.99 %: its RMWs are atomic counters issued by many threads in a
burst, every window open at the next issue; only 3.1 % of the uncertain edges are cross-warp)
— and still reports nothing under it: nothing those edges order is otherwise unordered. So on
the realistic suites the sound column is a second run per program at the same price as the
first, and the no-dump programs' `hb_chain` says how much the certain clock refused.
(**tested**; two reps, one node, one day.)

## 7. The tables (step 6)

`make_tables.py --certain-results <dir>` (repeatable; the shard CSVs of a certain-policy
`parallel.py analyze`) loads the rows whose `notes` carry `gate_policy=certain` as tool
`cuvein-certain` and appends three columns to the operating-points table: `Race (sound) FP / TP`
(Race alone under the certain clock), `R u L (sound) FP / TP` and `n (sound)`, the programs of
the row with a certain-policy run; the other columns, `latent` and `sc` included, stay the
recorded clock's. Without the option the output is byte-identical to HEAD's (**tested**). Rendered
on the committed `eval/results` with the two re-score stores' certain CSVs (vector-clock rows;
the scalar-clock rows have no certain run and print a dash — the policy does not touch that
mode). The recorded columns come from the committed baseline sweeps, the sound columns from the
re-scored programs, so the denominators differ (`n (sound)`); the like-for-like comparison is §5's
table, where both policies run on the same dumps:

| pset | Race u Latent FP / TP (recorded sweeps) | Race alone FP / TP | Race (sound) FP / TP | R u L (sound) FP / TP | n (sound) |
|---|---|---|---|---|---|
| P1 | 0/199 / 182/182 | 0/199 / 0/0 (n/a 182) | 0 / 106 | 0 / 106 | 161 |
| PI | 0/1260 / 1714/1862 | 0/1260 / 0/148 | 0 / 1 | 0 / 1 | 1 |
| P3 | 14/58 / 0/0 | 0/44 / 0/0 | 14 / 0 | 14 / 0 | 36 |
| P4 | 5/9 / 9/9 | 0/4 / 0/0 | 2 / 9 | 2 / 9 | 14 |
| P5 | 0/14 / 19/19 | 0/14 / 0/0 | 1 / 4 | 1 / 4 | 27 |
| P6, P7, P9 | — | — | — | — | 0 |

(`eval/BASELINES.md` itself is not regenerated by this branch: the column belongs to the mode
comparison, whose certain-policy runs are a second run per program of the final sweep.)

## 8. What remains unverified

- **A2w itself.** The soundness claim rests on A2w (an RMW has taken effect by its thread's next
  record), which T13 never saw violated under NVBit's timing (30 runs) and which the Sanitizer
  callback does not guarantee (it does not wait for the atomic's result, `RED` in particular;
  CLAUDE.md B2 "Open on A2w"). It is an assumption of the trusted base, not a measured fact.
- **Soundness relative to the model.** `Rep_certain ⊇ Rep(co)` is Lemma "Monotonicity" applied to
  the model's happens-before over the execution's coherence order; what the model leaves out
  (I6, I7, `bar.arrive`, the access-size check, local memory) is left out here too.
- **The refinement's cost** is measured (`unsafe` edges: 0.015 % of the main set's, in three
  mixed-scope programs) but its *necessity* was argued, not observed: no kept dump shows an
  execution whose chain is broken by a non-ms intermediate (the values are not recorded).
- **Pre-T3b dumps**: the main set's open-ended refusals (2.0 M) over-refuse relative to a run with
  exit records; the exits set shows they vanish, but the exits set is 97 programs.
- **The second run**: four programs, two reps, one node, one day; the ±1 % is within the
  rep-to-rep spread, not a measured per-record cost.
- **The default tool path** (no `YOSEMITE_HB_TRACE`) was not re-diffed; `HbClock` is never
  constructed there (unchanged code path), and the collector is untouched.
- **The old check job** on the binary before the `xwarp` counter and this one agree; the installed
  runtime (a37ad29a) was not touched — the branch's runtime is private until the merge is
  installed.

## 9. Commands

```
# worktree, private runtime (both components' hashes in the job logs under build_logs/)
git worktree add ../wt-t16 -b feat/certain-clock cuVein
W=/home/fzheng4/wt-t16 sbatch -p normal,rtx4060ti16g,rtx4060ti8g -x c54,c2,c37,c21,c22,c34,c20 \
    --cpus-per-task=4 eval/baselines/setup/t16_build.sh                       # job 311008
W=/home/fzheng4/wt-t16 sbatch -p rtx4060ti16g,rtx4060ti8g -x c54,c2,c37,c21,c22,c34,c20 \
    eval/baselines/setup/t16_check.sh                                         # job 311009: green set + parity
W=/home/fzheng4/wt-t16 sbatch -p rtx4060ti16g,rtx4060ti8g -x c54,c2,c37,c21,c22,c34,c20 \
    eval/baselines/setup/t16_time.sh                                          # job 311010: step 5
# re-score (CPU)
.env/bin/python eval/baselines/t16_rescore.py prepare                        # a normal node (BeeGFS)
W=$W SET=main  sbatch --array=0-23 eval/baselines/setup/p_t16_rescore.sh      # 310967
W=$W SET=exits sbatch --array=0-7  eval/baselines/setup/p_t16_rescore.sh      # 310966
W=$W SET=main  WHICH=recorded sbatch --array=0-31 eval/baselines/setup/p_t16_analyze.sh   # 311038
W=$W SET=main  WHICH=certain  sbatch --array=0-31 eval/baselines/setup/p_t16_analyze.sh   # 311039
W=$W SET=exits WHICH=recorded sbatch --array=0-3  eval/baselines/setup/p_t16_analyze.sh   # 311156
W=$W SET=exits WHICH=certain  sbatch --array=0-3  eval/baselines/setup/p_t16_analyze.sh   # 311157
.env/bin/python eval/baselines/t16_rescore.py tables                         # login node
# the tables with the sound column (does not touch eval/results/baselines-*.csv)
.env/bin/python eval/baselines/make_tables.py --certain-results eval/results/t16-rescore/main-certain
# proof
cd design/proof && pdflatex hb_proof.tex && pdflatex hb_proof.tex
# the knob
YOSEMITE_HB_TRACE=1 YOSEMITE_HB_GATE_POLICY=certain accelprof -t pc_dependency_analysis -n 1 ./app
.env/bin/python python/hb_oracle.py kernel.dot kernel_0.json --gate-policy certain
```
Node c37 of `rtx4060ti16g` has no CUDA 13.3 (`/usr/local/cuda` → 13.2; no `compute-sanitizer/`
for 13.3): with `CUDA_HOME=/usr/local/cuda-13.3` every HB run there fails to load
`libsanitizer-public.so` and the green set reports "no trace produced" (the first check job,
310872, is that failure, not a code one); every GPU job above excludes it.

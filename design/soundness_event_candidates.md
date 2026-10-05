# Soundness of vector-clock mode, and the event-stream candidates (T9, Parts 1–2)

Revision: branch `fix/publish-then-tick` (T9), based on `cuVein` 1a3aea5 (= the detector of
3331d35 plus PR #4). Proof: `design/proof/hb_proof.tex` (the one document; T9 edits listed in
its *Status and scope* paragraph). Measurements: `eval/T9_RESCORE.md`. Vocabulary as in the
proof: **sound** = misses no race (no false negative), **complete** = every report is a race
(no false positive). Labels: **proved-in-effect** (an invariant checked over N real traces),
**tested** (a specific verdict asserted), **read** (from the code), **argued** (on paper only).

The question of todo 9: the event-stream candidates (`sync_dominance.py`, knob
`CUVEIN_EVENT_CANDIDATES`) and the CAS past-release gate (`_past_release`, knob
`CUVEIN_R3_PAST_RELEASE`) let scalar-clock mode catch `race_interblock_none-lock_rtraw`,
whose racing pair has no dependency edge. Does vector-clock mode still miss no race — in
particular, does it catch every race scalar-clock mode now catches?

Answer, in one paragraph (numbers: Part 3). At 3331d35, no: the engine's algorithm was not the proof's
`Detect`. Two substitutions broke Theorem "Sound" — I1 (tick before publish) and I2 (one
last write per location, SC dropped) — and I1 is exactly what hid the rtraw race when the
releaser runs first. The event-stream candidates were never the issue for the engine: its
guarantee is about records on a location, not about dependency edges. T9 replaces I1, I2 and
I5 by the proof's algorithm (publish-then-tick, per-(thread, key) buckets in both clocks,
local memory outside the model); the engine is then `Detect(T, vec)` with the trusting gate
(I4 remains, T12) and the cp.async agents (I7, now inside the model: Proposition "Agents").
Vector-clock mode's Race ∪ Latent is a superset of scalar-clock mode's Race on the same
trace, up to the vetoes (Part 2).

## Part 1 — the engine itself (Theorem "Sound", location level)

### 1.1 I1: tick before publish — the missed class, and the corpus instance

The proof's Algorithm 1 publishes the RMW's clock and *then* ticks the releaser's own
component; the code at 3331d35 ticked first (`hb_oracle.py:332-333`,
`pc_dependency_analysis.cpp:471-473` at 3331d35) and recorded the RMW at the post-tick epoch.
The published clock then covers the releaser's accesses after its release. Threads `t`
(block 0) and `u` (block 1), grid-scope atomics on `f`, plain `x`; `t`'s epoch is `c` before
its release:

| seq | record | 3331d35 | Algorithm 1 (T9) |
|---|---|---|---|
| 1 | `t`: RMW on `f` (unlock) | tick to `c+1`, publish `{t:c+1}` | publish `{t:c}`, RMW recorded at `c`, tick to `c+1` |
| 2 | `t`: write `x` | bucket `(t, W, weak)` = `c+1` | bucket `(t, W, weak)` = `c+1` |
| 3 | `u`: RMW on `f` (lock) | `clk[u][t] = c+1` | `clk[u][t] = c` |
| 4 | `u`: read `x` | `c+1 > c+1` false → **no report** | `c+1 > c` → RAW reported |

Nothing orders seq 2 before seq 4: a race. The omitted pairs are exactly
`R_miss` (proof, Proposition "Missed class of I1"): a non-RMW record `a` of `t` whose
PO-last preceding tick is an RMW `r` with `r →hb⁼ b`, no later tick of `t` in `Pred(b)`,
`seq(a) < seq(b)` — the records of a releaser between an RMW and its next tick, met after an
acquirer that joined that RMW. In the other trace order (the acquirer's access first) the
reader bucket catches it as a WAR, which is why the gap needs the releaser to run first.

**Corpus instance** (T9-0, `eval/LATENT_CENSUS.md` §3): the evcand vector-clock dump of the
ScoR kernel `race_interblock_fence_rtraw` — block 0 releases with `atomicExch(&flag, 1)` at
seq 5, block 1's spin succeeds at seq 6, block 0 reads `data` at seq 7 after its own release,
block 1 writes it at seq 8; `hb_races` was empty and the verdict survived only as `latent`.
Re-scored with the T9 oracle (no GPU, `eval/baselines/t9_rescore.py`): the pair 0x100/0x1f0
is a DR in `hb_races` and the verdict class is `structural` (*proved-in-effect* on this dump;
`eval/T9_RESCORE.md`). The same pair is reported on the 2026-09-28 re-recording of the ScoR
litmus with the T9 runtime (`algorithms_check.py`: 1 race, marked `(i1)` = the pair the I1
switch would lose), and so is one pair of `race_interblock_lock-no-tf_waw` on that trace.

**Regression tests** (*tested*, green set since T9): `python/test_hb_substitutions.py::`
`test_write_after_unlock_other_schedule` (the rtraw lock with block 0 forced first by a
memory-free `clock64()` spin; the write-after-unlock/read pair is a DR in `hb_races` with
class `structural` in vector-clock mode) and `::test_write_after_unlock_scalar_clock` (RACE in
scalar-clock mode); `python/test_sync_dominance.py::test_hb_engine_matches_oracle` on the 32
ScoR binaries, including `race_interblock_fence_rtraw`.

### 1.2 I2: one last write per location, SC dropped — the counterexample and the lost class

The code at 3331d35 kept, per location, the last write and each thread's last read since
it (FastTrack's state), shared by both clocks, and skipped every morally strong pair
(`coherent()` under `--strong-ldst generic`). Remark "Why one bucket per key": `A` (block 1)
and `B` (block 0, thread 0) store `x` with relaxed `cuda::atomic` stores (strong, sys scope),
unordered, `A` first; a `__syncthreads()` joins `B` with `C` (block 0, warp 1); `C` loads `x`
weakly. `(A, C)` is a data race. The check at `C` saw only `B`'s store (the barrier orders it)
and `A`'s store was gone; `(A, B)` is an SC pair and was dropped — nothing reported, in either
clock. On the real kernel (`python/testdata/strong_stores_barrier_weak_load.cu`, traced by T6
on an RTX 4060 Ti) the strict xfail `test_strong_stores_barrier_weak_load` confirmed it;
with T9 it passes: `(A, C)` is a DR and `(A, B)` an SC in `hb_races`, `(A, C)` is in
`hb_races_sync_only` and `(B, C)` is not (the barrier), and the pair is a RACE in both modes
(`test_strong_stores_barrier_weak_load{,_scalar_clock}`; *tested*).

**The lost class under I2** (*argued*, from the code at 3331d35): (i) every SC pair; (ii) every
DR pair `(e, a)` on a location whose earlier record `e` had been displaced from the state
before `a` was checked — a write `e` by an intervening write `w'` of another thread, a read
`e` by any intervening write — and where the displacing write did not itself carry the pair:
the check at `a` saw `w'` instead, which is either ordered before `a` (then nothing is
reported although `e` is unordered with `a`: the Remark's case) or unordered (then `(w', a)`
is reported instead of `(e, a)`, a different record pair and often a different pc pair). What
FastTrack keeps is the first reportable access of each location, not Theorem "Sound"'s
per-(thread, key) coverage; policy `none` (no strong loads/stores) does not repair (ii)
(T6 headline 4). The same state fed the barrier-only clock, so (ii) also removed pairs from
`hb_races_sync_only` / `barrier_only_pairs` — `algorithms_check.py` found 8 such pc pairs on
3 of the 33 litmus traces at 3331d35 — and §5 fact (ii) ("absent from Rep_sync ⇒
barrier-ordered") did not hold for the code.

**The fix** (D6: buckets): per location, per thread, per key `(kind ∈ {R, W, RMW}, strong
scope or weak)`, the latest record's (vector-clock epoch, sync epoch, pc); `Check` walks every
other thread's buckets on the location, reports DR unless morally strong, SC unless both are
RMWs; never a FastTrack collapse across threads. One bucket serves both clocks (both runs of
`Detect` replace it at the same records), so the second clock is `Detect(T, sync)` too.
Proof: Theorem "Sound" uses exactly that a bucket's representative is PO-after the record it
replaced with the same key (and block), hence the same conflict, `ms` and class.

### 1.3 I5: local memory

T6 measured 8,096 spurious race records on a 2×32-thread kernel with thread-private arrays
(the collector's thread-id fold of a local address is a 32-bit shift). D14 (with Yanbo Zhao):
local memory is outside the HB model (proof, Definition "Records": a location is shared or
global; local memory is thread-private by construction). T9: `hb_collect_events` no longer
serializes `MemoryType::Local` records (the collector's default path and its local-address tag
are untouched); the engine, the oracle and `barrier_only_pairs` skip any `local` record of an
older dump before the monitor and before `Check`, so a kept dump replays as a new one would
(*tested*: `test_local_memory_is_thread_private`, `test_local_records_of_an_older_dump_are_ignored`).

### 1.4 No edge, no problem: the engine needs no candidate mechanism

Theorem "Sound" is a statement about records on a location: for every reportable `(e, a)`
with `seq(e) < seq(a)`, `Check(a)` adds `(e', a)` of the same class with `e' = e` or
`e →po e'` of the same key. Nothing in it mentions the dependency graph. The engine checks
every memory record against every other thread's buckets on its location, so **any
conflicting, HB-unordered pair on a location yields a report on that location**, whether or
not the collector's dependency side recorded an edge between the two pcs (it records only
the last accessor per location, so a pair such as rtraw's read-by-A / read-by-B / write-by-B
has none). The event-stream candidates exist for the *verdict layer*, which judges pc pairs
and used to take them from the edges only: in vector-clock mode every pc pair of `hb_races`
(and of `hb_races_sync_only`) is a candidate, so every `Rep_vec` pair is judged (§5 fact (iii));
in scalar-clock mode the offline pass `barrier_only_pairs` is the candidate source. The
engine itself needs none.

### 1.5 The asynchronous copies (I7) inside the model

T9 moved I7 from "outside the model" into §1–§4 of the proof: Definition "Asynchronous
copies" (a copy is a pair of records of the issuing thread's agent `α(t)`; commits are the
agent's ticks; a wait completes the oldest groups), generators (ISSUE), (GROUP), (WAIT) of
Definition "Happens-before" (all in `HB^sync`), the agent operations of §3 (join at issue,
snapshot-then-tick at commit, join the snapshot at wait — the publish-then-tick shape of an
RMW), and Proposition "Agents": the lemmas and both theorems hold with agents, with "PO" for
an agent read as its group order (*argued*; the operations are what `hb_oracle.py`, the engine
and `barrier_only_pairs` do since T1a, and the parity tests hold on `python/testdata/cp_async_wait.cu`).
Not covered: copies completed through an mbarrier (`ARRIVES.LDGSTSBAR`, T1b) and bulk copies.

## Part 2 — the composed vector-clock verdict vs the scalar-clock verdict

**Claim.** On one trace, scalar-clock mode's RACE set equals vector-clock mode's
Race ∪ Latent minus the vetoes; with the T9 classes, scalar-clock's RACE ∪ `sc` equals
vector-clock's `structural` ∪ `model_bug` ∪ `latent` ∪ `sc` ∪ `latent-sc` minus the vetoes.

**Argument** (*argued*; proof §5 fact (i)). Both modes judge the same candidate pairs with the
same static rules (R1, R3; since D12 R2 only classifies): the edges, plus the event-stream
pairs — `hb_races_sync_only` ∪ `hb_races` in vector-clock mode, the offline pass in
scalar-clock mode. The engine's second clock and `barrier_only_pairs` are the same
`Detect(T, sync)` (proved-in-effect: `test_hb_engine_matches_oracle` and
`test_offline_barrier_pass_matches_oracle` assert equality, counts included, on the green set,
and since T9 they no longer share I2's state). `HB^sync ⊆ HB` gives `Rep_vec ⊆ Rep_sync`
(Lemma "Monotonicity"). For a pair that R1 or R3 does not order: scalar-clock says RACE (or
`sc`) iff it is in `Rep_sync`; vector-clock says `structural`/`sc` if in `Rep_vec`, else
`latent`/`latent-sc` if in `Rep_sync` — the same set. For a pair that R1 or R3 orders:
scalar-clock says ORDERED; vector-clock says ORDERED unless the pair is in `Rep_vec`, where it
vetoes the certificate (`model_bug` if R1, `structural`/`sc` if R3) — the vetoes. The full
clock never adds ORDERED and never removes a report. The DR/SC split can differ in one
direction only: vector-clock takes the class from the pair's `hb_races` instances (DR if any
is), scalar-clock from R2 at the widest observed distance of the pair, which may exceed every
raced instance's distance (an ordered instance at a wider distance) and then demotes SC to DR.

**Measured** (T9-0, `eval/LATENT_CENSUS.md` §6, not re-measured): on the same trace 557 of 558
programs agree; the exception is crs-cuda, where the offline pass is skipped above
`CUVEIN_BARRIER_PASS_MAX_LANES` (26 kernels above 5·10⁶ lane-accesses) and 6 vector-clock
pairs are never judged by scalar-clock mode. An absent `hb_races_sync_only` key and
candidate-generation differences did not occur. The three ways scalar-clock mode can miss
what vector-clock mode reports are the proof's §5 (a)–(c): (a) R3 grants ORDERED at pc level
to a pair some instance of which is unordered (the P5 canary; vector-clock vetoes it);
(b) candidate generation — a pair with no edge and no event-stream candidate; (c) the
`MAX_LANES` cutoff (crs-cuda). Everything else is reported identically.

## Part 3 — the change and what it moved (details: `eval/T9_RESCORE.md`)

Implemented in `hb_oracle.py`, `HbEngine` and `barrier_only_pairs` (commits b87adbb,
2494aa3): I1, I2 (buckets, SC reported with class `"SC"`), I5 (local records out of the HB
trace, skipped on replay), D12 in the verdict layer (`sc` / `latent-sc`, verdict `SC`), D2 in
the harness (`classes=` note, `make_tables.py` operating-points section). Because the
no-collapse race set is O(threads²) record pairs (1.7·10⁹ on the kept P1 dumps), `hb_races`
is aggregated per pc pair, kind, class, space, thread distance and async side with a count.

Measured on the 554 re-scored kept programs: no pc pair lost; 26 DR pairs gained on 15
programs; 200 SC pairs; no program verdict moved at the Race ∪ Latent point; at the
Race-alone point `race_interblock_fence_rtraw` (TP, I1) and `matrix-multiplication-norace-small`
(new FP) moved. The FP is not a detector defect but **assumption A2 failing on the trace**: a
successful lock CAS is recorded before the release it read from, so the (ATOM) edge comes
from the wrong RMW; tick-before-publish (I1) had hidden it. It is reported, not suppressed.

## What remains unverified

* Proposition "Agents" and the lost-class characterization of I2 are hand arguments (the
  former is exercised by the cp.async parity tests, not proved mechanically).
* The superset claim of Part 2 is argued for the T9 matrix and measured (T9-0) on the 3331d35
  matrix; it was not re-measured with the SC classes.
* A2 (seq order of a location's RMWs = coherence order) is violated on at least one kept
  trace; how often is not counted (the collector records no values), and its cause (the
  memory callback running before the atomic) is inferred, not measured.
* I4 (the trusting gate) is still in the code: the certificate is relative to the implemented
  HB, and 8 of the 10 latent-only ScoR races stay latent until T12.

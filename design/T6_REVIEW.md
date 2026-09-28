# T6: review of `design/proof/hb_proof.tex` against the code (2026-09-26)

Reviewer: Claude Opus 5.5, fresh context (had not worked on the code before this task), plus a
second fresh Opus context for the acceptance check of §3/§7 (below). Code: `cuVein` 3331d35 —
identical at 3ed5c9c (the T9-0 merge adds only `eval/`), so every `file:line` below holds on
both. Document: the 2026-09-26 revision (`docs/proof-inputs` e1303f4); the corrected version is
on branch `design/algorithms`. GPU runs: node c23, RTX 4060 Ti (sm_89), driver 580.82.07,
CUDA 13.3; installed runtime = the 3331d35 build (collector `7bafac9fbac26efd`, libsanalyzer
`95659970773ed751`, i.e. the T1a-review stage — the install is done).

Legend: **proved-in-effect** = an invariant checked over N real traces; **tested** = a specific
verdict asserted; **read** = established by reading the code; **unverified** = neither.

## Headline

1. The code is Algorithm 1 with I1–I7 **plus** three things §7 did not list: a non-blocking
   `bar.arrive` is modelled as a blocking arrival (the collector drops the Sanitizer barrier
   callback's `flags`); there is no access-size/overlap check (a location is the access's
   start address); scalar-clock mode runs no trace-validity check. All three are now in §7
   (I3, I6). None is exercised by the kept corpus (no `BAR.ARV` in 293 kept sm_89 CFGs).
2. **I5 is worse than §7 said:** the collector means to fold the thread id into a local
   address (`(get_flat_thread_id()) << 54`, `gpu_patch_pc_dependency.cu:89`) but
   `get_flat_thread_id()` returns `uint32_t` (`gpu_utils.h:58`): a 32-bit shift by 54, which
   yields 0. Every thread's local access at one offset is one location. On
   `python/testdata/local_mem_blocks.cu` (2×32 threads, thread-private arrays) the engine
   records **8,096 spurious race records (287 pc pairs, 5,824 cross-block)**; no verdict
   changes, because the dependency side records no local pc (`pc_dependency_analysis.cpp:1716`),
   so the 268 local candidates have no event evidence (`sync_dominance.py:990`). The fix is to
   key local memory per thread in the engine/oracle (T9); fixing the shift alone would still
   collide across blocks. *Tested* (strict xfail `test_local_memory_is_thread_private`).
3. **I2 also breaks the second clock.** The barrier-only clock shares the last-write state, so
   `hb_races_sync_only` / `barrier_only_pairs` are not `Detect(T, sync)`: 8 barrier-unordered pc
   pairs are absent on 3 of the 33 litmus traces (`algorithms_check.py`, "SYNC-MISS"). §5 fact
   (ii) (absence from Rep_sync = barrier-ordered) holds only for `Detect`; on the litmus corpus
   none of the 8 pairs is judged (no edge, no candidate), so no verdict moves there. *Proved-in-
   effect* on 33 traces for the count; the verdict-level consequence is *read*.
4. **§7's I2 row overclaimed policy `none`:** FastTrack's argument gives a report at the first
   reportable access of each location, not Theorem "Sound". E2 of `check_e1_e2.py` under
   `none` reports (w0, w1) and misses the DR (w0, r); `algorithms_check.py` reports both.
5. **§3's deferred acquire was not exact as written:** Algorithm 1 runs `Check(r)` after the
   acquire join, so deferring the join to t's next record changes r's own check (a spinner's
   plain read of the lock word against the next owner's CAS becomes a spurious DR). Exact
   once `Check(r)` is evaluated against `clk[t] ⊔ Ch_ℓ` with the difference held until
   `acq(r)` is known — now in §3; T12's design note must carry it.
6. **§5 matrix precedence:** with the SC row first, a pc pair with both SC and DR instances
   (a cta-scope atomic meeting a strong store in and across blocks) would be `sc`. Now: one DR
   instance makes the pair a Race.
7. Referee reading (§4, §6): §4 follows except that Lemma "Clock invariant" (c) was stated
   only for "⇝-maximal" RMWs while the RMW case uses it for every chain member (fixed), and
   "schedule-independent" in Corollary "The sync instance" needs the threads to reach the same
   instances in the other execution (note added). §6 has two real gaps, written in as referee
   notes: under the instance gate two consecutive morally strong RMWs can be HB-unordered, so
   the Values step needs MM2 with coherence order; MM3 is false for counted barriers used by
   part of a block (and instance labels need the barrier index).

## (a) §3, §5, §7 against the code

Confirmed (*read*):

| statement | evidence |
|---|---|
| I1: order acquire → check → tick → publish; the RMW's entry has the post-tick epoch | `hb_oracle.py:315-335` (tick 332, publish 333, entry 334); `pc_dependency_analysis.cpp:447-475` (tick 471-472, publish 473, entry 474) |
| I2: one last write per location + per-thread last read since that write; `coherent()` skips morally strong pairs | `hb_oracle.py:110-111,166-171,326-358`; `pc_dependency_analysis.cpp:76,80,264-268,459-505` |
| `released[loc]` = Ch_ℓ | overwritten, not joined (`hb_oracle.py:333`, `.cpp:473`); equal to Algorithm 1's join under the trusting gate — now said in §3 |
| trusting gate (I4): every RMW acquires and releases; chain break = scope test | `hb_oracle.py:315-321`, `.cpp:447-453` |
| I3: `expected = thread_count or block_tc`, no exits | `hb_oracle.py:250,260`; `.cpp:344` (BlockExit skipped), `:375,389`; `hb_collect_events` drops BlockExit (`.cpp:961-962`) |
| I5: local keyed `(local, addr)` | `hb_oracle.py:211-213`; `.cpp:437-438` (loc_block 0 for local) |
| I6: completion-order check per (block, warp); degrade when count unknown | `hb_oracle.py:250-285`; `.cpp:375-429` |
| I7: agent `t | 2^62`, commit/wait joins | `hb_oracle.py:183-209`; `.cpp:127-186`; `sync_dominance.py:533-547` |
| `barrier_only_pairs` = Detect(T, sync), shared base + scalar own | `sync_dominance.py:490-639` (sync_group 549-564: one fresh joined dict per group, copy-on-write in `join_to`) — with I2/I3/I5/I7 as for the engine |
| §5 matrix = `_hb_class`; the full clock never grants ORDERED | `sync_dominance.py:671-696` (rows 2-5), `:897` (latent → verdict RACE today) |
| R3's release point today = region dominance | `release_scope` (`sync_dominance.py:377-383`: a MEMBAR in postdom(u) ∩ dom(a)), `chain` (412-449) |
| no write-before-lock check | `_past_release` docstring, `sync_dominance.py:405` ("the mirror … is not gated") |
| fifth check absent | `kernel_trace_flush` (`.cpp:1156-1341`) never inspects `pending_barriers`; `tv_violation` is written only by `HbEngine::emit` (`.cpp:648-652`) |

Contradicted, fixed in the document:

| where | was | fix |
|---|---|---|
| §1 | the four TV checks "decide W0, … and W2" | W2 only for memory records, per warp; arrival/syncwarp/cp.async records of a waiting warp unchecked; W0 only in the oracle; scalar-clock mode runs none (`barrier_only_pairs` has no TV code) |
| §1 | exit/memory records one per thread | dump records carry a warp + lane mask, expanded in lane order (the collector's exit record too, `gpu_patch_pc_dependency.cu:215-249`) |
| §2 | "the monitor rejects" mixed sizes / proxies | no such check; a location is the start address (`hb_oracle.py:299`, `.cpp:436-438`); listed under I6 |
| §3 | deferred acquire "exact", "nothing reads clk[t] in between" | `Check(r)` reads it; evaluate against `clk[t] ⊔ Ch_ℓ`, hold the difference until `acq(r)` |
| §5 | R3 "each hop … at scope ≥ d, release-fenced at the start" | hops are validated at their own distance (`sync_dominance.py:741`), the first hop within the release fence's scope (443), no fence when u is atomic (426-427), program-order steps between atomics (445-448); d enters only through `_cs_fenced` (474) |
| §5 | matrix row order SC before DR | DR wins per pc pair |
| §5 | (not stated) | `judge` relabels after the matrix: `benign` (913; verdict stays RACE) and opt-in `warp-po-ordered` (931); no Rep_sync at all → latent (696); D2's counts must use the pre-relabel class |
| §5 (ii), (iii) | unqualified | (ii) holds for Detect, not under I2 (8 pairs / 3 traces); (iii) only pcs the dependency side records (no local pcs) |
| §7 I2 | policy `none` ⇒ Theorem "Sound" | only FastTrack's first-race-per-location guarantee |
| §7 I3 | — | `bar.arrive` recorded as blocking: `BarrierCallback` drops `flags` (`gpu_patch_pc_dependency.cu:183-189`; `SANITIZER_BARRIER_FLAG_IS_SYNCHRONIZING = 0x2` in CUDA 13.3 `sanitizer_patching.h:266`) |
| §7 I5 | "spurious WAW if the collector records the per-thread window offset; to check" | it does (the fold is a 32-bit shift): measured, see headline 2 |
| §7 I6 | — | no size/overlap check; none of the TV checks in scalar-clock mode |
| §7 | — | labeling note: an atomic with no SASS scope gets the empty scope (`sync_dominance.py:112`); `.STRONG` LD/ST strong only in generic form (policy `generic`) |

Fresh-context acceptance check (a second Opus context that read only §3/§7 and the code;
first pass 1,437 s, 50 tool calls). It found 11 statements the code contradicts or deviations
§7 did not list, plus one design note; all are now in the document:

| # | finding | resolution |
|---|---|---|
| 1 | an `ATOMS` without a scope gets `cta`, not the empty scope (`sync_dominance.py:108-111`, sidecar :57-60) | labeling paragraph |
| 2 | I3 dumps are flagged in vector-clock mode, indirectly: `TV-barrier-completion-order` fires when a released warp runs on (oracle 273-285, engine 404-429); nothing in the verdict layer reads `tv_violation` (only `scale_harness.py:113`) | note (b) |
| 3 | the offline pass has a size cutoff and an off switch (`CUVEIN_BARRIER_PASS_MAX_LANES`, `CUVEIN_BARRIER_PASS=0`; `sync_dominance.py:510-512,797,805`): scalar-clock mode then runs no Detect | §3 correspondence |
| 4 | engine vs oracle: labels from the sidecar (merged over a binary's CFGs, merged-table fallback; `.cpp:329-338`) vs the one CFG; record-and-continue vs raise on a TV violation; `is_write` from the WRITE flag vs the event type (latent: the dump's "atomic" test is flag 0x4 = `FLAG_ATOMSYS` in CUDA 13.3) | §7 intro |
| 5 | the per-warp degrade exists in scalar-clock mode, unmonitored (`sync_dominance.py:604-607`) | I6 row |
| 6 | there is no "re-arriving warp" row; the per-warp check is `TV-barrier-completion-order` on memory records | I6 row |
| 7 | `bar.arrive`: the arriving thread's accesses before the completion keep its pre-arrival epoch, which the instance hands to all participants — a second over-ordering (missed races) | note (b) |
| 8 | I7 applies only to dumps with `hb_async`, not to `ARRIVES.LDGSTSBAR` kernels; each issue joins the thread's clock into the agent | I7 row, note (d) |
| 9 | "no local pc" holds for purely local pcs only; a generic pc that also reaches global/shared memory is a node, and its spurious local records reach the verdict layer | note (c), §5 (iii) |
| 10 | "the other schedule is reported by both" is ambiguous (block 1 first: neither reports; read-before-write under the same lock order: both, as a WAR) | Tested paragraph |
| 11 | "7/7" counts two ordering tests; five of the seven monitor tests, oracle only | Monitor sentence |
| 12 | design note, not a contradiction: the §3 deferral is consistent with Algorithm 1, whose publish is a join; wiring it (T12) also needs `released[loc] = vc[t]` turned into a join (`hb_oracle.py:333`, `.cpp:473`), no publish when `rel(r)=0`, and held pairs resolved at kernel end (`acq(r)=1` for a thread's last record) | end-of-kernel case in §3; the rest is for T12's design note |

Second pass (same context, revised text, 164 s): **no contradictions remain**. Two optional
notes it did not ask to put in the text: with the offline pass skipped by the cutoff,
vector-clock mode also leaves unjudged the candidates only `hb_races_sync_only` shows
(`no_event_evidence`, `sync_dominance.py:982-993`; §5 already says "six vector-clock pairs are
never judged" for crs-cuda); and the latent read/write difference of item 4.

The verifier also noted, for the fix of I5, that a 64-bit shift of the in-block thread id would
still merge threads of different blocks (the engine/oracle must key local memory per thread).

Observations kept out of the document (no statement there contradicts them):
- The coherence profile Π is keyed by raw address (`hb_oracle.py:305`, `.cpp:443`), not by
  location: shared-memory atomics at one offset in different blocks share one sequence. It is
  observational; equal code profiles imply equal per-location Π, so grouping by it is finer.
- Atomics appear in `hb_events` as `"type": "write"` (the Sanitizer flags carry no ATOMIC bit
  for `ATOMG`); every consumer classifies atomics by pc, so nothing depends on it.

## (b) Referee reading of §4 and §6 (time-boxed)

§4, case by case: Lemma "seq-forwardness", "Assembly", "Chain clock", the five cases of
"Clock invariant" (exit; read/write; non-completing arrival; completing arrival or exit —
including an exit completing several keys, whose participant sets are disjoint by W2; RMW),
"HB test", "Complete", "Sound", the `sync` corollary and the buckets remark all follow, with
two findings written into the document: (c)'s "⇝-maximal" qualifier (the RMW case applies (c)
to non-maximal chain members; restated for every published RMW) and the scope of
"schedule-independent" in Corollary "The sync instance".

§6: Lemma "First reportable prefix" is immediate. Lemma "Matching": *Participants* relies on
MM3, false for counted barriers used by part of a block, and on instance labels (block,
count) that must include the barrier index; *Values* needs every two RMWs of a location to be
HB-comparable, true under the trusting gate on a race-free trace but not under the instance
gate (two ms RMWs with gate 0 are unordered and not reportable) — MM2 must then be read with
the RMWs' coherence order (fixed by Π). Theorem "Per-profile certificate": the closing
bijection needs the lemma applied in both directions. Proposition "Fidelity" follows under
A1–A3. All four are referee notes at the end of §6; none is resolved.

## (c) The simulator and the real-kernel checks

`design/algorithms_check.py`: Algorithm 1 (`Detect(T, vec|sync)`, buckets, chain clock,
publish-then-tick, trusting gate) with I1 and I2 as switches. Its core, `detect()`, is 78
lines rather than the brief's ~40: the I2 switch reproduces the code's state and race labels
so that the comparison with `hb_oracle.py` can be exact equality. With both on it must equal
`hb_oracle.analyze` (`races` and `races_sync_only`); with both off it is the reference.

| corpus | traces | switches on == oracle (vec and sync) | reference-only pairs |
|---|---|---|---|
| ScoR litmus (green-set artifacts, 2026-09-23 and regenerated 2026-09-26) | 32 | 32/32 | `race_interblock_fence_rtraw` 0x100/0x1f0 (I1); `race_interblock_blklock_waw` 0x150/0x260 (I2); sync clock: 8 pairs on `norace_interwarp-block_fence-atom_hrd-indirect` (2), `norace_interwarp-block_fence_hrf-indirect` (5), `race_interblock_blklock_waw` (1) |
| P5 canary (`canary_pc_level_false_negative.cu`, traced 2026-09-26) | 1 | 1/1 | none |
| T6 kernels (I1, I2) | 2 | 2/2 | the I1 pair; the I2 DR and SC pairs |
| `check_e1_e2.py` hand-made dumps | 4 | 4/4 | E1 block 0 first (I1); E2 (w0, r) DR and (w0, w1) SC under `generic`, (w0, r) under `none` |

No trace has a code report the reference lacks (the code is complete relative to Detect on
all of them). *Proved-in-effect* on 33 litmus traces (+2 kernels, +4 synthetic dumps).

`python/test_hb_substitutions.py` (not in the green set), job 291536: **5 passed, 3 xfailed**.
Controls (pass): the reference reports the I1 RAW and the I2 DR + SC; engine == oracle on both
kernels; the local kernel's verdict is clean. Strict xfails:
`test_write_after_unlock_other_schedule` (I1: the pair is in `hb_races` and the verdict class
is `structural`; today `latent`), `test_strong_stores_barrier_weak_load` (I2: (A, C) in
`hb_races`; today nothing at x, verdict CLEAN), `test_local_memory_is_thread_private` (I5).
Schedules are forced by a memory-free `clock64()` busy wait; each fixture skips if the order
was not reached (it was, on c23).

Green set (CLAUDE.md A4), same job, from this worktree: **136 passed, 1 xfailed**
(`test_relaxed_handoff_should_race`) — unchanged.

## (d) A3, the fifth check and T3b

§1's A3 ("the hardware waits for the non-exited threads … and for n threads when a count is
given; under exit records a statement about the hardware") and the fifth check (every open
segment complete at the end of the kernel) are what route (a) needs. Four things in CLAUDE.md's
T3b brief do not match:
1. Its context paragraph and step 5 describe the 09-24 draft ("Definition 'Expected count'
   does not subtract exits", A3 "on the collector"); the 09-26 Definition "Instances" already
   subtracts exits and Lemma "Assembly" already has `exited_β` — step 5 is done on the proof
   side.
2. "subtract exited threads from the expected count of every later instance" — the Definition
   subtracts only for count-0 (whole-block) instances; a counted instance keeps `exp = n`.
3. Step 4's re-score of crs-cuda from the T0 store cannot reach CLEAN: no stored dump has exit
   records (`hb_collect_events` drops BlockExit, `.cpp:961-962`). Only a fresh recording can.
4. Placement of `TV-barrier-pending-at-end`: in vector-clock mode it must run in the engine
   before `HbEngine::emit` (which is where `tv_violation` is written; `kernel_trace_flush` calls
   it through `hb_engine_emit`, `.cpp:1334`); in scalar-clock mode the engine never runs
   (`.cpp:1036,1875`), so the check exists only offline, in `barrier_only_pairs`, which has no
   TV code yet (T11 unifies).
The collector's exit record is per warp with the exiting lanes (`BlockExitCallback`,
`gpu_patch_pc_dependency.cu:215-249`), the same shape as an arrival — route (a) needs no new
device code, only serialization.

## (e) The 2026-09-26 edits

- **Instance gate as a predicate on records.** Every use of `rel`/`acq` in §4 (equation (1),
  Lemma "Chain clock", the RMW case of "Clock invariant", Definition "Happens-before") is at
  the RMW in question and reads correctly with a record predicate. The online deferral in §3
  was not exact (headline 5); fixed. Open for T12's design note: whether a path that *starts*
  or *ends* at a fence or `BAR.SYNC` (p or q is itself a barrier arrival) "crosses" it.
- **SC row vs `_hb_class`:** dormant (I2 drops SC); precedence fixed (headline 6). Note for T9:
  in scalar-clock mode R2 certifies morally strong pairs, so SC pairs land in `ordered` there;
  the `sc` column exists only in vector-clock mode unless R2's output is relabelled.
- **R3 amendment vs `HBGraph.chain`:** the release point today is region dominance
  (`release_scope`); no write-before-lock check exists. The amendment's "PO-next RMW of u's
  thread" is per dynamic instance; the pc-level certificate needs it for every observed
  instance of u (added).
- **Fifth check vs `kernel_trace_flush`:** see (d) 4. Also: the engine updates `warp_waiting`
  only when strict (`.cpp:399-407`), but `pending_barriers` always, so the fifth check does
  not depend on `YOSEMITE_HB_STRICT`.

## Evidence on the two settled choices (not reopened)

**O2 (fence inventory, T12).** Over 293 distinct sm_89 CFGs (the ScoR artifacts and every
home `traces_keep*/*/dots/`): 461 `BAR` instructions, all `BAR.SYNC(.DEFER_BLOCKING)`, **none
with a `MEMBAR` immediately before or after it** — ptxas relies on the barrier alone, as the
settled `fenced()` choice assumes. No `BAR.ARV`/`BAR.RED`. Fence-like opcodes: 493
`CCTL.IVALL`, 314 `ERRBAR`, 244 `MEMBAR.SC.SYS`, 132 `MEMBAR.SC.CTA`, 70 `MEMBAR.SC.GPU`,
103 `WARPSYNC`, 1 `DEPBAR.LE`. A seq_cst fence is `MEMBAR.SC.{GPU,SYS}; ERRBAR; CCTL.IVALL`.
**Acquire loads and acquire RMWs lower to the access followed by `CCTL.IVALL` with no MEMBAR**
(e.g. `LD.E.STRONG.SYS; …; CCTL.IVALL` and `ATOM.E.MIN.S32.STRONG.SYS; CCTL.IVALL` in the
Indigo3 `CudaAtomic` kernels): a `fenced()` that counts only `MEMBAR` sets `acq = 0` on PTX
acquires — the case T12 step 1 asks to check before trusting `acq = 0`.

**T12 before T5b.** `eval/baselines/setup/engine_timeout_ids.txt` (58 programs, all with kept
dots), by what their SASS contains: 30 atomics + barriers, 8 atomics only, **10 barriers and
no atomics** (P7 heartwall, hotspot, lavaMD, particlefilter, pathfinder, srad, stencil1d,
P9 dxtc2, …), 10 neither (P6 asyncmemcpy ×3 and interkernel ×2, P7 bezier-surface, bitonic,
haversine, …). T5a measured the
barrier-only regime (tiled_gemm: all of `vc`'s 2.73 GB from `sync_group` copies). The gate
governs (ATOM) only, so for the 10 barrier-only programs — mostly P7, the suite with no
vector-clock dump — T12 removes nothing and T5b is the only fix; ordering T5b after T12 only
delays them. For the 38 with atomics the gate may shrink the clocks first. This is static
opcode presence, not measured join counts.

## Commands

```
# simulator (login node)
.env/bin/python design/algorithms_check.py                       # 32 ScoR artifacts
.env/bin/python design/algorithms_check.py ScoR/microbenchmarks/artifacts/* \
    t6_runs/canary_pc_level_false_negative t6_runs/write_after_unlock_other_schedule \
    t6_runs/strong_stores_barrier_weak_load                     # 35 traces
.env/bin/python design/proof/check_e1_e2.py
# GPU (rtx4060ti16g, c23)
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t6_probe.sh   # job 291532: build + trace the 3 kernels and the canary
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t6_check.sh   # job 291536: green set, test_hb_substitutions.py, simulator
# SASS scans (BAR/MEMBAR adjacency, fence opcodes, timeout-set classification); run from the
# main checkout, which holds the gitignored traces_keep* stores the worktree lacks
cd /home/fzheng4/AccelProf && .env/bin/python <worktree>/eval/baselines/setup/t6_sass_scan.py
# document
pdflatex hb_proof.tex; pdflatex hb_proof.tex                        # TeX Live 2026 in ~/texlive
```
The reviewed document builds to 13 pages (11 before T6), no Overfull boxes, no undefined
references; the §7 table is now a float (as a non-breaking block it left most of a page
empty).

## What remains unverified

- The §3 deferral with `Check(r)` evaluated twice is argued, not implemented or tested (the
  instance gate does not exist yet).
- The §6 referee notes are findings, not repairs: MM2 with coherence order and a participant
  argument for counted barriers are not written.
- Whether any corpus kernel has a pc pair with both SC and DR instances (the precedence case)
  — SC is not reported today, so it cannot be measured before T9.
- The 8,096 local records are one run of one kernel; the count depends on warp interleaving.
  How many corpus kernels touch local memory, and how large their spurious `hb_races` are, is
  not measured (the verdict layer is unaffected by construction).
- Whether a judged pair of any corpus program is absent from the code's Rep_sync while
  barrier-unordered (I2 in the second clock) — measured only on the litmus traces (none).
- `bar.arrive` behaviour: read from the header and the collector; no kernel with `BAR.ARV`
  was traced.
- The O2 and timeout-set statements are static SASS scans of the kept (home) CFGs, not of the
  BeeGFS stores and not runtime measurements.

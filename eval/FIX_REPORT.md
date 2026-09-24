# cuVein false-positive / false-negative root causes and fixes

_Companion to `eval/REPORT.md` (the evaluation). This document is about the detector:
what caused each false-positive / false-negative class the evaluation surfaced, the
evidence, whether it is fixable, what was changed, and what remains. Detector diffs live in
`python/sync_dominance.py`, `python/hb_oracle.py`,
`sanalyzer/src/tools/pc_dependency_analysis.cpp` (+ `.h` comment) on branch
`worktree-eval-suite` (commits `9a30954`, `0edd92b`)._

## Summary

| id | class | root cause (verified in code + traces) | fixable? | status |
|---|---|---|---|---|
| F2 | 82 `model_bug` verdicts | **report-attribution bug**: WAR race records carried only the writer pc and the verdict matrix matched pc pairs with a *subset* test, so every pair sharing that pc counted as raced; plus bare shared `ATOMS` scoped NONE | yes | **fixed**; tripwire 0 on every suite |
| F6 (new) | residual `model_bug` on 2-block TC | atomic **release map keyed by raw address**; shared-memory offsets repeat per block, so one block's release clobbered another's → spurious same-block atomic race | yes | **fixed** (engine + oracle) |
| R1 loop hole (new, latent) | none observed | `dominance()` ignored sync-free wrap-around paths on the cyclic region graph | yes | **fixed** |
| F1 | 12 structural FPs on the lock-based reduction | **not** fence-blindness: 10 intra-warp lock-step pairs the engine has no event for; 2 a trace **record-order inversion** | partly | opt-in `--assume-warp-lockstep` removes the 10; the 2 are documented |
| F4 | confirmed FN (`cp.async` read-before-wait) | the async shared write **is** recorded but attributed to the issuing lane's own tid; the wait is not instrumented | yes | **fixed** in T1a (`eval/CP_ASYNC_REPORT.md`): async agent per thread + commit groups (`PIPELINE_COMMIT` / `PIPELINE_WAIT`); racy → 1 RAW, fixed → 0 in both modes, E6a 9/9, no other P5/P6 verdict change; review follow-up: a barrier between copy and read, two copies of one thread, mbarrier-completed copies |
| F5 | structural FPs on graph-analytics benign races | plain reads of atomically-updated locations; idempotent plain WAW; trace `ATOMIC` flag is `ATOMSYS` (unusable) | partly | Tier-1 `benign` re-bucket applied; plain-vs-plain residue needs Tier 2/3 |
| — | 1 Indigo3 TC RaceBug miss | 1-block input cannot exhibit the cross-block planted race | yes | caught on the 2-block 1024-node graph |

Invariants preserved through every change: `pytest python/test_sync_dominance.py
python/test_barrier_soundness.py` → **68/68** (33 litmus race_≥1 / norace_=0, 33 engine ==
exact-oracle key-by-key, intersubwarp regression, barrier soundness); the canary still
reports exactly one structural race (`0x1f0→0x160`).

---

## F2 — `model_bug` tripwire: report-attribution bug (fixed)

**Symptom.** 82 verdicts in the `model_bug` cell (R1/R2 claim all-schedule ordering, the
engine says the pair raced): graph-connectivity racy `0x400→0x430` (1) and Indigo3 TC
BlockAdd variants (81). The first-draft hypothesis (divergent/conditional barrier) is refuted.

**Root cause.** `sync_dominance.py` built `raced_pcsets` from the engine's `hb_races` and
tested a pair with `any(s <= pair …)` — a subset test. A record degenerates to a single-pc key
when (a) it is a WAR: engine (`pc_dependency_analysis.cpp`, `add_race(…, -1, …)` → `null`)
and oracle (`hb_oracle.py`, `"a_pc": None`) stored only the writer pc because `last_reads`
kept clocks without pcs; or (b) `a_pc == b_pc`. `{0x400} ⊆ {0x400,0x430}` then marked the
ordered pair as raced. Evidence: graph-connectivity `linkKernel` emits **5520 WAR records,
all `a_pc: null`**; the real partner of `0x400` is `0x160` (the planted race, same barrier
interval); barrier instance #2 completes 400/400 before the `0x430` reads; participation is
perfect (780 barrier events, 0 pending; warp 12 `active_mask=0xffff`); no `__syncthreads` is
in a thread-dependent branch. On TC, `atomicAdd_block` on shared memory compiles to bare
`ATOMS.ADD` (no `.STRONG`), which `atomic_scope()` mapped to NONE → sidecar scope 0 → the
engine never joined on it → 6 self-races per launch with `a_pc==b_pc==0x680` → singleton keys
→ the two barrier-ordered pairs (`0x70→0x680`, `0x680→0x6e0`) became `model_bug` (and TC
nobug's lone FP was that self-race).

**Fix.** (1) `HbEngine.last_reads` / oracle `last_reads` store `(clock, pc)`; WAR records
name both pcs; `hb_pair_raced` is an exact `frozenset((a,b)) in raced_pairs` (same-pc races
still match). Must ship together — exact match alone demotes the true positive `0x160→0x400`
to latent because engine WAR records would match nothing. (2) `atomic_scope`: bare `ATOMS` →
BLOCK (shared memory is per-CTA, hence CTA-coherent by construction; bare `ATOM`/`ATOMG`
stay NONE = sound over-report). The sidecar reuses `atomic_scope`, so the engine picks it up
with no other change.

**Also found and fixed — R1 loop back-edge hole.** `HBGraph.dominance()` applied dom/postdom
on the cyclic region graph without checking for a sync-free path between the two regions
(`loop_scope` did so only for same-PC pairs). In `linkKernel`, `read@0x430` (iteration k) and
`write@0x400` (iteration k+1) are joined by a sync-free wrap-around path yet were declared
block-ordered; it had not fired only because the trace held ~1 iteration per block. Now a
pair is ordered only if every path between the regions crosses a qualifying sync of scope ≥
the claimed strength. Litmus unchanged (every `norace_*` still 0).

**Also found — harness collision.** Detail files were keyed by (program, variant, input) and
three TC flavors shared a variant slug; `eval/mk_e1_manifest.py` now keeps the flavor
(`BlockAdd/GlobalAdd/Reduction`) and `Determ/NonDeterm` in the slug.

**Result.** `tv_violations` = 0 on E0, E1 (both sets, both graphs), E2, E3, E5; every TC
nobug variant clean (12 TN); graph-connectivity racy: `0x160→0x400` structural (TP),
`0x400→0x430` latent.

## F6 — Release map keyed by raw address (found by the re-run; fixed)

**Symptom.** After F2's fixes, TC BlockAdd still produced `model_bug` — only on the 2-block
1024-node graph, never on the 1-block 100-node one: `0x680→0x680` (`ATOMS.ADD` vs itself,
same block), correctly BLOCK-ordered by R2, yet reported raced by the engine.

**Root cause.** Engine and oracle stored releases as `released[addr]`. Shared addresses are
per-block *offsets*; with two resident blocks, block B's `ATOMS` on offset X overwrote block
A's record, A's next `ATOMS` on X found B's record, failed the same-block check, never
acquired A's own earlier release, and reported a spurious atomic race. Confirmed by running
the oracle keyed by location on the recorded trace: it no longer reproduces the engine's
races (`oracle_verified = MISMATCH` against the old engine). Global memory unaffected (its
location key carries no block).

**Fix.** `released` keyed by the location tuple `(space, block, addr)` in `HbEngine`
(`std::map<Loc, Released>`) and `hb_oracle.analyze` (`released[loc]`); parity re-verified
68/68. **Lesson:** the litmus corpus has no multi-block shared-memory atomics, so it could
not have caught this; the 2-block Indigo input did.

## F1 — Reduction false positives: intra-warp lock-step + record-order inversion

**Symptom.** ScoR lock-based reduction, race-free build: 25 deduped reports, 12 structural,
13 latent, all volatile global `LDG/STG.E.STRONG.SYS`; the racy build reports the same count.

**Root cause — not fences.** The engine publishes the releaser's *entire* vector clock at
every atomic (`hb_oracle.py:157`, `cpp:178`), so `__threadfence_block` adds nothing to HB
(roadmap.md:77 "the fence is redundant for HB"); the static R3 chain certifies 6/6
lock-handshake store→load pairs (4 land ORDERED, 2 are overridden by the dynamic race). The
12 structural reports are:
- **10 intra-warp** (`tid<32` tail, `red_kernel.cu:89-117`): lanes *i* / *i−off* of one warp
  writing `sdata[i]` and reading `sdata[i−off+off]`, with no lock or fence in the source.
  Ordering is lock-step execution + `BSSY/BSYNC` reconvergence — excluded from sync
  classification and emitting no `Syncwarp` — so the engine has zero evidence (roadmap 5.3).
- **2 record-order inversions** (stage-1 handshake, both inlined copies): the Sanitizer
  callback is a *pre-op* patch and `GetBufferIndex` reserves the slot with an `atomicAdd`
  before the instruction executes, so in a tight spin-then-exit the spinner's last
  `ATOMG.ADD` record lands before the releaser's `ATOMG.EXCH` (seq 475 vs 478) → the engine
  sees acquire-before-release. Stages 2–4 survive only because extra spin iterations land a
  record after the release. The count is schedule-dependent (11+1 on a fresh trace).
The 13 latent reports are phase-1→phase-2 pairs ordered by the retirement ticket
(`MEMBAR.SC.GPU + ATOMG.INC.STRONG.GPU`), which no static rule reaches — benign.

**Fixability.** MEMBAR instrumentation is impossible on the Sanitizer backend (no memory-fence
entry among the 40 `Sanitizer_InstructionId`s; `WARPGROUP_FENCE` is the Hopper wgmma register
fence) and would not remove any of the 12; NVBit could match `MEMBAR` but `pc_dependency` is
wired only to the Sanitizer path. Downgrading `dyn_raced ∧ chain_ordered` to latent is
unsound — the canary's only report sits in exactly that cell. A static "fence-certified
release" bit is a no-op (release already covers all prior stores); the sound direction (gating
release coverage on a dominating fence) would make the fence-*removed* RACEY build report
*more* — the engine currently cannot distinguish the two builds at all.

**Fix applied (the 10).** Opt-in `--assume-warp-lockstep` in `sync_dominance.analyze`: a
structural warp-distance pair whose racing instances are all in one warp, whose ancient
access's region reaches the current's with no path back (no loop) — or, same region, precedes
it in offset order — is reclassified `warp-po-ordered` / ORDERED with `assumption:
warp-lockstep`. Divergent siblings (neither region reaches the other) stay races, which keeps
the ITS-sensitive cuHadron intersubwarp true positives. Off by default: not a proof under
independent thread scheduling. Effect: reduction race-free structural 12 → 1 (11 → 1 on the
fresh trace), racy still TP.

**Documented (the 2).** `pc_dependency_analysis.h` (`hb_collect_events`): record order is
instrumentation order; a `%globaltimer` stamp would narrow but not close the window; a
"spun-then-released" pattern match is the kind of case-specific heuristic the project rejects.

## F4 — `cp.async` read-before-wait false negative (fixed in T1a)

**Symptom.** `cuHadron/memcpy/shared_readwrite_race` racy: cuVein clean, Compute-Sanitizer
racecheck reports a shared-memory hazard.

**Root cause.** `LDGSTS @0x70` (cp.async global→shared), `LDS @0x90` read, `DEPBAR.LE @0xa0`
(`cp.async.wait_all`) *after* the read; the fixed build moves the wait ahead. The shared write
**is** recorded — `compute_sanitizer.cpp:285` registers `SANITIZER_INSTRUCTION_MEMCPY_ASYNC`
and `gpu_patch_pc_dependency.cu:142-150` emits a global READ and a shared WRITE at the same
pc, addresses matching the reads — but both legs treat it as a synchronous store by the
issuing lane: the engine's conflict test is `writer.tid != t` (same tid → no RAW) and the
static leg drops the `0x90←0x70` edge as `intra_thread_only`. `LDGDEPBAR`/`DEPBAR` are not
instrumented, so racy and fixed traces are event-for-event identical. Blast radius: exactly
this case (`memcpy/shared_writewrite` 32 WAW and `memcpy/global_readwrite` 32 RAW are caught
because their pairs are cross-thread; ScoR has no cp.async; HeCBench's cp.async users are
false-*positive* risk). `bulkcpy`/TMA is a separate unregistered family (sm90).

**Fix (designed).** Register `SANITIZER_INSTRUCTION_PIPELINE_WAIT` (=16; fires on
`cp.async.wait_group/wait_all`) in `nv-compute/src/compute_sanitizer.cpp` with a
`PipelineWaitCallback` via `EmitSyncEvent`; add `MemoryType::PipelineWait` and an
`ASYNC_COPY` flag on the LDGSTS shared write (`gpu_patch.h`, `gpu_patch_pc_dependency.cu`);
in engine + oracle attribute that write to a virtual async agent `t | ASYNC_BIT` and
`join_into(vc[t], vc[async(t)])` on the wait event; static leg: `DEPBAR` becomes a
non-qualifying sync node with an `async_wait()` ordering source. Expected: racy → 1 RAW, fixed
→ 0, E6a agreement 9/9. Tripwire: if `PIPELINE_WAIT` does not fire for `DEPBAR.LE` on sm_86,
the fixed build reports a race. Requires a clean rebuild of `nv-compute` (fatbin) and
`sanalyzer` (build notes in `memory/build-toolchain-gotchas.md`; use the conda compiler the
existing build used, `CXX=/home/fzheng4/miniconda3/bin/x86_64-conda-linux-gnu-c++`).

**Applied (T1a, 2026-09-23; `eval/CP_ASYNC_REPORT.md`).** Merged on `cuVein`, with four
changes to the design above:
1. **Commit groups.** `cp.async.wait_group N` completes only the groups older than the N
   newest, so `PIPELINE_COMMIT` (15) is registered too, and a wait joins the snapshot of the
   group it completes.
2. **Where asyncness comes from.** It comes from the `LDGSTS` opcode (sidecar `# async`
   lines for the engine, the CFG for the oracle and the offline pass), not from an
   `ASYNC_COPY` flag bit, which would have changed the default path's `current_flags`.
3. **Static leg unchanged.** The event stream rescues the intra-thread edge instead.
4. **Old dumps.** The engine marks its dumps `"hb_async": 1`, and unmarked pre-T1a dumps keep
   the old reading.

Measured on sm_89 (c20): `memcpy/shared_readwrite_race` racy RACE `shared:0x70-0x90:RAW` and
fixed CLEAN, in both modes. The other 116 P5/P6 rows are unchanged. E6a agreement is 9/9. The
green set plus `python/test_cp_async.py` gives 157 passed and 1 xfail. The default tool path
is byte-identical. The tripwire holds: `PIPELINE_WAIT` fires for `DEPBAR.LE`. The sm_86 half
of the tripwire was not run.

**Review follow-up (`fix/cp-async-review`, `eval/CP_ASYNC_REPORT.md` §6).** A fresh-context
review found three model gaps, each reproduced before it was fixed:
1. **A barrier between a copy and the read.** The static rules credited the barrier, which
   gave a scalar-clock FN and a vector-clock `model_bug`. They now give no credit to a pair
   whose earlier access is a copy.
2. **Two copies of one thread to one location.** These were unordered but never raced. They
   are now checked against the thread's view of its agent (engine, oracle and offline pass).
3. **Copies completed through an mbarrier.** These never completed under the model. Such a
   kernel now keeps the pre-T1a reading until T1b.

The corpus verdicts are unchanged (118 + 354 re-scored rows). Green set + `test_cp_async.py`
(67 cases): 203 passed, 1 xfail.

## F5 — Benign / inherent races of graph analytics (Tier 1 applied)

**Symptom.** Indigo3 nobug kernels and all four ECL `racefree` codes report structural races.

**Root cause.** Real HB-unordered accesses the algorithms tolerate: plain `LD.E.STRONG.SYS`
reads of a location updated by `ATOMG.E.CAS.STRONG.GPU` (union-find parent pointers), and
same-pc idempotent plain WAW. `HBGraph.coherence` needs *both* endpoints atomic and the engine
enters its atomic branch only for `pc in atom_scope`, so a plain read of an atomic's location
acquires nothing — by design. Two constraints: the trace records **no values**
(`MemoryGlobalAccessCallback` receives `pData` = the written value and discards it), and the
trace's `ATOMIC` flag is `SANITIZER_MEMORY_DEVICE_FLAG_ATOMSYS` (system scope only) — zero
ECL nodes carry it — so atomicity must come from the CFG/sidecar. Both deterministic and
nondeterministic Indigo nobug variants over-report: "nobug" means *no planted bug*, not
race-free.

**Fix applied (Tier 1).** `sync_dominance.analyze` builds, from the trace edges, the set of
write/atomic pcs each read pc conflicts with; a RAW/WAR whose read pc's writers are all in
`atom` is tagged `benign: atomic-maintained-read` and bucketed in a new `hb_class` cell
(verdict stays RACE; nothing hidden; `structural` is what a precision table counts).
Effect: ECL-MIS 20 → 0 structural (19 benign), ECL-MST 25 → 14 (15 benign), TC SyncBug
variants surface latent with benign-tagged reads; ECL-CC stays 24 because its array is *also*
plainly written (path compression), so the PC-granular test correctly declines; BFS/CC/SSSP
nobug (plain-vs-plain) untouched.

**Follow-ups designed.** Tier 2: per-location "never plainly written" bit in `HbEngine`'s
shadow (+ oracle mirror). Tier 3: same-value WAW — capture the written value from `pData`
into a `values[32]` field of `MemoryAccess` (layout change, ~+40% trace), carry it through
`hb_collect_events` `lanes[]`, compare in the WAW branch.

## TC RaceBug miss — input too small (resolved)

`RaceBug` replaces `atomicAdd(g_count, val)` with `(*g_count) += val` by one thread per block;
the 100-node torus gives `grid_dim [1,1,1]`, so the only edge is intra-thread. On the
1024-node grid (2 blocks) all TC RaceBug flavors are caught. The pre-fix 100-node TC "TPs"
were artifacts of the `ATOMS` self-race and are now honest 1-block FNs.

---

## Post-fix deltas (pre → post; `eval/results/*-fixed.csv`, `E1-final.csv`, `E1-determ-final.csv`)

| suite / item | before | after |
|---|---|---|
| `tv_violations` (all suites) | 82 | **0** |
| E1 Indigo3 NonDeterm (60 rows, both graphs) | recall 13/14, precision 0.52, TC BlockAdd nobug = FP | recall **26/28**, precision 0.57, **all 12 TC nobug rows TN**, TC slice P=1.00 |
| E1 Indigo3 Determ (40 rows) | recall 0.90, precision 0.60 | recall 18/20, precision 0.69, TC slice P=1.00 |
| E0 reduction race-free, structural | 12 | 11 (fresh trace) → **1** with `--assume-warp-lockstep` (10 `warp-po-ordered`) |
| E0 graph-connectivity racy | tv 1; `0x400→0x430` model_bug | tv 0; planted `0x160→0x400` structural TP; `0x400→0x430` latent |
| E3 ECL structural (CC/GC/MIS/MST) | 25/2/20/25 = 52 | 24/2/**0**/14 = 40 (benign 2/0/19/15) |
| E2 memcpy/intersubwarp | 4 TP, F4 FN | unchanged (F4 pending); F4 fixed later in T1a: 5 TP, E6a 9/9 (`eval/CP_ASYNC_REPORT.md`) |
| E5 litmus / canary | P=R=1.00, 33/33 oracle; 1 structural | unchanged, re-verified 68/68 |

## Verification

1. `rm -rf ScoR/microbenchmarks/artifacts/*` then `.env/bin/python -m pytest
   python/test_sync_dominance.py python/test_barrier_soundness.py` — run with the env's python
   directly, **not** under `conda run` (a nested `conda run` in `getall.sh` silently drops the
   atomic-scope sidecar and every atomic degrades to a plain access). Result: 68 passed.
2. `eval/reanalyze.py` re-runs the static leg on stored traces (no GPU) for fast checks of
   `sync_dominance` changes; the GPU re-runs used `eval/driver.py` with
   `CUVEIN_HOME=<worktree>` (runtime mirrored by symlinks) and the manifests
   `e0_fix*.json`, `e1.json`, `e1_determ.json`, `e1_tc.json`, `e1_determ_tc.json`,
   `e2_fix.json`, `e3_fix.json`, `e5_special_fix.json`.

## Files changed

- `python/sync_dominance.py`: exact pc-pair race matching; `atomic_scope` bare `ATOMS`→BLOCK;
  `dominance()` sync-free-path check; `benign` tag + `warp-po-ordered` opt-in class; new
  `hb_classes` cells; `--assume-warp-lockstep`.
- `python/hb_oracle.py`: reader pc in `last_reads` (WAR `a_pc`); `released` keyed by location.
- `sanalyzer/src/tools/pc_dependency_analysis.cpp`: `Reader{clock,pc}` in `last_reads`; WAR
  emits the reader pc (no `null`); `released` keyed by `Loc`. `.h`: record-order caveat.
- `eval/`: `driver.py` (`CUVEIN_HOME`, lockstep/scalar-clock forwarding, `--mode scalar-clock`,
  `--csv-suffix`), `aggregate.py` (benign/warp-po notes), `reanalyze.py`, `mk_e1_manifest.py`
  (flavor slug, repeatable `--graph`, `--only`), `mk_e0_manifest.py --lockstep`,
  `mk_e2_manifest.py --only`, manifests, `README.md`.

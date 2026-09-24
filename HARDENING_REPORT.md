# Hardening & Scaling the Multi-Warp Barrier HB Certificate — Report

Branch: `harden/trace-validity-and-scale` (off `cuVein`). Hardware: NVIDIA RTX 4060 Ti
(sm_89), CUDA 13.2, driver on the NCSU SLURM cluster. Phases 1 and 3 merged to `cuVein`;
Phase 2 finding+test merged; Phase 2 *model fix* deferred to a user decision; Phase 4
delivered as a harness + large apps.

A note on method: I distinguish **proved-in-effect** (a checked invariant that held across
N real traces), **tested** (a specific verdict asserted), and **assumed/unverified**.

---

## Phase 0 — baseline (starting state was stale)

At session start the working tree was at `08dfec5` (pre-barrier-fix); a fresh `git pull`
mid-session moved it to `871c466`, which already contains the prior agent's multi-warp
`__syncthreads` fix (`031f47d`: `pending_bar`/`pending_barriers` instance assembly in both
`hb_oracle.py` and `HbEngine`, plus `test_barrier_soundness.py`). I initially read the stale
tree and wrongly concluded the fix was missing; corrected after the pull. Everything below is
against `871c466`.

---

## Phase 1 — trace-validity (TV) invariants  [MERGED to cuVein]

**Changed.** Four collector-trace assumptions turned into runtime invariants, identically in
`hb_oracle.py` (raises `AlignmentError`) and `HbEngine` (loud stderr banner + `tv_violation`
recorded in the kernel JSON; gated by `YOSEMITE_HB_STRICT`, ON by default):

- **TV-barrier-overfill** — arrivals at a `(block, bar_index)` instance must never exceed the
  expected participant count (strict `>`).
- **TV-barrier-completion-order** — a warp blocked at a not-yet-fired barrier must not issue a
  post-barrier memory access before its instance completes (the segmentation property the
  barrier-instance assembly relies on).
- **TV-expected-nonzero-multiwarp** — the per-warp fallback (unknown expected count) with >1
  warp at the instance is exactly the pre-fix bug → raise instead of silently degrading.
- **TV-seq-monotonic** — events consumed in strictly increasing seq (oracle asserts it on the
  external JSON; the engine consumes the trace buffer in native order → monotonic by
  construction, documented not re-checked).

**Tested.** `test_barrier_soundness.py` rebuilt with a norace multi-warp control (expect 0), a
**positive control** (two post-barrier cross-warp writes, no second barrier → genuine WAW that
must be reported), one test per TV invariant (each violation must raise), and a valid-trace
guard (must not raise). 7/7 pass. So neither a "reports-0-on-everything" nor a
"raises-on-everything" regression can pass.

**Proved-in-effect.** Full ScoR corpus (32/32 traces) regenerated with strict ON →
**ZERO TV violations**. Canary → still **2 WAW**. `test_hb_engine_matches_oracle` runs (not
skipped) → **engine == oracle, 0 mismatches** on all 32 + canary.

**Assumed/unverified.** The four invariants are the collector assumptions I could make
*checkable and check them holding*; other collector properties (e.g. address correctness,
lane-mask fidelity) remain assumed. `TV-seq-monotonic` in the engine is structural, not
actively asserted.

---

## Phase 2 — relaxed-atomic / memory-model question  [FINDING: model UNSOUND; fix deferred]

**The exact rule.** `sync_dominance.atomic_scope`: opcode base in `{ATOM,ATOMG,ATOMS,RED}`;
scope = the token *after* `.STRONG.` mapped `{CTA,SM→BLOCK, GPU,SYS→GRID}`; **no `.STRONG`
token → NONE**. The runtime oracle/engine gate the release/acquire HB edge on this `.STRONG`
scope **alone** and never consult a fence (MEMBAR is used only by the *static* HBGraph R3
chain, not the runtime model).

**Discriminating test** (`testdata/atomic_mm_handoff.cu`, `test_atomic_memory_model.py`): a
cross-warp producer→consumer handoff of a non-atomic global via an atomic flag, in two
versions differing only in the flag's memory order.

**Verdict — BOTH report norace ⇒ UNSOUND.** On sm_89/CUDA 13.2 the relaxed and the
release/acquire device-scope atomics disassemble to the *identical* opcode
`ATOM.E.{EXCH,ADD}.STRONG.GPU`; the **only** SASS difference is `MEMBAR.SC.GPU` +
`MEMBAR.ALL.GPU` in the strong version (from `__threadfence` + release), absent in the relaxed
one. `.STRONG` is a *coherence-scope* marker present on relaxed atomics too — not a
release/acquire marker. So `atomic_scope` gives the relaxed flag GRID scope, the model orders
the surrounding non-atomic read after the write, and reports **0 races** for a handoff that
genuinely races. That is a **false negative → unsound for the certificate**. `handoff_strong`
→ 0 races (a plain-assert control that must always hold); `handoff_relaxed` → race is
`xfail(strict)` documenting the known unsoundness (flips to a failure once fixed).

**Corpus impact of a naive fix.** 8/32 corpus binaries have a non-NONE atomic with no MEMBAR;
**4 are `norace_*_atom`/`blkatom` cases that are race-free *because of* sound atomic-atomic
same-address coherence** (coherence needs no fence). A blanket "unfenced atomic → NONE" flip
would turn those into false positives. So the corpus genuinely depends on scope-based
coherence, and per the task I did **not** silently change the classification.

**Proposal (needs your decision).** Separate the two roles of `released[addr]`:
(1) atomic→atomic same-address **coherence** — keep scope-based (sound, no fence needed);
(2) release/acquire ordering of **non-atomic** state — require a qualifying fence (the
`postdom(release)`/`dom(acquire)` MEMBAR condition the static R3 chain already computes). The
sidecar would then mark an atomic PC "synchronizing" only when fence-qualified. This is
corpus-affecting and non-trivial; I can implement it on the branch if you want.

---

## Phase 3 — record the coherence profile Π  [MERGED to cuVein]

**Changed.** For each address touched by ≥1 atomic, both the oracle report and the engine JSON
now emit `coherence_profile`: the observed sequence of `(tid, that-thread's-atomic-index)` in
event order plus a stable 64-bit FNV-1a hash. `coherence_hash` is byte-identical in Python and
C++.

**Proved-in-effect / tested.** Full corpus regenerated: **32/32 traces carry a
`coherence_profile`** (33 atomic addresses total), **race counts byte-identical** to the
pre-change baseline (0 verdict changes), and `test_hb_engine_matches_oracle` now also asserts
**engine profile hashes == oracle** on all 32 (0 mismatches). Canary: its two flag addresses
each show their 3-atomic observed order.

---

## Phase 4 — scale evaluation  [harness + large apps; iGUARD blocked]

**Harness** (`python/scale_harness.py`): runs an app through `YOSEMITE_HB_TRACE=1 -n 1`,
records event count, engine race count (deduped + grouped by pc-pair), TV violations,
coherence-profile size, A/B wall time (scalar-clock dump vs vector-clock dump+engine via `YOSEMITE_HB_MODE`), and
the exact-VC oracle verdict + peak RSS + wall **where it fits** — flagging engine-only rows
above the fit bound as **UNVERIFIED against the oracle**. (Fixed a bug where `getall.sh`
doesn't forward app args; the harness now runs accelprof itself with args.)

**Results** (RTX 4060 Ti sm_89; engine Δt = dump+engine − dump-only; "engine-only" = the
exact oracle did not fit, so that verdict has NO independent cross-check):

| app | grid | threads | events | engine races (pc-pairs) | TV | oracle verdict | oracle peak RSS | engine==oracle | engine Δt |
|-----|------|--------:|-------:|:-----------------------:|:--:|----------------|----------------:|:--------------:|----------:|
| tiled_gemm N=128 | 4×4   | 16,384  | 94,720    | 0 (0) | none | 0 races | 1.41 GB | true | +4.9 s |
| tiled_gemm N=256 | 8×8   | 65,536  | 755,712   | 0 (0) | none | 0 races | 8.23 GB | true | +53.8 s |
| tiled_gemm N=512 | 16×16 | 262,144 | 6,037,504 | 0 (0) | none | **SKIPPED (events > 2M cap)** | — | **engine-only, UNVERIFIED** | +521 s |
| grid_workqueue   | 128×1 | 16,384  | 1,024     | 0 (0) | none | 0 races | 67 MB | true (Π length 768) | +0.6 s |

Reading the table: the 32-warp-per-block barrier app is **race-free and TV-clean at every
size** (the pre-fix per-warp bug would have flooded these with spurious cross-warp RAWs). The
exact O(threads) VC oracle fits through N=256 (8.2 GB RSS) and **does not fit N=512** (≈64 GB
projected) — that row is engine-only and explicitly unverified against the exact spec. The
grid work queue's single global counter carries a **768-long observed coherence order Π** and
is correctly race-free (distinct outputs). The engine's own per-thread clocks are also
O(threads); it completed N=512 in C++ where the Python oracle could not fit in host RAM, but
without the oracle that verdict has no cross-check.

**Cross-check.** compute-sanitizer `racecheck` on the tiled-GEMM shared memory → **0 hazards**,
independently confirming the barrier-heavy app is genuinely race-free (the HB engine agrees:
0 races).

**iGUARD head-to-head — BLOCKED (honest).** iGUARD ships precompiled **sm_70 (Volta) / sm_60
(Pascal)** binaries linked with **static cudart**. Two independent blockers on this cluster:
(1) accelprof's LD_PRELOADed `libcompute_sanitizer.so` resolves CUDA runtime symbols from the
target process, which requires `--cudart shared`; the static binaries fail with
`undefined symbol: cudaDeviceGetStreamPriorityRange`. (2) No Volta/Pascal-sm_60 GPU exists on
the cluster, so the binaries JIT from PTX to sm_75/sm_89 → the runtime PCs don't match the
sm_70 CFG accelprof extracts. Running the head-to-head requires **rebuilding the iGUARD
benchmarks from source** (their sources are external repos linked from iGUARD's README) with
a current `-arch` and `--cudart shared`. Not done this session; flagged as the concrete next
step.

**The scale wall (surfaced, not hidden).** The exact O(threads) VC oracle's peak RSS was
~1.4 GB at 16,384 threads; it does not fit the largest grids — those rows are the engine-only
(unverified) rows, marked as such. No compact/epoch engine was invented (that needs its own
correctness lemma first).

---

## Honest status of soundness & completeness

**Now backed by checked invariants + tests:** the multi-warp barrier soundness argument's
trace-validity assumptions are checked at runtime and **held with zero violations across the
entire ScoR corpus, the canary, and every scale app run** (Phase 1); engine ≡ oracle on races
*and* coherence-profile hashes across the corpus (Phases 1, 3); the barrier soundness test has
a real positive control; the observed coherence profile Π is now recorded so the per-profile
certificate matches the artifact (Phase 3); the large barrier app (32 warps/block) is
demonstrably clean post-fix, cross-checked by racecheck (Phase 4).

**Still resting on unverified assumptions:** (1) **The atomic release/acquire path is UNSOUND
on unfenced/relaxed atomics** — the model treats a `.STRONG`-scoped relaxed atomic as
synchronizing and can hide a real race (Phase 2). This is the most important open soundness
gap; the fix is proposed but deferred to your decision. (2) Collector correctness beyond the
four TV invariants (addresses, lane masks, that the emitted schedule reflects the hardware
schedule) remains assumed. (3) Large grids are **engine-only, unverified against the exact
oracle** — the exact spec does not fit there, so those verdicts have no independent
cross-check. (4) The iGUARD head-to-head (and thus the FP comparison against prior work) was
not run; it needs a source rebuild.

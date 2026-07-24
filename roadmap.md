# Implementation Roadmap: cuVein-Based GPU Data-Race Detection (v3)

v2 revised around the **dominance-based bottleneck ordering method**, which replaces the cut/separator (sync-edge-deletion) approach from v1. The deletion method was discarded because unreachability in a sync-deleted graph conflates two opposite situations — "every path crossed a sync" (ordered) and "no path ever existed" (divergent siblings, concurrent) — producing false negatives on divergent-branch races and on asymmetric-sync branches. The replacement never uses reachability as a proxy for ordering.

v3 revised to match the implementation (`python/sync_dominance.py`): there is **no standalone static leg**. Detection is trace-driven — one tool joins a kernel's CFG (used only for sync structure) with its cuVein trace and emits per-edge verdicts. Participation masks / SASS register dataflow were dropped (the trace already carries access flags and masks), and v2's Phase 5.1 (atomic/fence ordering) was pulled forward into the core: the ScoR corpus made it a correctness requirement, not future work.

## The core method (Phase 1's contract)

Conflicting PC pairs come from the cuVein trace (shadow-memory dependency edges with a topological-distance histogram), never from static enumeration. For each observed pair (u, v), ordering strength is the max over three sources:

- **Dominance (barriers/warpsync):** over the sync-split region graph, a qualifying sync s orders the pair iff **s ∈ postdom(u) ∩ dom(v)** or **s ∈ postdom(v) ∩ dom(u)** — both threads provably execute s, one before its access, one after. Participation is part of the definition, not an assumption.
- **Atomic coherence:** two same-address atomics are ordered by hardware coherence at **min of their `.STRONG` scopes** (SM/CTA → block, GPU/SYS → grid; unknown/weak → ⊥).
- **Scoped happens-before closure (ScoRD model):** release-fence + observed atomic synchronization + acquire-dependency chains order flag/lock-protected accesses transitively (details in Phase 1.7).

- **Race verdict:** the pair races at its observed Topological Distance d iff `strength(u,v) < d` on the scope lattice ⊥ < warp < block < grid.

Validated cases: divergent siblings → no qualifying sync → race ✓. Pre-branch barrier vs. post-branch accesses → barrier post-dominates the init store and dominates both arms → ordered ✓. Sync on one arm only → fails postdom on the sync-free arm → race ✓. Loop-carried same-PC conflict → sync qualifies iff it lies on every cycle through u ✓. ScoR: scoped atomics at sufficient distance → ordered; fence/lock/indirect-HB `norace_*` → ordered; every deliberately broken `race_*` variant (under-scoped atomic, missing fence, unlocked arm, wrong-direction chain) → race ✓.

Complexity: dominance + post-dominance are single-pass standard analyses computed once per kernel; per-pair queries are set intersections plus a max; the HB closure is a DFS over a graph with one node per traced memory PC. No per-scope graph variants, no closures over deleted graphs.

---

## Phase 0 — Foundations: verified alignment and binary acquisition *(implemented)*

1. **Test corpus.**
   - **ScoR microbenchmark suite** (`ScoR/microbenchmarks/`): labeled `race_*` / `norace_*` binaries covering scoped atomics, fences, locks, and indirect (transitive) happens-before, at intrawarp/interwarp/interblock distances. Primary accuracy corpus — every `norace_*` is a false-positive control, every `race_*` a false-negative control.
   - **cuHadron examples** (`cuHadron/`): divergent-subwarp shared-memory races (the method-regression kernels: divergent siblings — the case that killed mutual-unreachability; one-sync-arm — the case that killed edge deletion).
2. **Binary acquisition (`getall.sh`), no cuVein modification:** `cuobjdump -xelf all` → `nvdisasm -bbcfg -poff` per cubin (one cfg.dot per kernel) + `accelprof -t pc_dependency_analysis` for the trace JSON. JIT/cache ELF-carving documented as plan B.
3. **Verified alignment stage (hard-fail, in `sync_dominance.py`):** kernel name (c++filt-demangled cluster symbol vs. trace JSON `kernel_name`), PC invariant (every traced PC lands on an LD/ST/ATOM/RED-family opcode in the CFG). Any mismatch aborts — no silent verdicts.

**Exit criteria (met):** one command per corpus example yields an aligned (trace, cubin, CFG) triple or fails loudly; `python/test_sync_dominance.py` regenerates and checks the whole ScoR corpus.

---

## Phase 1 — Dominance engine joined against the trace (`python/sync_dominance.py`)

**Goal:** the bottleneck ordering method, evaluated only on the PC pairs the trace actually observed. One tool: `sync_dominance.py <kernel_cfg.dot> <kernel_N.json>` → per-edge verdicts (`<trace>.races.json` + summary; exit 1 on alignment failure, 2 on unknown sync opcodes).

The CFG is used **only for sync structure**. Memory space, read/write/atomic type, and warp masks come from the trace flags — never re-derived from SASS operands (no register dataflow, no participation-mask reconstruction).

1. **CFG parser** (pydot): nvdisasm Mrecord labels → per-block `(offset, opcode)` lists; block edges from the dot; every `EXIT` gets a synthetic edge to a unified virtual exit node.
2. **Sync-aware tokenizer** (prefix + modifier, never exact-string):
   - `BAR.SYNC*`, `BAR.RED*` → block scope, qualifying; `BAR.ARV*` arrive-only, non-qualifying.
   - `WARPSYNC` → warp scope, qualifying (mask matched dynamically via the trace).
   - `MEMBAR.*` → fence: **non-qualifying for barrier dominance**, but real scope recorded (`CTA`→block, `GPU`/`SYS`→grid) for release-edge certification (1.7).
   - `ATOM/ATOMG/ATOMS/RED` `.STRONG.{SM,CTA,GPU,SYS}` → atomic coherence scope (1.6).
   - Any unrecognized sync-family opcode → **unknown-sync counter**, nonzero exit (CI tripwire).
3. **Region splitting + dominance:** blocks terminated at sync instructions; each sync is its own node (so it appears in dominator sets); dominator/post-dominator sets once per kernel (networkx); `strength(u,v)` = max scope over qualifying syncs in `postdom(u)∩dom(v) ∪ postdom(v)∩dom(u)`.
4. **Candidate predicate on trace edges:** non-cold-miss ∧ distance beyond intra-thread ∧ ≥1 write/atomic endpoint; warp-same-inst read-read excluded, same-inst multi-lane writes kept (ITS territory, strength ⊥ by construction).
5. **Loop-carried conflicts:** same-PC pair (u,u) ordered across iterations iff a qualifying sync of sufficient scope lies on every cycle through u's region.
6. **Atomic coherence ordering:** both endpoints atomic → strength lifted to `min(scope(u), scope(v))` on the atomic scope map (SM/CTA → block, GPU/SYS → grid). Two same-address atomics race only if that scope is weaker than their distance (`race_interblock_blkatom`: SM×SM at grid → still race).
7. **Scoped happens-before closure** (ScoRD synchronization model; clears fence/lock/indirect `norace_*`):
   - *Sync edges (dynamic):* non-cold atomic–atomic trace edges — the shadow memory tracks flag/lock addresses like any data, so the synchronization itself is in the trace — usable iff min atomic scope ≥ that edge's own distance; direction ancient→current.
   - *Release po-edges (static, directional):* `u → a` iff a MEMBAR `f ∈ postdom(region(u)) ∩ dom(region(a))` with fence scope ≥ the following sync edge's distance (atomic u needs no fence, dominance-certified order suffices).
   - *Acquire po-edges (static):* `a → w` iff `region(a) ∈ dom(region(w))`; no fence needed — consumer accesses are dependency-ordered behind the spin-loop atomic. Exception (direction-independent): an ordinary *store* dominated by a **CAS** atomic sits in a competing critical section whose entry order is schedule-dependent, so it additionally needs an acquire fence of sufficient scope between the CAS and the store — `race_*lock-no-stf/blkfence*` are exactly this omission; non-CAS flag/spin handoffs pin their direction by dataflow and are exempt.
   - A residual RACE edge is upgraded to ORDERED iff a valid HB path exists in *either* direction. Cross-thread trace-edge direction is temporal only under **single-worker replay** (`accelprof -n 1` — per the cuVein author; now the `getall.sh` default, ScoR artifacts regenerated with it). Multi-worker replay records offline-analyzer processing order and can even mis-pair last-writers (hrf-indirect's old trace had `0x500→0x2e0` where true dataflow is `0x500→0x420`), so the search stays direction-agnostic for compatibility with such traces. Reported as `hb-chain` with the chain PCs, distinct from dominance-ORDERED.
   - *Known limitation:* PC-level HB assumes all dynamic instances of a PC are ordered alike — exact for one-thread-per-arm and lock-protected patterns; Phase 2 per-thread epochs are the precise upgrade.

Dropped from v2: the static concurrency pre-filter (the trace supplies observed pairs), SASS participation-mask analysis (trace carries masks), and the barrier-divergence diagnostic (deferred; needs mask reconstruction).

**Exit criteria:** cuHadron intersubwarp readwrite → exactly the divergent LDS/STS pair as RACE (strength ⊥ < warp) and the barrier-ordered init pair as ORDERED (strength block). ScoR suite → **every `norace_*` 0 races, every `race_*` ≥ 1 race**. Automated in `python/test_sync_dominance.py`.

---

## Phase 2 — Dynamic leg: sync events and per-thread epochs in cuVein

**Goal:** the one cuVein extension; per-thread epochs replace the two Phase 1 approximations that are PC-granular (the hb-chain closure and warp-same-inst handling) with per-instance ordering evidence.

1. **Instrument sync opcodes** in the Trace Collector using the Phase 1 tokenizer classification: BAR family, WARPSYNC (+ mask), MEMBAR family. Sync events interleave with memory events in the existing warp-granularity trace stream.
2. **Decode scope modifiers** on already-instrumented memory ops (`.STRONG.CTA/GPU/SYS`, acquire/release) — extra trace fields, no new instrumentation points.
3. **Per-thread (per-warp-slot) epoch counters — not per-CTA-global.** Each thread's barrier epoch advances only when *that thread's* warp executes the sync; a CTA-global counter would fabricate ordering for threads that skipped the barrier (dynamic mirror of the one-sync-arm bug). Warp epochs keyed by (warp, mask). Fence counters recorded but never used as ordering alone.
4. **Shadow entry extension:** widen GMEM entries to 128-bit (matching SMEM): last **writer** + last **accessor** slots (iGUARD split), each with epoch snapshot(s), PC offset, flat thread ID, generation. Preserve the quartered demand-paged layout; measure paging impact.
5. **Epoch-based dynamic ordering check:** accesses from threads t1, t2 are dynamically ordered by a barrier iff both threads' relevant epoch counters advanced past a common sync instance between the accesses — same participation logic as the static side, evaluated on the observed execution.
6. **Trace schema fixes:** per-access-instance flags (no `READWRITE GLOBALSHARED` unions), documented cold-miss edge semantics (cold-miss edges excluded from race logic), confirm `intra_instance_launch` ≡ warp-same-inst.

**Exit criteria:** writewrite trace shows epoch delta on init-store→divergent-store edges and none on the divergent WAW edge; one-sync-arm trace shows *no* fabricated epoch delta for the non-syncing thread.

---

## Phase 3 — Candidate extraction and dynamic verdict *(folded into Phase 1)*

The candidate predicate, per-edge verdict, and report v1 (racing PC pair, conflict scope, WAW/RAW/WAR from edge direction, contested weight, ordering syncs / hb-chain) are implemented in `sync_dominance.py`. Remaining here:

1. **Source-line attribution** via `-lineinfo` (nvdisasm line table → PC ranges) in the report.
2. **Epoch-based verdict** (once Phase 2 lands): per-thread epoch comparison at the conflict's scope → observed race or ordered, replacing the PC-level approximations.

**Exit criteria:** RACE/FIXED build pairs → exactly one report / zero. Permanent CI false-positive control (subsumed by the ScoR `norace_*` == 0 assertion).

---

## Phase 4 — Verdict classification *(join implemented; classification pending Phase 2)*

The pipeline join (trace PCs → dominance/coherence/HB strength vs. conflict scope) is Phase 1's core loop. Remaining:

1. **Verdict matrix** (needs Phase 2 epochs for the "dynamically ordered" axis):
   - Observed race ∧ strength < scope → **structural race** (every execution).
   - Observed race ∧ strength ≥ scope → **canary cell**: the model says ordered but execution disagreed — indicates conditional/named barriers beyond the model, or an epoch bug. Investigate immediately.
   - Dynamically ordered ∧ strength < scope → **latent race** (lucky schedule); lower-severity report.
2. **Masked syncwarp qualification:** WARPSYNC currently qualifies unconditionally at warp scope; validate its mask against the trace's dynamic warp masks (both conflicting lanes covered) before trusting warp-scope verdicts on masked syncs.
3. **Diagnostics:** attach PCDepGraph neighborhood + per-PC racing-traffic volume (weighted out-degree over racing edges) — the race-in-context output no existing detector provides.

**Exit criteria:** writewrite triple → single *structural race* end-to-end; one-sync-arm kernel → structural race; a scheduling-sensitive example → latent race demonstrated.

---

## Phase 5 — Hard cases (reduced again: atomic/fence ordering moved into core)

v1's 5.3 (participation) became core in v2; v2's 5.1 (fence/atomic pairing) is now core Phase 1.6–1.7 — atomic coherence scope plus the ScoRD-style scoped HB closure, forced by the ScoR corpus. Remaining:

1. **grid.sync recognition:** pattern-match the fence + atomic-counter spin idiom; accept cooperative-launch metadata as a hint. Concrete reduction of the grid-scope problem. (The HB closure already orders the constituent atomics; recognizing the idiom as a *barrier* would extend ordering to all grid threads, not just chain participants.)
2. **Named / conditional barriers:** `bar.sync N`, `bar.arrive/wait` producer-consumer pairs, barriers whose *instances* differ across threads despite one static PC. Dominance handles the all-paths structure; instance matching under data-dependent trip counts remains open. The Phase 4 canary cell is the tripwire for pulling this forward.
3. **ITS-era intra-warp same-inst writes:** per-lane ordering assumptions made explicit.
4. **Per-instance HB precision:** the PC-level HB closure can over-order kernels where many threads share one synchronization PC with mixed roles; resolved by Phase 2 per-thread epochs, not by more static modeling.

All defensible as future work in a first paper; the ScoR corpus exercises none of them.

---

## Phase 6 — Evaluation and paper artifacts

1. **Accuracy:** ScoR microbenchmark suite as the scoped-synchronization accuracy table (all `norace_*` clean, all `race_*` caught — already in CI); iGUARD benchmark suite (github.com/csl-iisc/iGUARD-SOSP21) — races found, false positives (target: zero), plus structural/latent classification iGUARD cannot produce. Cross-check compute-sanitizer racecheck on shared-memory cases.
2. **Differentiators to demonstrate:** compiler-transformed races (collapsed-loop example), latent races invisible to single-execution tools, asymmetric-sync races (one-sync-arm — a class where deletion-style static methods are unsound), scoped-atomic and transitive-HB classification (ScoRD-class precision from a binary-only tool), race-in-context diagnostics.
3. **Overhead:** vs. baseline, vs. cuVein-without-race-logic (isolating epoch + 128-bit entry cost), vs. iGUARD's ~5×, vs. compute-sanitizer. Reuse cuVein's worker-scaling methodology.
4. **Paper figures locked early:** (a) aligned triple: source race → PCDepGraph WAW edge → dominance query showing strength ⊥; (b) same-kernel false-positive control (barrier-separated twin edge, strength = block); (c) the bottleneck formalization: `strength = max(dominance, coherence, hb-chain)` on the scope lattice, with the deletion-method counterexamples as motivation; (d) verdict matrix, one real example per cell.

---

## Risk register

| Risk | Phase | Mitigation |
|---|---|---|
| Trace/CFG mismatch recurs silently | 0 | Hard-fail verification (name, PC-on-memory-opcode) — implemented |
| JIT cache format changes across drivers | 0 | Format-agnostic ELF carving; LD_PRELOAD shim plan B |
| Sync opcode variants missed (BAR.ARV, DEFER_BLOCKING, arch drift) | 1–2 | Prefix/modifier matching + unknown-sync-opcode counter failing CI when nonzero — implemented |
| Dominance model vs. named/conditional barrier instances | 1, 5.2 | Canary cell in verdict matrix; corpus kernel per new pattern before trusting verdicts on it |
| Regression to reachability-as-ordering thinking | 1 | Divergent-siblings + one-sync-arm kernels as permanent method-regression tests |
| Atomic-scope map wrong for an arch (`.SM`/`.CTA`/`.GPU`/`.SYS` drift) | 1 | Unknown scope suffix → ⊥ (over-reports); ScoR `race_*blkatom*` controls pin the SM→block mapping |
| PC-level HB closure over-orders multi-instance sync PCs (false negatives) | 1, 5.4 | `hb-chain` verdicts labeled distinctly from dominance-ORDERED; ScoR `race_*` ≥1 assertions in CI; Phase 2 epochs are the precise fix |
| Per-thread epoch state size in Offline Analyzer | 2 | Counters live in per-worker CTA-scoped state (SMEM-pool pattern), not global |
| 128-bit GMEM entries blow paging footprint | 2 | Quartered layout preserved; measure on XSBench-class workload first |
| Last-access shadow depth misses W₁ | 2 | Writer/accessor split; iGUARD depth-2/4/8 null result as justification |
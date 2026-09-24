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
   - *Known limitation:* PC-level HB assumes all dynamic instances of a PC are ordered alike — exact for one-thread-per-arm and lock-protected patterns, but it over-orders when instances differ (the canary). Phase 2's scoped vector-clock engine is the realized precise upgrade: on the canary's identical trace it reports the 2 WAW races this closure misses, as a consequence of per-address clocks.

Dropped from v2: the static concurrency pre-filter (the trace supplies observed pairs), SASS participation-mask analysis (trace carries masks), and the barrier-divergence diagnostic (deferred; needs mask reconstruction).

**Exit criteria:** cuHadron intersubwarp readwrite → exactly the divergent LDS/STS pair as RACE (strength ⊥ < warp) and the barrier-ordered init pair as ORDERED (strength block). ScoR suite → **every `norace_*` 0 races, every `race_*` ≥ 1 race**. Automated in `python/test_sync_dominance.py`.

---

## Phase 2 — Dynamic leg: sync events + scoped vector-clock happens-before *(engine implemented & corpus-validated; verdict matrix + oracle-cross-check pytest wired; scale knobs pending)*

**Goal:** the one analyzer/GPU extension supplying per-instance ordering evidence, replacing the two PC-granular Phase 1 approximations (the hb-chain closure and warp-same-inst handling). Built as an **exact vector-clock happens-before** mechanism — correct by construction — *not* the scalar per-thread epochs v3 sketched below. The canary, named barriers, masked syncwarps and loop-carried handshakes all fall out of the clocks with no pattern special-cased; that generality was the explicit design mandate (a case-specific canary fix was rejected).

**Design as built** (diverges from the 2.1–2.6 sketch wherever reality forced it):

1. **Sync instrumentation (GPU).** BAR family and WARPSYNC are instrumented via compute-sanitizer instruction patch points (`SANITIZER_INSTRUCTION_BARRIER`, `_SYNCWARP`); a first-lane callback emits one `MemoryType::{Barrier,Syncwarp}` record — participation = arrived-lane `active_mask` (barrier) / syncwarp mask — into the existing warp-granularity stream. **No MEMBAR instrumentation:** compute-sanitizer exposes no general fence patch point (only Hopper `WARPGROUP_FENCE`), so fence ordering stays CFG-static (Phase 1 `release_scope`). This is a hard tool boundary, not a deferral — fence-omission `race_*` are **static-only by necessity**. (NVBit *can* match `MEMBAR` by opcode if a fence-dynamic leg is ever wanted.)
2. **Atomic scope from the CFG, not instrumented** (2.2 dropped). `.STRONG.{CTA,SM,GPU,SYS}` is a static SASS property; `python/atomic_scope_sidecar.py` distills a `pc→scope` table from the CFG `.dot` (which `getall.sh` produces *before* the trace run) into a sidecar the analyzer reads (`YOSEMITE_ATOMIC_SCOPE_FILE`). No new trace fields.
3. **Scoped vector clocks, not scalar epochs** (supersedes 2.3). Every thread `(block<<10 | warp<<5 | lane)` carries a sparse VC. HB comes only from sync events: a barrier/syncwarp joins its *actual participants* then ticks each own component; a release atomic publishes the releaser's clock **keyed by address** at its scope; an acquire joins it back iff `min(acquire_scope, release_scope)` covers the two threads (GRID = any block / BLOCK = same block / NONE = never). A conflict (same location, ≥1 write, distinct threads) is a race iff the two instances' clocks are HB-unordered. Because releases are per-address, the canary's `flag[i]` never leaks block-*i*'s clock to a block that only touched `flag[j]` — precisely the over-ordering PC-level HB commits.
4. **Two artifacts, one spec.** `python/hb_oracle.py` is the exact full-VC oracle (offline over the `hb_events` dump, the executable correctness spec). A streaming **C++ engine** in `pc_dependency_analysis.cpp` is a 1:1 port that runs in-analyzer over the raw buffer in temporal order (`-n 1`) — per-thread sparse VCs + address-keyed release map + writer/reader location shadow — emitting `hb_races` into `kernel_N.json` under `YOSEMITE_HB_TRACE`. The engine is a **`.cpp` file-static singleton, not a `PcDependency` member**: adding any member re-triggers a latent heap-corruption UB in a non-instrumented dependency (ASan-clean, so *not* in `libsanalyzer`; documented in the build memo). The 128-bit shadow-entry merge (2.4) was therefore *not* done — the engine keeps its own `std::map` location shadow.
5. **Scale knobs deferred, set to exact for the corpus.** The engine uses **unbounded** VCs + **full** reader sets — O(threads) memory, O(threads) per barrier/atomic join. FastTrack epoch collapse (per-location read/write *epoch* vs. a reader set) and bounded per-thread clocks are the calibration knobs, left exact so the C++ engine matches the oracle bit-for-bit; `YOSEMITE_HB_NO_ENGINE` isolates dump-vs-engine cost for that calibration.

**Validated.** Canary (documented PC-level false negative, `sync_dominance` = 0) → **2 WAW races**, C++ engine == oracle exactly. Full ScoR corpus (32 binaries) → **C++ `hb_races` == oracle `races`, 0 mismatches**, exercising reads (RAW/WAR), barrier joins, BLOCK/NONE-scope coherence, and fence-based release/acquire (ordered via the atomic flag; the fence is redundant for HB). writewrite → race caught.

**Overhead** (reduction, 4M elts → 136K events, best-of-4, single GPU, `-n 1`):

| stage | time | vs bare |
|---|---|---|
| bare (no instrumentation) | 0.89 s | 1× |
| compute-sanitizer + `pc_dependency` (HB off) | 2.25 s | 2.5× |
| + event dump | 3.55 s | 4.0× |
| + engine (`HB_TRACE=1`) | 7.54 s | 8.5× |

Normal mode (flag off) adds **zero** cost — engine gated off, and off-class so no layout change. The base 2.5× is compute-sanitizer, not Phase 2. Within the HB delta the engine (~+4 s) dominates the dump (~+1.3 s), driven by barrier-grown vector clocks — the exact term the scale knobs target. Reduction is near-worst-case (all barriers); atomic-light kernels show a smaller engine delta.

**Exit criteria:** canary → 2 WAW as a *consequence* of per-address clocks (met); C++ engine == VC oracle on every corpus binary (met, 0 mismatches). **Done since:** verdict-matrix wiring (Phase 4.1) consuming `hb_races` — canary STG pair now classifies `structural` where the R3 chain alone said ordered; pytest formalization of the cross-check (`test_hb_engine_matches_oracle` in `test_sync_dominance.py`, asserts engine `hb_races` == oracle `races` per binary). **Pending:** bounded/epoch scale knobs calibrated on iGUARD/XSBench-class workloads; the loopcarried/namedbar/maskedsync microbenches.

*Original v3 sketch, retained for reference (superseded by the above):* per-thread scalar barrier epochs advanced only when that thread's warp executes the sync; 128-bit GMEM shadow entries with writer/accessor epoch snapshots; epoch-delta ordering check. Replaced by exact VCs because scalar epochs cannot represent partial-participation or address-keyed atomic handoff without becoming vector clocks anyway.

---

## Phase 3 — Candidate extraction and dynamic verdict *(folded into Phase 1)*

The candidate predicate, per-edge verdict, and report v1 (racing PC pair, conflict scope, WAW/RAW/WAR from edge direction, contested weight, ordering syncs / hb-chain) are implemented in `sync_dominance.py`. Remaining here:

1. **Source-line attribution** via `-lineinfo` (nvdisasm line table → PC ranges) in the report.
2. **Epoch-based verdict** (once Phase 2 lands): per-thread epoch comparison at the conflict's scope → observed race or ordered, replacing the PC-level approximations.

**Exit criteria:** RACE/FIXED build pairs → exactly one report / zero. Permanent CI false-positive control (subsumed by the ScoR `norace_*` == 0 assertion).

---

## Phase 4 — Verdict classification *(join + verdict matrix implemented)*

The pipeline join (trace PCs → dominance/coherence/HB strength vs. conflict scope) is Phase 1's core loop. Remaining:

1. **Verdict matrix** *(wired — `sync_dominance.analyze` consumes the Phase 2 engine's `hb_races` when the trace carries them; `_hb_class` assigns the cell, added as `hb_class` per verdict and a `summary.hb_classes` breakdown. Without `hb_races` it falls back to the R3 chain, as before).* Cells, crossing the static all-schedule axis (R1 dominance / R2 coherence, and the R3 handshake) with the observed dynamic HB race:
   - Observed race ∧ **not** R1/R2-ordered → **structural race** (chain over-ordered at PC level, or nothing ordered it — the false negative the dynamic leg corrects). *Live: the canary STG pair `0x1f0→0x160` — static `strength = none`, R3 chain present (would say ORDERED), dynamic HB = race → `structural`.*
   - Observed race ∧ **R1/R2**-ordered → **model_bug cell**: R1/R2 are all-schedule sound, so a race here means an unsound rule or a trace/CFG misalignment. Investigate immediately. (Empty on the whole corpus — a tripwire.)
   - Dynamically ordered ∧ nothing proves all-schedule ordering → **latent race** (lucky schedule); lower-severity report.
   - Dynamically ordered ∧ some all-schedule proof orders it → **ordered** (the common norace case; R3-handshake norace binaries land here, not latent).
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
3. **Overhead:** vs. baseline, vs. tool-without-HB-logic (isolating the engine cost via `YOSEMITE_HB_NO_ENGINE`), vs. iGUARD's ~5×, vs. compute-sanitizer. Reuse cuVein's worker-scaling methodology. *First data point* (reduction, 136K events, single GPU, `-n 1`, exact/unbounded engine): bare → sanitizer+tool **2.5×** → +event-dump 4.0× → +engine **8.5×**; normal mode (HB off) zero cost. The engine term (~4× of the 8.5×) is the exact-VC cost the scale knobs (FastTrack epoch collapse, bounded clocks) must retire — the headline overhead number is *not* meaningful until they are calibrated.
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
| PC-level HB closure over-orders multi-instance sync PCs (false negatives) | 1, 5.4 | `hb-chain` verdicts labeled distinctly from dominance-ORDERED; ScoR `race_*` ≥1 assertions in CI; **Phase 2 scoped-VC engine implemented** — catches the canary (2 WAW) and matches the VC oracle on all 32 corpus binaries (0 mismatches) |
| Per-thread HB state size in analyzer | 2 | Engine state off-class (file-static singleton), reset per kernel; bounded per-thread clocks are the deferred scale knob |
| Latent heap-corruption UB re-triggered by any `PcDependency` layout change (`malloc(): invalid size` at init) | 2 | Engine kept off-class → zero layout change; ASan-clean in `libsanalyzer` (with `protect_shadow_gap=0`) so the UB is in a non-instrumented dep; root-cause deferred, documented in build memo |
| Exact unbounded vector clocks don't scale (O(threads) joins under heavy barriers; ~4× of the 8.5× on reduction) | 2, 6 | Exact only to match the oracle on the corpus; FastTrack epoch collapse + bounded clocks are the knobs; `YOSEMITE_HB_NO_ENGINE` isolates the cost for calibration |
| Atomic-scope sidecar wrong/missing (pc→scope from CFG) drops HB → over-report | 2 | Skips unparseable dots (empty cubin stubs) instead of aborting; cross-checked against the VC oracle on all 32 binaries (0 mismatches) |
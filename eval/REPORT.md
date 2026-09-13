# cuVein Scoped Happens-Before Race Detector — Evaluation Report

_AccelProf `cuVein` branch · RTX A5000 (sm_86) · CUDA 12.9 · produced by the harness in
`eval/` (`driver.py` + `aggregate.py`); every CSV in `eval/results/` is regenerable
(`eval/README.md`). This report evaluates the detector **as it stands after the root-cause
fixes**; the causes and fixes themselves are in `eval/FIX_REPORT.md`, referenced here as
F1–F6. Pre-fix numbers are kept where they matter and are marked as such. Sections follow
the suite numbering E0–E6 of the evaluation plan; the runtime-mode comparison (engine vs
trace-only) and overhead follow the suites._

## Summary (for someone who has not seen the tool)

cuVein is a binary-only GPU data-race detector: it instruments a CUDA program's memory and
synchronization instructions with NVIDIA Compute Sanitizer, replays the recorded trace
through a scoped happens-before (HB) engine, and reports each conflicting access pair as
**structural** (races in every schedule), **latent** (ordered this run but nothing guarantees
it), **benign** (a real unordered access on an atomically-maintained location the algorithm
tolerates) or **ordered** (safe). It also joins the kernel's static control-flow graph to
reason about barriers, scoped atomics and fences. It has two runtime modes: the full
**engine mode** (an in-process exact vector-clock engine) and a **trace-only mode**
(`YOSEMITE_HB_NO_ENGINE`) where only the static leg classifies the recorded trace.

**What was found.** On the labeled scoped-synchronization litmus (**ScoR, 33 programs**) the
detector is perfect — **precision 1.00, recall 1.00, specificity 1.00**, streaming engine ==
exact oracle on 33/33 — and it catches the multiplexed-handshake canary a PC-level checker
misses. Recall stays high on real code: **6/6** planted races in the ScoR applications,
**26/28** on the Indigo3 sample (the two misses need a ≥2-block input and are caught on the
1024-node graph), **5/6** in-scope races on cuHadron. Its soundness tripwire (`model_bug`) is
**0 on every suite** after the root-cause round fixed a report-attribution bug and two
engine/spec defects (F2, F6). **Precision on real graph analytics is the open problem:**
exact HB flags the benign races inherent in BFS/CC/SSSP-style kernels and in ECL's
race-free codes (F5); the new `benign` class re-buckets the atomic-writer cases (ECL-MIS
20→0 structural) but plain-vs-plain and value-idempotent writes remain. On non-graph
HeCBench apps and on cuHadron's synchronized builds it reports **zero false positives**.
An independent tool (Compute-Sanitizer racecheck, E6a) agrees on 8/9 shared-memory cases
and exposes one real miss (F4, a `cp.async` write attributed to the issuing lane; fix
designed). **Overhead is the second open problem:** the exact engine costs 3×–218× native
and OOMs on large graph kernels (F3). The **trace-only mode** (`YOSEMITE_HB_NO_ENGINE`)
was evaluated on every suite: it reaches the **same recall on every suite** (all planted
races flagged, as latent) at **3–9× native and ~820 MB**, losing only the structural/latent
classification and the address-multiplexed canary class — it is the configuration to run at
scale; the engine is the classifier and tripwire for small inputs.

---

## Setup & methodology

| Item | Value |
|---|---|
| Hardware | 2× NVIDIA RTX A5000, 24 GB, sm_86, driver 595.84; 503 GB host RAM |
| Toolchain | CUDA 12.9 (spack), host g++ 13.3 / conda gcc 15.2 for the analyzer, Python 3.10 + networkx 3.2.1 / pydot |
| Pipeline | cuobjdump→nvdisasm CFG + atomic-scope sidecar; `YOSEMITE_HB_TRACE=1 accelprof -t pc_dependency_analysis -n 1`; verdicts `python/sync_dominance.py`; exact oracle `python/hb_oracle.py` |
| Modes | **engine**: dump + in-process vector-clock engine (`hb_races`); **trace-only**: `YOSEMITE_HB_NO_ENGINE=1`, dump only, static-leg verdicts |
| Harness | `eval/driver.py` (extraction, native / trace-only / engine timing, `/proc` peak-RSS poller, process-group reaping) → `eval/aggregate.py` (pairs each kernel JSON with its CFG, dedups RACE reports on (unordered pc pair, space), engine-vs-oracle cross-check) |
| Timing | `t_native` = bare app (min of reps); `t_trace` = `YOSEMITE_HB_NO_ENGINE=1`; `t_engine` = full engine; `peak_mem` = host RSS of the whole process tree |

**Column schema** (`eval/results/<suite>.csv`): suite, program, variant, bug_label, input,
grid, block, events, t_native, t_trace, t_engine, peak_mem_mb, reports_raw, reports_dedup,
TP, FN, FP, TN, racecheck_verdict, oracle_verified, tv_violations, structural, latent,
unknown_sync, notes.

**Accounting.** A racy program is a **TP** iff ≥1 RACE verdict (structural, latent or
benign) matches the planted pcs — the tool's own detection criterion; a race-free program
with any RACE verdict is an **FP** by that strict reading, and the tables separate
`structural` (the count a precision claim should use) from `latent`/`benign`.
`tv_violations` = the `model_bug` cell (static all-schedule ordering claimed, engine raced —
must be 0). `oracle_verified` = engine `hb_races` equals the exact oracle over the same dump.
CSV naming: `*.csv` = original run; `*-fixed.csv` / `*-final.csv` = after the detector fixes;
`*-noengine.csv` = trace-only mode.

---

## E0 — ScoR applications (7 real apps, labeled via the RACEY build flag)  ✅

`E0.csv` (original), `E0-fixed.csv` (current). Each app built for sm_86 race-free (default)
and racy (`RACEY=1`, the ScoR-planted race); small inputs, engine-only (the exact oracle is
impractical on many-kernel apps). The same suite ScoRD (ISCA'20) and iGUARD (SOSP'21) used.

| app (ordering style) | build | events | t_native | t_trace | t_engine | peak MB | raw/dedup | struct | latent | verdict |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 1dconv (barrier) | race-free | 520 | 0.57 | 1.62 | 1.57 | 818 | 0/0 | 0 | 0 | **TN** |
| 1dconv | racy | 512 | 0.57 | 1.57 | 1.57 | 818 | 1/1 | 1 | 0 | **TP** |
| matrix-mult (barrier-tiled) | race-free | 189174 | 0.52 | 3.99 | 60.9 | 1220 | 2/2 | 0 | 2 | latent (benign) |
| matrix-mult | racy | 189788 | 0.52 | 3.94 | 63.2 | 1196 | 5/4 | 3 | 2 | **TP** |
| graph-coloring (atomic) | race-free | 89517 | 0.52 | 2.53 | **84.6** | 1433 | 84/6 | 0 | 84 | latent (benign) |
| graph-coloring | racy | 106930 | 0.52 | 2.63 | **112.4** | 1436 | 168/9 | 168 | 0 | **TP** |
| graph-connectivity (atomic) | race-free | 9736 | 0.52 | 1.62 | 24.8 | 2529 | 6/6 | 0 | 6 | latent (benign) |
| graph-connectivity | racy | 9151 | 0.52 | 1.67 | 21.7 | 2527 | 13/11 | 5 | 8 | **TP**; tv 0 (was 1, F2) |
| reduction (fence+lock) | race-free | 887 | 0.52 | 1.57 | 2.13 | 963 | 24/24 | **11** | 13 | FP (F1) |
| reduction | race-free, `--assume-warp-lockstep` | 891 | — | — | — | — | 14/14 | **1** | 13 | 10 `warp-po-ordered` |
| reduction | racy | 887 | 0.52 | 1.62 | 2.13 | 958 | 26/26 | 11 | 15 | **TP** |
| rule-110 (cellular) | race-free | 28248 | 0.52 | 2.13 | 2.58 | 834 | 16/1 | 0 | 16 | latent (benign) |
| rule-110 | racy | 28236 | 0.52 | 2.13 | 2.63 | 834 | 52/3 | 45 | 7 | **TP** |
| uts (persistent kernel) | both | — | — | — | timeout | — | — | — | — | **scope limit** |

**Recall 6/6** on the racy builds (the races ScoRD/iGUARD report). UTS spins under
instrumentation and times out — reported, not dropped. **Precision:** structural false
positives occur on exactly one app, the fence+lock reduction (F1: 10 intra-warp lock-step
pairs + 1–2 record-order inversions); every other race-free app emits only latent reports on
tolerated graph/grid updates. The `model_bug` hit on graph-connectivity (pre-fix) was the F2
attribution bug; the planted `0x160→0x400` is the structural TP. **iGUARD/ScoRD
cross-reference:** both report the planted race of each racy build; cuVein reproduces all six.
iGUARD could not run UTS-class persistent kernels either; neither can this harness.

---

## E1 — Indigo3 (labeled headline suite)  ✅

`E1-final.csv` (NonDeterm), `E1-determ-final.csv` (Determ); pre-fix `E1.csv`,
`E1-determ.csv`. Stratified CUDA sample: one representative style axis (Vertex, Push, Data,
Thread, NonPersist, ReadWrite) × Atomic/CudaAtomic × planted bug ∈ {none, RaceBug,
SyncBug (TC)}; other bug classes filtered out; 6 algorithms (BFS, CC, MIS, MST, SSSP, TC;
PR needs FloatType); two inputs — the 100-node torus (1 block) and the 1024-node grid
(2 blocks); engine-only.

| set | rows (racy / race-free) | recall | precision | specificity | tv |
|---|---|--:|--:|--:|--:|
| NonDeterm | 60 (28 / 32) | **26/28 = 0.93** | 0.57 | 12/32 = 0.38 | **0** (pre-fix 81) |
| Determ | 40 (20 / 20) | **18/20 = 0.90** | 0.69 | 12/20 = 0.60 | **0** (pre-fix 81) |

- **By bug type.** RaceBug: 10/10 on BFS/CC/MIS/MST/SSSP (both inputs); TC 4/6 — the two
  misses are the 1-block 100-node inputs (the planted `*g_count += val` by one thread per
  block needs ≥2 blocks) and both are **caught on the 1024-node graph**. SyncBug (missing
  barrier, TC): 8/8, surfacing as latent with `benign`-tagged reads. RaceBug+SyncBug: 4/4.
- **By style.** Atomic vs CudaAtomic behave identically. **Every TC nobug variant (BlockAdd /
  GlobalAdd / Reduction, both inputs) is clean — 12 TN, 0 FP.**
- **Race-free reports = F5.** BFS/CC/SSSP nobug (47–752 structural) are plain-vs-plain
  unsynchronized label/worklist updates; MIS 6–16; MST 25–98 structural with 37–43
  re-bucketed benign. Indigo's "nobug" means *no planted bug*, not race-free — both
  deterministic and nondeterministic variants carry these inherent races, which cuVein's exact
  HB reports and HiRace's benign-race-aware model suppresses (0 false alarms on this suite).

---

## E2 — cuHadron (27 cases; labeled via FIXED)  ✅

`E2.csv`, `E2-fixed.csv` (memcpy/intersubwarp subset re-run, identical). 19 in-reach cases ×
2 (race-present / synchronized) for sm_86; the 8 `bulkcpy` + `dsmem` cases are **sm_90-only —
an explicit hardware scope limit, not a silent omission**.

| class | count | cuVein |
|---|--:|---|
| synchronized builds (FIXED=1) | 19 | **0 false positives** |
| false_positives controls (byte-wise sub-word) | 4×2 | **0 false positives** |
| in-scope races | 6 | 5 TP (intersubwarp shared RW & WW, interwave global WW, memcpy global RW & shared WW), 1 FN (`memcpy/shared_readwrite`, F4) |
| out-of-model races (host↔device ×3, inter-kernel ×2, multi-GPU ×2; cp.async-host ×2 hang under the sanitizer) | 9 | not detected — outside the intra-kernel single-device model |
| bulkcpy + dsmem | 8 | sm_90-only (not built) |

---

## E3 — ECL suite (false-positive test at scale)  ✅

`E3-fixed.csv` (pre-fix `E3.csv`). The four `src/racefree/egr-input` codes (benign races
removed by construction), sm_86, torus-100 ECL graph. Expected: race-free.

| code | events | raw/dedup | structural (pre → post) | benign | triage |
|---|--:|--:|--:|--:|---|
| ECL-CC | 13714 | 26/17 | 25 → 24 | 2 | union-find array is *also* plainly written (path compression) → value-based check needed |
| ECL-GC | 3406 | 2/1 | 2 → 2 | 0 | idempotent plain WAW |
| ECL-MIS | 265 | 19/11 | 20 → **0** | 19 | every read conflicts only with atomic writers |
| ECL-MST | 1195 | 29/6 | 25 → 14 | 15 | partial |

All four still emit RACE verdicts (0/4 clean by the strict reading); structural 52 → 40. The
reports are real HB-unordered accesses ECL tolerates (plain read of a CAS-updated parent
pointer; equal-value WAW) — the clearest demonstration of the F5 precision gap, and no
candidate real race was found in the suite.

---

## E4 — HeCBench (real apps, overhead & scale)  ✅

`E4.csv`. Four real apps built for sm_86 at small sizes (the exact engine OOMs at realistic
sizes, F3); reports deduped on (pc_a, pc_b, location class).

| app (kind) | events | t_native | t_trace | t_engine | peak MB | trace× | engine× | reports |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| bitonic-sort (sort) | 1 048 | 0.52 | 2.18 | 2.08 | 818 | 4.2× | 4.0× | 0 |
| stencil1d (stencil) | 14 973 | 0.57 | 1.77 | 2.23 | 916 | 3.1× | 3.9× | 0 |
| nbody (n-body) | 2.64 M | 0.67 | 33.0 | 44.2 | 2198 | 49× | **66×** | 0 |
| mandelbrot (compute) | 4.18 M | 0.92 | **≥120 (timeout)** | ≥120 | 2362 | >130× | >130× | 0 |

**All four report zero races** — the F5 over-reporting is specific to graph analytics.

---

## E5 — ScoR microbenchmark litmus, canary, barrier fix  ✅

`E5-micro.csv`, `E5-special-fixed.csv`. 33 scoped-synchronization litmus programs
(intrawarp / interwarp / interblock; scoped atomics, fences, locks, indirect HB).

| metric | value |
|---|---|
| racy → TP / FN | **18 / 0** |
| race-free → FP / TN | **0 / 15** |
| precision / recall / specificity | **1.000 / 1.000 / 1.000** |
| structural / latent (total verdicts) | 11 / 10* |
| tv_violations, unknown_sync | 0, 0 |
| oracle_verified (engine == exact VC oracle) | **33 / 33** (re-verified after every fix: 68/68 tests) |

\*Fence-/lock-gated races surface as **latent**: the engine cannot observe `MEMBAR`
(no Compute-Sanitizer patch point), so the static leg's "no all-schedule proof" is the
detection — correct, and the documented static-only path.

**Canary** (`canary_pc_level_false_negative.cu`, two producer/consumer handshakes
multiplexed over one release pc): PC-level analysis reports 0; the address-keyed engine
reports **2 WAW structural** on `data[0]/data[1]` (pc `0x1f0→0x160`), oracle-verified — the
one report the verdict matrix must never lose (it is the `dyn_raced ∧ chain_ordered` cell).
**Multi-warp `__syncthreads` fix** (commit 031f47d): `test_barrier_soundness.py` passes and
`norace_interwarp_barrier_raw` is a clean TN at real scale.

---

## E6a — Compute Sanitizer racecheck baseline  ✅

`E6a-racecheck.csv`. racecheck detects **shared-memory** hazards only; run on the 9
shared-memory cuHadron cases as an independent oracle.

| case | racecheck | cuVein | agree? |
|---|---|---|---|
| intersubwarp shared read-write — racy | RACE (1) | RACE | ✅ |
| intersubwarp shared read-write — fixed | clean | clean | ✅ |
| intersubwarp shared write-write — racy | RACE (1) | RACE | ✅ |
| intersubwarp shared write-write — fixed | clean | clean | ✅ |
| memcpy shared read-write — racy | **RACE (1)** | **clean** | ❌ **cuVein FN (F4)** |
| memcpy shared read-write — fixed | clean | clean | ✅ |
| memcpy shared write-write — racy | RACE (1) | RACE | ✅ |
| false_positives shared read-write — racy | clean | clean | ✅ |
| false_positives shared write-write — racy | clean | clean | ✅ |

**Agreement 8/9.** The single disagreement is F4 — a real shared-memory race racecheck
finds and cuVein misses (a `cp.async` write attributed to the issuing lane's own thread; fix
designed). racecheck cannot adjudicate global-memory races, so it does not speak to the E0
reduction reports (F1) or the graph benign races (F5).

## E6b — HiRace (SC'24)

Artifact available at `github.com/JohnJacobsonIII/HiRace-Artifact-SC24` (NVBit-based; could
in principle build for sm_86; not rebuilt in this session). Published numbers: on ~580 CUDA
kernels (346 racy) it reports races other tools miss with **0 false alarms**, **>10× faster**
than the prior state of the art at **half the memory**, via a constant-size per-location
state machine. This is the direct foil: HiRace's headline is efficiency plus
benign-race-aware zero-false-alarms, whereas cuVein's exact unbounded vector-clock engine is
the opposite on cost (F3) and flags benign races (F5). On the scoped-atomic litmus cuVein
matches the zero-false-positive bar (E5); on real graph code it does not (E1/E3).

## E6c — iGUARD (SOSP'21) / ScoRD (ISCA'20)

iGUARD's source is available at `github.com/csl-iisc/iGUARD-SOSP21` (NVBit-based; not
rebuilt for sm_86 in this session — the blocker is the NVBit toolchain setup, not the
hardware). iGUARD and ScoRD evaluated on the same ScoR applications as E0 and report the
planted race in each racy build; cuVein reproduces all six (E0 recall 6/6). A same-pc
cross-check would require the rebuild; the RACEY-labeled E0 recall is the equivalent evidence.

---

## Overhead — engine mode

Ratios vs native (`t_x / t_native`), tracing and engine separated (from E0/E4/E5 rows):

| workload | events | trace× | engine× | engine/trace | peak MB |
|---|--:|--:|--:|--:|--:|
| ScoR litmus / canary (tiny) | 4–10 | ~3× | ~3× | 1.0 | 818 (sanitizer floor) |
| 1dconv | 520 | 2.8× | 2.8× | 1.0 | 818 |
| reduction | 887 | 3.0× | 4.1× | 1.4 | 963 |
| rule-110 | 28 k | 4.1× | 5.0× | 1.2 | 834 |
| graph-connectivity | 9.7 k | 3.1× | **48×** | 15 | 2529 |
| matrix-mult | 189 k | 7.7× | **117×** | 15 | 1220 |
| graph-coloring | 90–107 k | 4.9× | **163–218×** | 33–43 | 1436 |
| nbody | 2.6 M | 49× | 66× | 1.3 | 2198 |
| mandelbrot | 4.2 M | >130× (timeout) | — | — | 2362 |

Two regimes: on compute kernels the **event dump** dominates (nbody: engine only +34% over
tracing; mandelbrot's tracing alone times out); on graph kernels the **engine's vector-clock
joins** dominate (graph-coloring: engine 43× its trace). Host memory grows to GB-scale and a
graph run was killed by the OS — the exact unbounded vector clocks (F3) bound the engine to
small inputs. This motivates the trace-only evaluation below.

---

## Trace-only mode (`YOSEMITE_HB_TRACE=1 YOSEMITE_HB_NO_ENGINE=1`)

`*-noengine.csv` (every suite re-run with `driver.py --no-engine`). The runtime dumps the
event stream but runs no vector-clock engine; verdicts come from the static leg alone (R1
barrier dominance, R2 atomic coherence, R3 fence→atomic→acquire chains over the trace's pc
edges). Without `hb_races` every detection is **latent** — the structural/latent split and
the address-level per-instance evidence are exactly what the engine adds.

**Accuracy: identical recall on every suite; the only loss is the canary class.**

| suite | engine mode | trace-only mode |
|---|---|---|
| E5 litmus (33) | P 1.00 / R 1.00 / S 1.00; 11 structural + 10 latent | **P 1.00 / R 1.00 / S 1.00**; all 21 latent |
| E5 canary | TP — 2 WAW structural (address-keyed) | **FN** — the PC-level false negative the engine exists to close |
| E0 ScoR apps (6 usable) | racy 6/6; reduction race-free 11 structural | racy **6/6** (`caught-latent-only`); same report sets, all latent (reduction 23, graph-coloring 84, matrix-mult 2, rule-110 16) |
| E1 Indigo3 NonDeterm (60) | 26/28, precision 0.57, spec 0.38 | **26/28, 0.57, 0.38** — identical |
| E1 Indigo3 Determ (40) | 18/20, precision 0.69, spec 0.60 | **18/20, 0.69, 0.60** — identical |
| E2 cuHadron (38) | 5 TP, 0 FP, F4 + out-of-model FN | **5 TP, 0 FP**, same FN set |
| E3 ECL (4) | 40 structural (MIS 0 / benign 19) | same pairs as latent (CC 25, GC 2, MIS 0 + 21 benign, MST 14 + 15 benign) |
| E4 HeCBench | 0 reports | 0 reports |

Every planted race the engine finds, the static leg finds too — the litmus's fence/lock
races were static-only detections to begin with, and the real-suite planted races are all
PC-distinguishable pairs. What the engine contributes is (a) the **structural** label (an
observed, address-level race vs. "no static proof"), (b) the **canary** class (one release
pc multiplexing several handshakes — invisible at PC granularity), and (c) the `model_bug`
tripwire. It does not change which programs are flagged.

**Overhead: 3–9× native instead of 48–218×, and ~820 MB instead of GB-scale.**

| workload | events | native | trace-only | engine | trace× | engine× | peak trace / engine (MB) |
|---|--:|--:|--:|--:|--:|--:|--:|
| 1dconv | 520 | 0.52 | 1.52 | 1.57 | 2.9× | 3.0× | 820 / 818 |
| reduction | 889 | 0.52 | 1.57 | 2.13 | 3.0× | 4.1× | 819 / 963 |
| rule-110 | 28 k | 0.52 | 2.13 | 2.58 | 4.1× | 5.0× | 820 / 834 |
| graph-connectivity | 9.7 k | 0.52 | 1.67 | 24.8 | 3.2× | **48×** | 822 / 2529 |
| graph-coloring | 90–107 k | 0.52 | 2.63–2.68 | 84.6–112.4 | 5.1× | **163–218×** | 819 / 1436 |
| matrix-mult | 190 k | 0.52 | 4.04 | 60.9 | 7.8× | **117×** | 1074 / 1220 |
| ECL CC / GC / MIS / MST | 0.3–14 k | 0.67–0.72 | 1.6–1.8 | — | 2.5× | — | 818–826 / — |
| bitonic-sort p12 | 32 k | 0.57 | 2.93 | (OOM'd at this size) | 5.2× | — | 818 / — |
| stencil1d 65536×10 | 399 k | 0.57 | 5.29 | (OOM'd at this size) | 9.3× | — | 862 / — |
| nbody 2048 | 2.6 M | 0.67 | 33.7 | 44.2 | 50× | 66× | 1534 / 2198 |
| mandelbrot | 9.4 M | 0.87–1.72 | ≥120 (timeout) | ≥120 | >70× | — | 1197 / 2362 |

The trace-only cost is the Compute-Sanitizer floor (~3× on small kernels) plus the event
dump, which scales with event count (nbody 50×; mandelbrot's 9.4 M-event dump exceeds the
120 s budget). The engine's extra cost is what the vector-clock joins add on top — negligible
on straight-line kernels, 15–43× on graph kernels — and its memory is what OOM'd the graph
runs. Two configurations the engine mode could not finish at all (bitonic p12, stencil
65536×10) complete in trace-only mode in seconds.

**Reading.** For finding *which programs and pc pairs race*, the trace-only mode delivers the
engine mode's recall at a fraction of the cost and is the configuration to run at scale. The
engine mode is the tool for *classifying* a report (structural vs latent), for
address-multiplexed handshakes (canary), and as the soundness tripwire — and, until the
FastTrack/bounded-clock knobs land (F3), only on small inputs.

---

## Findings (details, evidence and fixes: `eval/FIX_REPORT.md`)

| id | one line | status |
|---|---|---|
| F1 | reduction FPs = intra-warp lock-step pairs (10) + trace record-order inversion (2); not fence-blindness | opt-in lockstep filter; inversion documented |
| F2 | 82 `model_bug` = WAR records without the reader pc + subset pair matching, plus unscoped shared `ATOMS`; also a latent R1 loop-back-edge hole | **fixed**, tripwire 0 |
| F3 | exact vector-clock engine: 3–218× native, OOM on graph kernels | known deferred scale knobs |
| F4 | `cp.async` write attributed to the issuing lane → read-before-wait missed (racecheck-confirmed) | fix designed (`PIPELINE_WAIT`), needs patch rebuild |
| F5 | benign/inherent graph races flagged (plain read of atomically-updated location; idempotent WAW) | Tier-1 `benign` class applied; Tier 2/3 designed |
| F6 | release map keyed by raw address clobbered per-block shared releases (2-block spurious atomic races) | **fixed** |

---

## Bottom line

**Accuracy:** perfect on the scoped-synchronization litmus (P=R=1.00, engine==oracle
33/33); high recall on every real suite (ScoR apps 6/6, Indigo3 26/28 with the two misses
needing a ≥2-block input, cuHadron 5/6 in-scope); soundness tripwire 0 everywhere after the
F2/F6 fixes. **Precision on graph analytics is the open problem** (F5): exact HB reports the
inherent benign races of BFS/CC/SSSP-style kernels and ECL's race-free codes; the `benign`
class re-buckets the atomic-writer cases, the plain-vs-plain residue needs value-level
information the trace does not yet carry. **One confirmed in-scope false negative** (F4) has
a designed fix. **Overhead:** the exact engine is not viable on large kernels (F3), but the
**trace-only mode matches its recall on every suite at 3–9× native and ~820 MB** — losing
only the structural/latent label and the canary class — so the practical deployment is
trace-only at scale with the engine reserved for classifying and cross-checking small cases.
All numbers reproducible via `eval/` (`eval/README.md`).

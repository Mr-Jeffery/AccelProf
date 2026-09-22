# Why cuVein reports so many false positives — diagnosis

_Branch `harden/trace-validity-and-scale`, data from the head-to-head run in `eval/BASELINES.md`
(`eval/results/baselines-cuvein.csv`, `eval/baselines/confirm/`, `eval/baselines/traces_keep/`).
Reproduce the attribution with `python3 eval/baselines/classify_fp_causes.py`
(→ `eval/results/baselines-fp-causes.csv`, one row per false-positive report). No GPU needed._

## The numbers being explained

Race-free programs reported RACE (engine mode; trace-only is the same or worse):

| pset | FP / race-free | note |
|---|---|---|
| P1 Indigo3 BFS | 72 / 199 | |
| P2 Indigo (orig) | 6 / 30 | |
| P3 Indigo3 CC (race-free) | 41 / 57 | |
| P4 ScoR apps | 7 / 9 | |
| P5 ScoR litmus, P6 cuHadron | 0 | |

`eval/REPORT.md` (F5) attributed these to "benign races inherent to graph analytics". That is
mostly wrong: only RC4 below is of that kind.

## Method

Every RACE report of a race-free program was mapped to the SASS opcodes of its two pcs (CFG dots
kept next to the trace) and each endpoint typed as `atom` (ATOM/ATOMG/ATOMS/RED), `seq`
(`MEMBAR; ERRBAR; CCTL.*; LD|ST.*.STRONG.*`), `strong` (unfenced `LD|ST.*.STRONG.*`) or `plain`;
for engine dumps the report was also checked against the engine's exact `hb_races` pairs.

Program-level result (`classify_fp_causes.py`, engine mode):

| pset | programs | set of causes |
|---|---|---|
| P1 | 72 | RC1 |
| P2 | 6 | RC2 |
| P3 | 27 | RC1 |
| P3 | 8 | RC1 + RC3 + RC4 |
| P3 | 7 | RC3 + RC4 |
| P4 | 4 | RC2 |
| P4 | 2 | RC2 + RC5 |
| P4 | 3 | RC5 |

## RC1 — `cuda::atomic` load/store is invisible to the atomic model (P1 72/72, P3 35/42)

- `sync_dominance.atomic_scope()` recognises only the RMW opcode families
  `ATOM/ATOMG/ATOMS/RED`; `atomic_scope_sidecar.py` reuses it, so the C++ engine has the same
  blind spot.
- `cuda::atomic<T>::load()/store()` do not lower to those opcodes. seq_cst:
  `MEMBAR.SC.SYS; ERRBAR; CCTL.IVALL; LD|ST.E.STRONG.SYS`. `memory_order_relaxed`: bare
  `LD|ST.E.STRONG.SYS`. Both R2 (static coherence) and the engine treat them as plain accesses, so
  any cross-thread pair on them is a race.
- Indigo3's labelling convention is exactly this distinction: a `nobug` program and its `RaceBug`
  twin differ only in `typedef cuda::atomic<int> data_type` vs `typedef int data_type`
  (`LD.E.STRONG.SYS`/`ST.E.STRONG.SYS` vs `LDG.E`/`STG.E`). cuVein reports the same pc pairs on
  both, so its ~100 % recall on P1 is not detection skill.
- Evidence: all 126 P1 FP reports have both endpoints in {`LD/ST.E.STRONG.SYS`, `ATOM*.MIN`,
  `RED.MIN`}; none is plain-vs-plain. The build pattern matches: `Atomic` style is FP only in the
  default build (`atomicRead/Write` = relaxed load/store; 12 programs × 2 inputs = 24 rows) and
  clean under `-DSLOWER_ATOMIC` (`atomicAdd(x,0)`/`atomicExch` are real ATOM ops); `CudaAtomic`
  style is FP in both builds (12 × 4 = 48 rows).
- Complication: ScoR encodes racy shared data as `volatile`, which lowers to
  `LDG/STG.E.STRONG.SYS` — the same qualifier, and `__threadfence(); volatile store` is the same
  `MEMBAR; ERRBAR; CCTL.IVALL` idiom. A blanket "STRONG ld/st is atomic" rule drops ScoR litmus
  recall from 17/18 to 2/18 (offline what-if). The only binary-level difference is the opcode
  form: generic `LD/ST` from the cuda::atomic builtins (all 686 strong operands in P1/P3 FP
  reports) vs `LDG/STG` from volatile pointers (all 216 in P4); no overlap in the corpus. It is a
  toolchain-lowering fact, not semantics, hence a policy knob (`--strong-ldst`, default `generic`)
  pinned by litmus tests.
- iGUARD, also binary-level and ScoR-derived, shows the same behaviour and worse
  (100/200, 30/30, 48/60).

## RC2 — `latent` counts as RACE, and PC-level rules cannot prove barrier idioms (P2 6/6, P4 6/9, P7 srad)

- These reports are all `latent`: the engine observed no race (`hb_races: []`), R1/R2/R3 have no
  all-schedule proof, and the harness calls the program RACE.
- Shared-memory tree reduction (`conditional_edge_neighbors_block*`, srad `reduce_kernel.cu`):
  `for (stride…) { if (tid < stride) s[tid] = max(s[tid], s[tid+stride]); __syncthreads(); }`.
  The read and the write share one sync region, so `dominance()` returns NONE (`ru == rv`);
  same-iteration instances are index-disjoint, cross-iteration ones are barrier-separated.
- ScoR work-distribution prelude (`if (tid==0) *base = …; __syncthreads(); my_base = *base;`
  inside a `while`): the in-loop barrier does not post-dominate the pre-loop read.
- `latent` was designed for fence-omission races, where the engine's ordering comes from atomic
  release/acquire joins that ignore fences. Barrier/syncwarp joins are schedule-independent, so a
  pair ordered by them alone is not a "lucky schedule". What-if with barrier-only clocks:
  graph-connectivity → no raced pair in any kernel; rule-110 → 1023 raced instances per pair
  (its ordering really is the atomic handshake, so it correctly stays latent).

## RC3 — this branch lacks the detector fixes described in `eval/FIX_REPORT.md`

They exist only on `origin/worktree-eval-suite` (`112a99f`, `f0daa01`); the branches diverged at
`871c466`. Visible here: WAR records with `a_pc: null`; `hb_pair_raced` does subset matching, so
a same-pc race `{pc}` marks every pair containing that pc as raced — barrier/syncwarp-ordered
pairs become `structural` and P3 shows 12 `model_bug` tripwire hits although the engine raced only
the same-pc pair (28 such reports in 15 programs). Also missing: `released` keyed by location
(F6), bare `ATOMS` → BLOCK, the R1 loop back-edge check. Inflates and mislabels reports; it rarely
flips a program verdict on its own.

## RC4 — same-value idempotent writes (P3 15 programs)

`__shared__ bool updated = true` written by many threads between two barriers/syncwarps (CC Pull
Block/Warp variants); Rodinia bfs `*over = true`. Genuinely HB-unordered, benign by design;
needs written values in the trace (FIX_REPORT F5 Tier 3). Not addressed here.

## RC5 — ScoR volatile handshakes (reduction ×2, rule-110 ×2, matrix-mult)

FIX_REPORT F1: intra-warp lock-step pairs plus pre-op record-order inversion, and lock/fence
handoffs the R3 chain cannot certify. Unchanged.

## Hazards found on the way

- The atomic-scope sidecar is `pc → scope` merged across kernels; pcs are function-relative.
  149/183 kept programs are multi-kernel; in 14 a plain `LDG/STG` collides with an `ATOMG` offset
  of another kernel, so the engine treats that plain access as atomic.
- The engine's atomic branch checks `last_write` only, never `last_reads`: "plain read, then
  atomic write" is missed while "atomic write, then plain read" is flagged, so the same pair
  flips between structural and latent with event order.
- `bin/accelprof` exits 127 on every run (elapsed-time `printf`), so `rc` cannot signal a
  collector failure. `pc_lines` in `meta.json` merges function-relative offsets across functions.

## Fixes applied and measured effect

1. **RC3** — ported the `112a99f`/`f0daa01` detector changes (exact pc-pair matching with reader pcs in
   WAR records, `released` keyed by location, bare `ATOMS` → BLOCK, R1 sync-free-path check, `benign`
   and `warp-po-ordered` classes). Old dumps with `a_pc: null` still match on the writer pc.
2. **RC1** — `sync_dominance.coherent_scope()`: RMW atomics plus, per `--strong-ldst`
   (`generic` default | `all` | `none`, env `CUVEIN_STRONG_LDST`), `.STRONG` loads/stores. Used for
   pairwise same-address coherence only (R2 and the engine/oracle conflict check); a coherent
   load/store joins no clocks and is not an R3 atomic, so the Phase-2 relaxed-atomic unsoundness is
   not widened. The engine's RMW branch now also checks prior readers.
3. **RC2** — engine + oracle keep a second, barrier/syncwarp-only clock and emit
   `hb_races_sync_only`; a pair that did not race, has no static proof and is absent from that set
   is `barrier-ordered` (ORDERED); pairs ordered only through atomic handoffs stay `latent`. With
   `YOSEMITE_HB_NO_ENGINE` the engine emits no race keys at all (an empty list would read as
   "everything is barrier-ordered").
3b. **RC2 in trace-only mode** — the barrier-only clock needs no atomic joins, so
   `sync_dominance.barrier_only_pairs()` derives the same set offline from the dump's `hb_events`
   (shared-base clock, O(threads) per barrier; identical to the oracle's second clock on every
   corpus kernel). A trace-only pair without a static proof is ORDERED (`barrier-ordered`) iff
   barrier/syncwarp joins order every observed conflict; anything they leave unordered stays RACE,
   so fence/lock/atomic-omission races are untouched. `CUVEIN_BARRIER_PASS=0` disables it, dumps
   above `CUVEIN_BARRIER_PASS_MAX_LANES` (5 M) stay static-only. Also used for engine dumps that
   predate `hb_races_sync_only`.
3c. **Edge rescue** — a dependency edge remembers only the LAST accessor of a location, so a
   single-instance conflict is recorded at intra-thread distance when the last reader happened
   to be the writer's own thread, and was skipped (`conditional_edge_neighbor_cond_guardBug`:
   RACE in 3/3 baseline trace-only reps, CLEAN in 6/6 after the collector timing shifted). The
   event stream keeps every reader: a pair it shows as a cross-thread unordered conflict (engine
   race record, or the offline pass) is now analysed at that thread distance instead of being
   skipped (`edge_rescued`).
4. Sidecar keyed by kernel (`<pc> <scope> <kind> <kernel>`, every kernel declared), selected at
   kernel launch.
5. `bin/accelprof` exit status fixed; `make_tables.py` renders the class/cause split.

Tests: `python/test_coherent_ldst.py` + `testdata/coherent_ldst.cu` (cuda::atomic seq_cst/relaxed
and RMW-vs-load → no race; atomic load vs plain store and a volatile pair → race; barrier-in-loop
reduction → `barrier-ordered`, its barrier-less twin → race; pins the LD/ST vs LDG/STG lowering;
engine == oracle on `hb_races` and `hb_races_sync_only`). Corpus: 88 passed, 1 xfailed (Phase 2),
1 failed — `race_interblock_none-lock_rtraw`, a schedule-dependent miss whose output is
byte-identical to the 2026-09-10 artifacts (already an FN in BASELINES).

Post-fix re-runs of P1–P6 (615 programs) with the final code: engine mode `setup/p_fpfix_eng.sh`
→ `eval/results/fpfix/`, `confirm_fpfix/`, `traces_keep_fpfix/`; trace-only `setup/p_fpfix_tr.sh` →
`eval/results/fpfix_tr/`, `confirm_fpfix_tr/`, `traces_keep_fpfix_tr/`. Table from
`compare_fpfix.py --after-glob 'eval/results/fpfix*/baselines-cuvein-shardfpfix*.csv'`
(an earlier engine+trace-only run from before the edge rescue is in `eval/results/superseded_pre_rescue/`):

| pset | mode | FP before | FP after | TP before | TP after |
|---|---|---|---|---|---|
| P1 | engine | 72/199 | **0/199** | 185/185 | 178/178 |
| P1 | trace-only | 72/200 | **0/200** | 200/200 | 200/200 |
| P2 | engine | 6/30 | **0/30** | 23/30 | 25/30 |
| P2 | trace-only | 6/30 | **0/30** | 25/30 | 25/30 |
| P3 | engine | 41/57 | **14/58** | — | — |
| P3 | trace-only | 44/60 | **16/60** | — | — |
| P4 | engine | 7/9 | 5/9 | 9/9 | 9/9 |
| P4 | trace-only | 10/14 | 6/14 | 14/14 | 14/14 |
| P5 | engine | 0/14 | 0/14 | 18/19 | 18/19 |
| P5 | trace-only | 0/14 | 0/14 | 17/19 | 17/19 |
| P6 | engine | 0/19 | 0/18 | 5/11 | 5/10 |
| P6 | trace-only | 0/20 | 0/19 | 5/12 | 5/11 |

- **No true positive lost and no new false positive in either mode.**
- Residual FPs are exactly the two classes left out of scope. P3 (14 engine / 16 trace-only): every
  program carries ONE report, the same-pc `STS` write-write `updated = true` (RC4) — really
  unordered, benign by value. P4 (5 / 6): ScoR volatile handshakes — reduction, rule-110,
  matrix-mult (RC5/F1). In trace-only the P4 graph-coloring/-connectivity programs and all six P2
  block reductions are now clean through the offline barrier pass.
- P2 engine TP 23 → 25: the RMW-vs-readers check catches plain-read-then-atomic-write pairs the
  engine used to miss.
- Engine ERROR/TIMEOUT: P1 16 → 23, P6 4 → 6 (P3 3 → 2). Every program involved sat at the 120 s
  cap already (baseline: TIMEOUT in ~25 of 30 reps, a verdict only in a rep at 113–119 s, or only
  under the separate 20-minute budget; the P6 interkernel pair also times out in trace-only, where
  no engine runs). The P1 TP denominator drops 185 → 178 for that reason, not through misses. The
  sync-only clock is O(threads) per barrier; the exact main clock remains the scaling wall (F3).
- Trace-only collector wall time is unchanged (medians within noise); the offline pass runs in
  the analysis step.

## Addendum (2026-09-20) — the engine "FN" that was an OOM-killed partial run

In the Sep 18 re-run `P1-CC_CUDA_V_Data_Push_…_RaceBug_Block_…-slower_atomic-1296n` scored
engine CLEAN ×1 / TIMEOUT ×2 but trace-only RACE ×3, all rows saying `events=83`. It looks like
the two modes disagree on one trace. They never saw the same trace:

- The CLEAN rep is `rc=1`, 111 s, 113.8 GB peak — the only `CLEAN` row with `rc≠0` in the merged
  CSV. Every other `rc=1` row carries `accelprof: … Killed … Fail to run the application`: the
  app was OOM-killed under the engine.
- Engine reps dumped `nkernels=1` (0.1 MB); trace-only reps `nkernels=5` (381 MB). The one kernel
  is `init`, which has exactly 83 `hb_events`; the racy `cc_vertex_data` kernels never finished.
- `events=` was the *engine* dump's count (`meta["events"]`) printed on the rows of both modes.

The harness scored any non-timed-out rep with ≥1 kernel JSON as a complete run. Fixed:
`parallel.py` records `complete = not timed_out and rc == native_rc` per rep, prefers a complete
rep's dump, flags a partial one, and an incomplete rep is `ERROR incomplete-trace(rc;nkernels;
peak_mb)` — or RACE `partial` if the prefix already shows a race — never CLEAN. Rows now carry
their own mode's `events=` and `nkernels=`. `run_cuvein.py` applies the same rule, and
`make_tables.py` / `compare_fpfix.py` re-score old rows (`CLEAN` with `rc ∉ {0,127}` → ERROR;
127 = the pre-fix `bin/accelprof` exit after a successful run). Effect on the merged tables:
exactly this program, engine CLEAN → TO; P1 engine TP 182/183 → 182/182 with 19 TO/ERR.

Live check after the fix (job 284845, node c37): engine rep 1 was OOM-killed again (rc=1, 70 GB,
stderr `Killed`) and is now `ERROR incomplete-trace(rc=1;nkernels=1;peak_mb=70133.6)`, reps 2–3
TIMEOUT; trace-only RACE ×3 with its real size `events=451467;nkernels=5` (the engine prefix had
83). Four control programs (P1 TP/TN, P4 TP/TN) keep their verdicts in both modes.

Why the engine dies here (not fixed — deferred): `cc_vertex_data<<<wlsize=1296, 512>>>` is
663,552 threads, each through two `__syncthreads()` plus grid-scope atomics. `sync_group` hands
every participant a private full copy of the joined clock and every atomic release stores another
full copy, so state grows as threads × clock size (≥19 GB after the first barrier, 113–127 GB
observed; same before the FP fixes: 107–126 GB, TIMEOUT ×3). The sync-only clock already uses a
shared immutable base per sync group; doing the same for the main clock (shared bases + small
per-thread delta, pointer-copied into release records) is the planned fix for this and most of
the P1 engine timeouts in `baselines/setup/engine_timeout_ids.txt`.

## Addendum (2026-09-20) — `race_interblock_none-lock_rtraw`: a race with no dependency edge

ScoR micro `race_interblock_none-lock_rtraw` (block 0: `lock; read data; unlock; data[0] = 1`,
block 1: `lock; read data; unlock`) was missed in both modes — the one standing failure of
`test_scor_microbenchmark`. Two independent causes, both needed fixing:

1. **No candidate.** A dependency edge remembers only the LAST accessor of an address. The write
   (0x340) gets an intra-thread edge to block 0's own read (0x2c0); block 1's read (0x140) is already
   overwritten, and the only link between the reads is read-after-read. No edge names {0x140, 0x340}
   (the earlier "edge rescue" only upgrades an edge that exists). The event stream does show the pair:
   engine `hb_races_sync_only = [[0x140,0x340,1], …]`, and the offline barrier pass finds the same.
   → **Event-stream candidates**: every pc pair in `hb_races_sync_only ∪ hb_races` (engine) / the
   offline pass (trace-only) that no edge produced a verdict for is judged like an edge pair
   (distance, orientation and conflict count from the event stream; `event_candidate: true`). Their
   writers also enter the benign-read map, so a plain writer seen only in the events cannot be
   masked as `atomic-maintained-read`. Pairs that barriers alone order need no candidate
   (`barrier-ordered` anyway). Knob: `CUVEIN_EVENT_CANDIDATES=0`.
2. **R3 over-ordered it.** As a candidate the pair was still ORDERED: R3 accepted
   `read 0x140 → fence → release 0x1b0 → hop → CAS acquire 0x230 → po → 0x340`, because the acquire
   test was just `po(acquire, cur)` — true for anything after the CAS, including an access past the
   thread's own unlock (EXCH 0x330). Competing CAS acquires succeed in schedule-dependent order, so
   the hand-off orders only what is still INSIDE the critical section; had block 0 won the lock, its
   write would run concurrently with block 1's section. This is the static twin of the engine's
   schedule-dependent miss (`hb_races` empty on this schedule).
   → **Past-release gate** (`HBGraph._past_release`): when the acquire in force is a CAS, the chain is
   refused if an atomic observed on the same location (any atomic–atomic trace edge, intra-thread
   included: 0x330→0x230) lies between the acquire and `cur` in program order. Non-CAS flag/spin
   hand-offs keep the old rule (direction pinned by dataflow), the same convention `_cs_fenced` uses.
   Knob: `CUVEIN_R3_PAST_RELEASE=0`. Not covered: the mirror case (an access BEFORE its thread's own
   acquire) — no corpus instance.

Either change alone leaves the verdict unchanged (checked on all 32 ScoR micro programs and pinned
by `test_write_after_unlock_is_event_candidate`). With both: RACE in both modes, report
`global:0x140-0x340:WAR`, engine class `latent` (this schedule's hand-off ordered it; nothing
orders it in all schedules). A lockset/predictive engine check is not needed for this; a
FastTrack-style shadow in the collector (last writer + per-thread readers) remains the answer for
dumps taken without `hb_events`. The old E5 "caught-latent-only" entry for this program was one of
the lock-protected pairs, not this race.

Measured (2026-09-20, `setup/p_evcand.sh`, jobs 285124; 31 of 32 shards = 597 of 631 P1–P6
programs, both modes; compared with the merged baseline by
`compare_fpfix.py --manifest eval/baselines/setup/manifest.evcand.csv --after-glob 'eval/results/evcand/*.csv'`):
**0 true positives lost, 0 new false positives**; P5 TP engine 18/19 → 19/19 and trace-only
17/19 → 18/19 (rtraw; the remaining trace-only miss is the canary, engine-only by design); every
other cell unchanged (P1 0/187 FP, P2 0/28, P3 14/56 | 16/58, P4 5/9 | 6/14, P6 0/17). Offline:
`pytest python/test_sync_dominance.py python/test_coherent_ldst.py` is fully green for the first
time (rtraw was the standing failure).

Not finished (jobs cancelled on request; the bench re-run moves to another session):
- shard 0 (18 programs: 12 P1, 2 P2, 2 P3, 2 P6) — its first attempt died when the kernel OOM killer
  took the harness instead of the engine run of `P6-asyncmemcpy-memcpy_htod_kernel_race-fixed`;
  `blib.run_timed` now marks the traced app as the preferred OOM victim (`oom_score_adj=1000`).
  Re-run: `sbatch --array=0 eval/baselines/setup/p_evcand.sh`.
- the same-trace BEFORE pass (`sbatch eval/baselines/setup/p_evcand_base.sh`, analysis only, new rules
  off) and its comparison (`--before 'eval/results/evcand_base/*.csv'`).
- Kept traces: `/mnt/beegfs/fzheng4/cuvein_traces/evcand` (~138 GB, 597 programs, `STORE_INFO.json`;
  compute nodes only, not backed up) and the 6-program `evcand_smoke` store. Both scripts pin
  `--manifest eval/baselines/setup/manifest.evcand.csv` (= `manifest.pre-PI.csv`): the live
  `manifest.csv` was rewritten during the run (pset PI added, P2 dropped), which changes sharding.

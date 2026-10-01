# CLAUDE.md — cuVein race detector (branch `cuVein`): standing rules + the Sept-2026 task queue

This file is read by every Claude Code agent that works in this checkout on the GPU
cluster. Part A applies to every task. Part B is the plan. Part C holds one
self-contained brief per task; you are normally launched with "do task Tn".
Written 2026-09-22 against `cuVein` HEAD `b7d463e` (merge of the head-to-head
evaluation); revised the same day after Jeffery's review (cluster inventory, storage,
full rename, host-memcpy scope, the publish/tick example), and on 2026-09-24 for the
state after T0/T8/T5a/T2/T3/T1a merged (`cuVein` 3331d35; see the status paragraph in
B2) and for the consolidated proof document on PR #4
(`design/proof/hb_proof.tex`: T6 becomes a review task, decisions D6/D7/D8 added), and on
2026-09-26 after the latent census (T9-0, `eval/LATENT_CENSUS.md`): D1/D6/D7/D8 resolved,
the instance gate and the three-verdict matrix in the proof, tasks T10–T12 added, T5b on
the critical path, the deadline rule in A1; and on 2026-09-27 after T6's review
(`design/T6_REVIEW.md`, PR #4 merged): T3b's brief corrected on four points, T9 widened
(buckets in both clocks, local memory excluded, R2 decides class not verdict, the `sc`
column), T5b moved ahead of T12, T12's design note extended with T6's findings, `bar.arrive`
and the access-size gap recorded as deferred deviations; and on 2026-09-28 after T3b and T9
finished (both on their branches, unmerged): the green set extended, the merge and
install procedure written into the status paragraph, A2 (RMW coherence order) recorded
as a fidelity finding with decision D15, T13 (the NVBit spike) added; and on 2026-09-28
evening after the merge (`cuVein` 6c34736: T3b + T9 + T13 in, library 75f46012 installed)
with T13's result — A2 inverts 1–4 % of contended hand-offs, so D15's flag is built as
T14 — and the proof's 09-27/28 edits re-applied on the merged file; and on 2026-09-29 after
T10 and T14 finished: D9 adopted, D2 amended (PTX primary, ScoRD's notion as a second column
for ScoR), D15's rate corrected to the Sanitizer's own (11–32 %) with the explanation of the
gap to NVBit, T15 (late ordering key) added, the T11 lead from ECL-GC recorded; and on
2026-09-30 after T15, T5b and T12 finished: the late key measured and not adopted and D15's
"explanation" withdrawn (schedule determinism; the NVBit gap unexplained), T5b and T12 merged
with their numbers, D11's list extended, the R1 same-pc over-claim and the R3 landing hole
closed, T4 reframed as no-dump mode and put on the critical path, T16 (the certain clock) and
T17 (the `HbEngine` rename) added. If HEAD has moved, re-read `eval/BASELINES_SUMMARY.md`,
`eval/FIX_REPORT.md`, `eval/FP_DIAGNOSIS.md` and `git log` before starting.

---

## A. Standing rules (every task)

### A1. What this repo is
AccelProf/cuVein: a GPU data-race detector for CUDA binaries. A Compute-Sanitizer
collector (`nv-compute/`, `sanalyzer/src/tools/pc_dependency_analysis.cpp`) records
per-warp memory/sync records; with `YOSEMITE_HB_TRACE=1` it dumps them as `hb_events`
into `kernel_N.json` and, in vector-clock mode (`YOSEMITE_HB_MODE`, the default), runs the
in-process C++ `HbClock` (vector clocks) over the same stream. `python/hb_oracle.py` is the
exact offline specification `HbClock` must match bit-for-bit; `python/sync_dominance.py` joins the
kernel CFG (nvdisasm) with the trace and produces the verdicts (R1 dominance, R2
coherence, R3 chain, offline barrier-only pass, event-stream candidates, verdict matrix).

The two modes (named by T8; the pre-T8 names survive only in `python/hb_modes.py`'s
compatibility path):
- **scalar-clock mode** (`YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock`): static rules
  + `sync_dominance.barrier_only_pairs()`, which needs only a per-thread scalar epoch.
- **vector-clock mode** (`YOSEMITE_HB_TRACE=1`, `YOSEMITE_HB_MODE=vector-clock` the
  default): `HbClock` in the analyzer + `hb_oracle.py`, full scoped vector clocks,
  per-address release/acquire.
`HbClock` (T17, D17) is the computation — it owns the per-thread clocks, whose value type is
T5b's `VClock`. Docs say vector-clock / scalar-clock for the modes and name `HbClock` only when
the sentence is about that code; do not mix vocabularies inside one file, identifiers
included.

Ground truth for the current state: `eval/BASELINES_SUMMARY.md` (head-to-head vs
racecheck, HiRace, iGUARD, SuperCollider; 2026-09-22), `eval/FIX_REPORT.md` (F1–F6),
`eval/FP_DIAGNOSIS.md` (RC1–RC5 + two addenda), `HARDENING_REPORT.md` (TV invariants,
scale), `roadmap.md` (method), `eval/README.md` (how to run the harness).

**Deadline rule (PLDI 2027).** The CFP is not posted yet; plan for a mid-November 2026
submission, the last three weeks of which are writing. The proof document
(`design/proof/hb_proof.tex`, revision 2026-09-26) is frozen except for the items its
"Order of work" lists; agents do not extend it (no I7 re-proof, no discharge of MM1–MM3,
no separate PTX-bridge proof) unless a brief says so. Code lands in this order: T6 (doc
review, done) → T3b, T9, T10, T14, T15, T5b, T12 (done, merged at 7849a70) → T17 (rename,
half a day) → T4 (no-dump mode, the critical path) with T11 and T16 alongside → the mode
comparison, the tables and one baseline re-run. T1b, T7, I6, the `bar.arrive` flag, the
access-size check and the value-recording collector are after the submission. When a task can finish without a GPU
(re-scores, census-style measurements), it does.

### A2. Environment (NCSU ARC SLURM cluster)

**A2.1 Nodes — from `sinfo` on 2026-09-22.** The compute-capability column is the
expected value for the partition's GPU; confirm it on the node with
`nvidia-smi --query-gpu=name,compute_cap --format=csv` (`parallel.py:_arch()` records
it in every `meta.json`).

| partition | nodes | time limit | GPU | expected cc |
|---|---|---|---|---|
| `rtx4060ti16g` | 35: c0-3, 23-24, 37, 50-56, 58, 60-79 | 1 d | RTX 4060 Ti 16 GB | sm_89 |
| `rtx4060ti8g` | 7: c20-22, 26, 28, 34, 57 | 1 d | RTX 4060 Ti 8 GB | sm_89 |
| `rtx5060ti16g` | 9: c4-10, 27, 59 | 1 d | RTX 5060 Ti (Blackwell) | sm_120 |
| `rtx3060ti` | 2: c25, 48 | 1 d | RTX 3060 Ti | sm_86 |
| `rtx2060super` | 12: c21, 25, 34, 39-47 | 1 d | RTX 2060 Super | sm_75 |
| `rtx2080super` | 1: c22 | 1 d | RTX 2080 Super | sm_75 |
| `a4000` | 2: c35, 36 | 1 d | RTX A4000 | sm_86 |
| `a6000` | 2: c30-31 | 8 d | RTX A6000 | sm_86 |
| `a5000ada` | 2: c32, 49 | 8 d | RTX 5000 Ada (or A5000 — check cc) | sm_89 (sm_86 if A5000) |
| `a100` | 1: c33 | 8 d | A100 | sm_80 |
| **`h100`** | **1: c29** | 8 d | **H100** | **sm_90** |
| `normal` / `max` / `all` / `class` / `csc549` | the same 80 nodes c0-79 | 1 d / 8 d / 8 d / 4 h / 8 h | general partitions; check `scontrol show partition` for gres | — |

Consequences that earlier documents got wrong:
- **sm_90 exists** (`h100`, node c29, one node, 8-day limit, often allocated — expect
  queueing; `sbatch --partition=h100`). `cp.async.bulk` / TMA / distributed shared
  memory and the 8 cuHadron `bulkcpy`+`dsmem` targets can be built (`-arch=sm_90`) and
  run there. The Blackwell `rtx5060ti16g` nodes (sm_120, 8 idle at the time of writing)
  may run the non-cluster bulk copies too — verify by compiling. What does not exist is
  sm_70 (iGUARD's precompiled Volta binaries still need a source rebuild).
- Several nodes carry two different GPUs (c21/c34: 2060 Super + 4060 Ti 8 GB; c25: 2060
  Super + 3060 Ti; c22: 2080 Super + 4060 Ti 8 GB). Pin `CUDA_VISIBLE_DEVICES` there
  (`setup/pin8g.sh` does it for HiRace/NVBit). Traces are architecture-specific (PC
  offsets, CFGs): never mix compute capabilities inside one sweep tag; `meta.json` has
  `arch` and `node` for every program.
- CPU work (the offline analysis, table generation, converters) does not need a GPU
  partition — use `normal`/`max` and read the traces from BeeGFS (T0).
- Node RAM/scratch as observed in `eval/BASELINES.md` §1b: 188 GB RAM, node-local
  `/mnt/local` 914 GB on most nodes but 230 GB on c37 and root-owned on c2 — check
  `df -h /mnt/local` on the node you get.

**A2.2 Storage.** Home has a 40 GB quota. BeeGFS `/mnt/beegfs/$USER` is a 100+ TB
parallel filesystem (per the ARC admins; not backed up). All trace IO belongs on BeeGFS —
see T0 for why the previous "keep every trace" attempt lost data and for the policy.

**A2.3 Toolchain — as documented in the repo; verify on a node before relying on it.**
- Login node has no usable CUDA/GPU (`eval/baselines/blib.py:16-20`): nvcc, nvdisasm,
  compute-sanitizer and every GPU run go through `srun`/`sbatch`. Documented versions:
  CUDA 13.3, Compute Sanitizer 2026.2.1.0, driver 580.82.07 (`setup/blockers.md`).
- Python env `.env/` (py3.10, networkx 3.2.1, pydot; `eval/README.md`). Tests run with
  the env's python **directly** — `.env/bin/python -m pytest …` — never under `conda run`
  (a nested `conda run` in `getall.sh` silently drops the atomic-scope sidecar and every
  atomic degrades to a plain access). Wipe `ScoR/microbenchmarks/artifacts/*` first so
  traces regenerate.
- Build: `nv-compute` (fatbin) and `sanalyzer` must be rebuilt after any `.cu`/`.cpp`
  change; the analyzer library (`libsanalyzer.so`) must install into the RPATH location
  `build/sanalyzer/lib`; the existing build used the conda compiler
  (`CXX=/home/fzheng4/miniconda3/bin/x86_64-conda-linux-gnu-c++`, `eval/FIX_REPORT.md`).
  **spack is available** (`eval/baselines/setup/spack_setup.sh`, `spack_env.sh`; used
  for GNU time/TBB) and is the alternative source for gcc/cmake/cuda toolchains if the
  conda one misbehaves; also check `module avail`. Build notes live in the agent memory
  file `memory/build-toolchain-gotchas.md`; `HARDENING_REPORT.md` and `roadmap.md` (risk
  register) describe the latent heap-corruption UB that forbids adding members to
  `PcDependency` — keep `HbClock`'s state in its file-static singleton.
- `ACCEL_PROF_HOME=/home/fzheng4/AccelProf` is the runtime checkout. A worktree becomes
  a full runtime mirror by symlinking the gitignored dirs `lib build .env nv-compute/lib
  ScoR cuHadron` from the main checkout and setting `CUVEIN_HOME=<worktree>` for
  `eval/driver.py` (see `eval/README.md` §"Re-analyzing existing traces").
- `accelprof -n 1` (single worker) is required for HB runs; the atomic-scope sidecar
  (`YOSEMITE_ATOMIC_SCOPE_FILE`, produced by `python/atomic_scope_sidecar.py` from the
  CFG dots) is mandatory.
- Run one GPU batch at a time per node; kill stragglers by PID. Big sweeps go through
  the sbatch scripts in `eval/baselines/setup/` (`p_*.sh`); results must land in a
  **new** directory under `eval/results/<tag>/`, never overwrite
  `eval/results/baselines-*.csv`.
- Kept traces for offline re-analysis (no GPU): the BeeGFS stores
  `/mnt/beegfs/fzheng4/cuvein_traces/<tag>` (`evcand`: 597 programs; T0 adds the full
  store) and the home copies `eval/baselines/traces_keep*/<id>/` (FP/FN/ERROR/TIMEOUT
  programs only, size-capped). `eval/baselines/parallel.py analyze --results-dir …
  --confirm-dir …` re-scores a store; `eval/reanalyze.py` re-runs the static leg on
  driver-style traces.

### A3. Branching and commits
- One git worktree + one branch per task: `git worktree add ../wt-<task> -b <branch>`
  (branch names are given per task below). Never commit to `cuVein` directly. When the
  task's acceptance criteria hold, merge with `git merge --no-ff <branch>` into `cuVein`
  and report the merge commit. If two tasks touch the same files (see the dependency
  column in B2), rebase onto the merged one before merging.
- Commit messages: imperative subject, a body that states what was verified and on which
  hardware/corpus. **Do not add a `Co-Authored-By` trailer.** The existing
  `Claude-Session:` trailer is fine.
- Do not modify `bin/accelprof` or the default (non-`YOSEMITE_HB_TRACE`) collector path:
  every collector change must be additive and gated so that the default tool output is
  byte-identical.

### A4. Correctness discipline
- `HbClock` == specification is a hard invariant: any change to `HbClock` is mirrored in
  `python/hb_oracle.py` in the same commit, and vice versa. Gate:
  `test_hb_clock_matches_specification` (`python/test_sync_dominance.py:179`,
  `python/test_coherent_ldst.py:158`) and `test_offline_barrier_pass_matches_oracle`
  (`python/test_coherent_ldst.py:182`).
- The green set, run before and after every change:
  ```
  rm -rf ScoR/microbenchmarks/artifacts/*
  .env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
      python/test_coherent_ldst.py python/test_atomic_memory_model.py \
      python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py
  ```
  Expected (after the T3b + T9 merge): everything passes, exactly one xfail
  (`test_relaxed_handoff_should_race`, the documented I4 case, until T12). A new failure
  is never "unrelated". The GPU halves of `test_barrier_exit.py` and `test_cp_async.py`
  skip on a runtime built before their change — a skip there means the installed
  `libsanalyzer.so` is stale, not that the test is fine.
- Verdict deltas are reported, never hidden: for any change that can flip a verdict,
  produce a before/after table over the kept traces (`compare_fpfix.py --before … --after-glob …`)
  and list every true positive lost and every new false positive by program.
- No case-specific heuristics, no benign-race or value-based tolerance in the detector,
  no reachability-as-ordering. If an idea needs a pattern match on a program, stop and
  write it up as a proposal instead.
- The fence gate governs (ATOM) edges only, never `ms` (`hb_proof.tex` Definition
  "Gate"). Scope is the one static label that must err narrow: a widened scope hides a
  report through the two-RMW exception (Lemma "Monotonicity", converse).
- R2 (both pcs coherent at scope ≥ d) decides the DR/SC class of a pair and never its
  verdict; ORDERED comes only from R1, R3, the barrier-only clock, and `hb_races` vetoes
  them. `model_bug` is raised by R1 alone (`hb_proof.tex` §5, 2026-09-27).
- Local memory is outside the HB model (`hb_proof.tex` Definition "Records"): the HB
  trace path does not emit `MemoryType::Local` records, and `HbClock`, oracle and
  `barrier_only_pairs` skip any `local` record of an older dump. The collector's
  default path and its local-address tag are not touched.
- The fence instructions of `fenced(p, p', s)` come from the per-architecture inventory
  (T12 step 1), never from a hard-coded `MEMBAR`: on sm_89 an acquire lowers to the
  access plus `CCTL.IVALL` with no `MEMBAR`, and `BAR.SYNC` carries the ordering with no
  adjacent fence (T6, 293 CFGs).
- `hb_events`, when written, stays lossless: offline trace-validity checking, the census
  scripts and every re-score replay it. Not writing it for a program (T4's no-dump mode)
  is allowed; writing a lossy version is not. Parity between the vector-clock
  implementation and the specification is established on the programs that dump.
- A labelled-clean program the detector reports under PTX §8.7.1 semantics (fence
  missing on one side of a hand-off) is not suppressed and not relabelled silently: it
  gets a footnote hook in `make_tables.py` with the PTX reason and, where available,
  a baseline that agrees (D11).
- Distinguish in every report: **proved-in-effect** (an invariant checked over N real
  traces), **tested** (a specific verdict asserted), **assumed/unverified**.
- Persisted artifact names (CSV column names and values, kept-trace directory names,
  confirm-file names, result-file suffixes) change only through a converter that
  migrates every existing store in the same change and logs what it touched — T8 does
  this once for the mode names. The `kernel_N.json` keys (`hb_events`, `hb_races`,
  `hb_races_sync_only`, `coherence_profile`, `tv_violation`) are not mode names and
  stay; new fields are added alongside them and old readers must ignore unknown fields.

### A5. Reports
Every task ends with a markdown report at the path given in its brief (under `eval/` or
`design/` — `docs/` is the upstream documentation submodule), containing: the exact commands run, the numbers, the git revision, hardware, and
a "what remains unverified" list. Facts only; no simulated results. If a step is
infeasible on this cluster, say so and stop rather than approximating.

---

## B. The plan

### B1. Order and rationale
The nine todos split into three kinds. **Functionality** (1 cp.async.bulk, 2 cp.async
H2D, 3 crs-cuda, 9 soundness), **documentation** (6 pseudo-code, 8 rename) and
**cost** (4 event size, 5 memory footprint, 7 rewrite). Jeffery's own note on todo 4
fixes the tail of the order: pre-aggregating `hb_events` destroys replayability, so it
is done only once functionality is settled. The head of the order is the rename: it is
mechanical, takes hours, and everything written afterwards (pseudo-code, reports, the
paper) should use the final vocabulary — doing it first also avoids merge conflicts in
the comment-heavy files every other task touches.

Two things surfaced while reading the code that the plan has to carry:

1. **Publish/tick order in the vector-clock algorithm — a concrete missed race.**
   Algorithm 1 of the proof (and the progress deck's "publish, then tick" slide) publishes
   the release clock and *then* ticks the releaser's own component, so the published
   clock never covers the releaser's later accesses. The checked-in code does the
   opposite: `python/hb_oracle.py:283-284` (`vc[t][t] = own(t) + 1` then
   `released[loc] = (VC(vc[t]), …)`) and `HbEngine`
   (`sanalyzer/src/tools/pc_dependency_analysis.cpp:357-359`: `nc = own(t)+1; vc[t][t] =
   nc; released[loc] = Released{vc[t], …}`). The two-modes deck notes already record this
   as an open implementation obligation; what follows is the race it loses. Threads `t`
   (block 0) and `u` (block 1), grid-scope atomics on `f`, plain `x`; `t`'s own epoch is
   `c` before its release. Trace order and what the checked-in oracle computes:

   | seq | record | checked-in code | Algorithm 1 |
   |---|---|---|---|
   | 1 | `t`: atomic on `f` (release / unlock) | tick to `c+1`, publish `{t:c+1}` | publish `{t:c}`, atomic recorded at `c`, tick to `c+1` |
   | 2 | `t`: write `x` | `last_write[x] = (t, c+1)` | `last_write[x] = (t, c+1)` |
   | 3 | `u`: atomic on `f` (acquire / lock) | `vc[u][t] = c+1` | `vc[u][t] = c` |
   | 4 | `u`: read `x` | `c+1 > c+1` is false → **no report** | `c+1 > c` → RAW race reported |

   Nothing orders `t`'s write at seq 2 (after its unlock) before `u`'s critical section —
   it is a genuine race — and the checked-in engine and oracle stay silent whenever the
   releaser's post-release access precedes the acquirer's access in trace order (in the
   opposite trace order the reader-set check catches it as a WAR). This is exactly the
   ScoR `race_interblock_none-lock_rtraw` kernel (block 0: `lock; read data; unlock;
   data[0] = 1`; block 1: `lock; read data; unlock`) in the schedule where block 0 runs
   first. The recorded trace had block 1 first, where the hand-off genuinely orders the
   pair, so the vector-clock leg's silence there was correct. The miss *has* since shown
   in the corpus: T9-0 found it in the evcand vector-clock dump of
   `race_interblock_fence_rtraw` (block 0 reads `data` after its own release at seq 7,
   block 1 writes it at seq 8, `hb_races` empty; the verdict survived only as `latent`).
   The fix is the three-line reordering in the two files (and the atomic recorded at the
   pre-tick epoch); it changes verdicts corpus-wide (more reports wherever a releaser
   touches shared data after its release), so it is folded into T9 with an offline
   re-score. D1 is decided (apply).
2. **cp.async.bulk is testable after all.** The cluster has an H100 node (`h100`
   partition, c29, sm_90; A2.1), so T1 is split into T1a — the already-designed cp.async
   fix (F4), testable on sm_86/89 — and T1b, the bulk/TMA extension validated on c29 with
   the eight cuHadron `bulkcpy`/`dsmem` targets built for sm_90.
3. **The previous "keep every trace" attempt lost data because of the harness, not
   BeeGFS.** Only one sweep pointed the trace store at BeeGFS, and that one ran with a
   20 GB per-program cap that silently deletes the largest traces; every other sweep used
   node-local `/mnt/local` (230 GB on c37) and hit `No space left on device` there. T0
   fixes the storage policy first, because every later GPU sweep depends on it.

### B2. Task table

| id | todo | task | agent (model · role) | GPU | depends on | branch |
|---|---|---|---|---|---|---|
| T0 | — | storage: BeeGFS as the only trace store; inventory of what the earlier "keep all" run dropped; no caps | Sonnet · infra | one node of each kind | — | `infra/beegfs-store` ✓ merged |
| T8 | 8 | rename the modes to scalar-clock / vector-clock, **including persisted strings** (converter over CSVs, kept stores, confirm files) | Sonnet · implementer; Sonnet subagent runs the green set + `make_tables.py` on migrated data | no | T0 (store inventory) | `rename/clock-modes` ✓ merged 1a45653 + 81b4262 |
| T6 | 6 | review of `design/proof/hb_proof.tex` against the code: deviation table, simulator, strict xfails for I1/I2/I5, referee reading, SASS scan for O2 | Opus · reviewer/verifier (fresh context) | one node | T8 ✓ | `design/algorithms` ✓ 8d1e36e, report `design/T6_REVIEW.md`; PR #4 merged |
| T3 | 3 | crs-cuda: the HeCBench program cuVein reports and SuperCollider calls race-free | Opus · investigator (+ Explore subagents); GPU for the reproducer and cross-checks | yes | T8 | `triage/crs-cuda` ✓ merged d8eb112 — false positive, cause below (T3b) |
| T3b | 3 | exit-aware `__syncthreads` instance assembly (route (a), D7 decided): exit records in `hb_events`, exited threads subtracted from the expected count of whole-block instances (counted barriers keep `n`), `Complete` on exit — in `HbEngine`, `hb_oracle.py`, `barrier_only_pairs`; the end-of-kernel `pending_barriers` check in the engine and offline; crs-cuda needs a fresh recording (kept dumps have no exit records) | Sonnet · implementer, Opus · reviewer | yes (crs-cuda fresh trace + green set) | D7 ✓, T6 ✓ | `fix/barrier-exit-count` ✓ done 2026-09-28 (aab77ca, 0e4e061; crs-cuda CLEAN 50/50 both modes; report `eval/CRS_CUDA_TRIAGE.md` §11) — merged 0b64d34 → `cuVein` 6c34736 |
| T2 | 2 | host-memcpy (`cudaMemcpyAsync`) races: evidence, stream-agent model, prototype behind a flag | Sonnet · investigator, Opus · model review | small | T8 | `feat/host-memcpy` ✓ merged 07d2798 (`YOSEMITE_HB_HOST_MEMCPY`, `python/host_hb.py`; D5 open) |
| T1a | 1 | apply the designed cp.async fix (F4: PIPELINE_WAIT + virtual async agent) | Opus · design check, Sonnet · implementer, Opus · verifier | yes (rebuild) | T8, T2 | `feat/cp-async-wait` ✓ merged bc32a1f + review 3331d35 (F4 fixed; runtime install pending) |
| T5a | 5 | memory-footprint table from existing CSVs + engine state attribution | Sonnet · analyst | 3 runs | T8 | `study/memory-footprint` ✓ merged 6d843e3 (`YOSEMITE_HB_STATS`, `eval/MEMORY_FOOTPRINT.md`) |
| T9-0 | 9 | latent census: what the `latent` tier catches and costs, fact (i) checked on the kept stores | Sonnet · analyst | no | — | `study/latent-census` ✓ report `eval/LATENT_CENSUS.md` 2026-09-26 (merge pending) |
| T9 | 9 | vector-clock soundness: I1 (publish-then-tick) + I2 (buckets in **both** clocks, SC reported) + I5 (local memory excluded) in one change to oracle, engine and `barrier_only_pairs`; R2 moved from verdict to class, the `sc` column, `make_tables.py` for D2; the T6 strict xfails and `fence_rtraw` as regression tests | Opus · prover; Sonnet · implementer; Sonnet subagent for the re-score | re-score only + one P5 sweep | T6 ✓; D1/D6 ✓ | `fix/publish-then-tick` ✓ done 2026-09-28 (b1a6408; 554 programs re-scored, no verdict moved at Race ∪ Latent; report `eval/T9_RESCORE.md`) — merged ebc464f → `cuVein` 6c34736; library 75f46012 installed; green set 238 passed + the one expected failure; evcand 3,621 rows unchanged; one new FP at Race alone (A2, D15 → T14) |
| T10 | — | sidecar strength and scope (O1): a load/store is strong at the scope its `.STRONG.<scope>` token names, generic and address-spaced alike (`volatile` included); default policy `token`, the old ones ablations | Sonnet · implementer, Opus · review | re-score only | T9 ✓ | `fix/sidecar-strength` ✓ done 2026-09-29 (f2a5bde; `eval/SIDECAR_STRENGTH.md`): 1,141 of 1,306 DR instances on the 43 ScoR programs with `volatile` become SC, no other program moves (545 × 2), 5 FPs removed, none added, green set 275 + 1; D9 adopted — **merge pending** |
| T11 | — | monitor: TV checks in one Python module shared by oracle, `barrier_only_pairs` and a standalone `tv_check` CLI; `HbClock` keeps them behind `YOSEMITE_HB_STRICT`; delete the `expected == 0` degrade path; per-lane W2 row (I6) only if cheap | Sonnet · implementer | no | T3b (fifth check) | `fix/tv-monitor` |
| T12 | — | I4: the instance gate and R3's release/acquire points from the trace | Opus · design + review, Sonnet · implementer | re-score + one P4/P5 sweep | T9, T10 | `feat/instance-gate` ✓ done 2026-09-30, rebased on T5b, merged 7849a70 (library e527875d installed; `eval/INSTANCE_GATE.md` §9, `design/instance_gate.md`): green set 305 + 55 gate tests, Detect == oracle 32/32 under both gates, T5b's parity set 60/60 (412 kernels, 0 mismatches); `test_relaxed_handoff_should_race` passes, xfail removed; the 8 ScoR fence races reported in the run that recorded them (as SC); `reduction-norace` and 5 `norace_*fence*` litmus reported (D11); CC push 1296n 6.9 → 1.3 GB on T5b's clocks; matrix-multiplication-small 11 s; beyond the brief: R1 certifies no same-pc pair (uts-norace-small CLEAN), `model_bug` an annotation, R3 declines a chain landing on the reader's own unlock; no verdict moves on 594 programs |
| T1b | 1 | cp.async.bulk / TMA / dsmem model, validated on the H100 node with the 8 cuHadron sm_90 targets — **after the submission** | **Fable** · design + implementation (the hardest task in the queue); fresh Fable context as verifier | yes (`h100`, c29) | T1a ✓ | `feat/cp-async-bulk` |
| T13 | — | NVBit feasibility spike: after-execution atomics with the value read; A2 inversion rate in vivo; overhead — report only | Sonnet · analyst | yes (one `salloc`) | none | `study/nvbit-spike` ✓ done 2026-09-28 (0a444e9, merged into 6c34736; `eval/NVBIT_SPIKE.md`): NVBit 1.8 loads on driver 580 (README says ≤ 575; the submodule's 1.7.1 does not load); old values correct in every test; Sanitizer-order inversions 0/155, 4/315, 52/1,275 hand-offs at 2/4/16 warps; cost 427× native unoptimised vs 134× for the Sanitizer HB path on the one kernel-dominated input |
| T14 | — | A2 in the tables: the `a2_uncertain` report flag (D15) and the offline RMW window count over the kept dumps; no verdict change | Sonnet · implementer, Opus · review of the flag's definition | no (kept dumps) | T9 ✓ | `feat/a2-flag` ✓ done 2026-09-29 (2c979fd; `design/a2_flag.md`, `eval/A2_WINDOWS.md`): flag moves 0 of 558 verdicts; 397/397 programs with cross-warp RMWs have overlapping windows; 432,810 DR instances flagged in 34 programs; 3 race-free ScoR programs' Race-alone verdicts rest on flagged reports only; Sanitizer's own inversion rate 11 / 32 / 28 % at 2 / 4 / 16 warps; green set 250 + 1 — **merge pending** |
| T15 | — | late ordering key for the HB records, measured before adoption | Sonnet · implementer | yes (one node) | T14 ✓ | `perf/late-seq` ✓ done 2026-09-29 (55fe57c; `eval/LATE_SEQ.md`): behind `YOSEMITE_HB_LATE_SEQ=atomic|timer`; cuts lock-hand-off inversions ~12 % (14.3→12.7 % at 4 warps, 16.6→14.7 % at 16); `%globaltimer` ties 87 %; **not adopted, off by default**; the dual-key dump (`bpos`, `lkey`) kept for measurement — merged de565c0; its collector and fatbin installed with the T17 merge (b6c9055) |
| T5b | 5 | shared-base main clock for vector-clock mode's runtime | Sonnet · implementer, Opus · reviewer | yes | T1a ✓, T9 ✓ | `perf/shared-base-clock` ✓ done 2026-09-30, merged b3bfdf3 (`eval/MEMORY_FOOTPRINT.md` §7): no clock value changes; green set 287 + 1; implementation == specification on 60/60 programs, 410 kernels; tiled_gemm `vc` 67 M → 131 k entries (4.5 → 1.95 GB), reduction-large 7.2 → 1.3 GB, CC push 1296n from OOM at 119.7 GB to 17.9 s / 6.9 GB; 25 of the 48 non-barrier timeout programs finish under 120 s; the 10 barrier-only programs cannot be reached by any clock change — 9 do not finish in scalar-clock mode either (100–252 GB of `hb_events` in 1,200 s, or OOM): **trace volume bounds both modes → T4** |
| T4 | 4 | **no-dump mode** (reframed 2026-09-30, on the critical path): both clocks computed during the run, only the per-pc-pair aggregates the verdict layer reads written at kernel end; lossless dump kept for programs that can replay; then the nine barrier-only programs and HeCBench in both modes; optional second half: streaming binary encoding for the mid-size suites | design: Opus · impl: Sonnet | yes (the timeout set, then P7/P9) | T5b ✓, T12 ✓, T17 | `feat/no-dump` |
| T16 | — | the certain clock: accept a chain edge only when the two RMW windows do not overlap; a third operating point "Race (sound)" in the tables; no GPU — **decision pending** | Sonnet · implementer, Opus · one-paragraph soundness note | no (kept dumps) | T14 ✓ | `feat/certain-clock` |
| T17 | — | rename `HbEngine` and its identifiers to the mode vocabulary (D17: `HbClock`); `YOSEMITE_HB_NO_ENGINE` retired with a warning; readers accept both spellings of any persisted field; historical reports untouched; no value changes | Sonnet | no | T12 ✓ merged | `chore/rename-hb-clock` ✓ done 2026-09-30 (663a288, merged b6c9055 with T15's de565c0): on the old collector green set 305 + 2 skipped, gate 55/55, re-score P1–P7/P9 byte-identical; merged runtime installed 2026-10-01 (libsanalyzer 6134effc, collector f2933966, fatbin e9634312): crs-cuda CLEAN both modes, gate 55/55, but green set **4 failed** / 301 — the T15 collector puts the lock litmus (`none-lock_rtraw`, `lock_waw`) in a schedule with an A2 inversion; every new report is `a2_uncertain` — **open, Jeffery** |
| T7 | 7 (opt.) | profile `sync_dominance.py` on the P9-mr trace; port the hot pass only if profiling says so — after the submission unless T4's reader needs it | Sonnet · profiler; Opus if a C++ port is warranted | no | T4 | `perf/analysis-hotpath` |

**Status 2026-09-24** (`cuVein` at 3331d35): T0, T8, T5a, T2, T3, T1a are merged. What
they changed for the remaining tasks: the two modes are now `vector-clock` /
`scalar-clock` everywhere (`python/hb_modes.py`, `YOSEMITE_HB_MODE`); all traces live
on BeeGFS with a store inventory; `YOSEMITE_HB_STATS` measures the engine's memory
(O(threads²) confirmed with cross-block atomic hand-offs — T5b's case); cp.async copies
are async agents (`hb_async` dumps); host operations are logged behind
`YOSEMITE_HB_HOST_MEMCPY` (D5 still open); crs-cuda is a cuVein false positive caused by
exit-unaware barrier assembly (new task T3b; `hb_proof.tex` §7, I3). The
installed engine library is the T8 build — T1a/T2/T5a's C++ takes effect only once the
runtime built from 3331d35 is installed (each merge says so); do that before T1b.

**Proof state 2026-09-24** (PR #4; `design/proof/hb_proof.tex`, the one document, nine
pages): one model, one happens-before relation with the fence gate as a parameter, DR/SC
verdicts, one algorithm `Detect(T, M)` of which the two modes are the two instances, and
the proofs — complete, sound, the `sync` instance, the per-profile certificate — for it.
The code at 3331d35 is `Detect` with seven substitutions (§7, I1–I7): I1 tick before
publish, I2 one last write per location instead of buckets and SC dropped, I3 exits
ignored, I4 the trusting gate, I5 local memory by address, I6 monitor details, I7 the
cp.async agents outside the model. Consequences proved there: completeness holds for the
code; soundness fails on `R_miss` (I1, Proposition "Missed class": a releaser's plain
accesses between an RMW and its next tick, met after the acquirer — the rtraw case of B1)
and for DR under I2 (two unordered strong stores, a barrier, a weak load); fidelity fails
for early-exit kernels under I3 (crs-cuda); the certificate is void for the code until I1
and I2 are fixed and is relative to the implemented HB until I4 is. I1 and I2 were
exercised on the real `hb_oracle.py` with synthetic dumps (`design/proof/check_e1_e2.py`);
the rest is unreviewed hand analysis. T6 verifies all of it, T9 acts on it.

**Status 2026-09-26** (after T9-0, the latent census; detector still 3331d35). What the
census established, all on kept traces with the detector unchanged: (1) fact (i) of §5
holds on the same trace for 557 of 558 programs — scalar-clock's Race set is
vector-clock's Race ∪ Latent minus the vetoes; the exception is crs-cuda, where the
`CUVEIN_BARRIER_PASS_MAX_LANES` cutoff skips the offline pass (class (c)); across P1–P6
the only program whose verdict differs between the modes is the P5 canary (a veto).
(2) The `latent` tier alone reports 10 of 236 labelled races, all ScoR litmus: 8 are
fence/scope bugs the run did not order under PTX (I4 ordered them; R3's fence check kept
the verdict), 1 is I1's `R_miss` observed on a real trace (`race_interblock_fence_rtraw`),
1 is the rtraw lock genuinely ordered by the recorded acquisition order. Three of the ten
are reported by no baseline (`none-lock_rtraw`, `interwarp_blklock-no-stf_waw`,
`interwarp_dev-blklock-no-stf_waw`); iGUARD reports 7. (3) It costs 25 pairs on 5
race-free ScoR apps: 23 are R3's release-point defect (region dominance, fixed in T12),
2 the success-branch-fence idiom. (4) The per-pc PTX gate of the 09-24 draft would turn
`matrix-multiplication`'s correct lock into structural FPs — replaced by the instance
gate (proof Definition "Gate", T12). (5) Vector-clock mode has no dump for P7, 8 of 9 P9,
10 of 28 P4 and 23 P1 programs: the reference mode does not finish on the realistic
suites, which is why T5b is on the critical path. Decisions taken on this evidence: D1,
D6, D7, D8 (see B3); D2 follows from D8.

**Status 2026-09-27** (T6 done; `cuVein` at e50c509 locally, 3ed5c9c merged the
census; PR #4 merged with the reviewed proof, 14 pages). What T6 established beyond the
09-26 state (`design/T6_REVIEW.md`): (1) the code is `Detect` with I1–I7 plus three
unlisted deviations — `bar.arrive` recorded as blocking (the collector drops the
Sanitizer's `IS_SYNCHRONIZING` flag), no access-size/overlap check, no trace-validity
check in scalar-clock mode; none exercised by the corpus (no `BAR.ARV` in 293 CFGs),
all deferred. (2) I5 is worse than stated: the local-address tag is a 32-bit shift
(FlagZhao `nv-compute`, branch `cuVein`, commit `ccefba0`, 2026-02-11 — predates the
project; `AccelProf/nv-compute` `main` has the cast), 8,096 spurious race records on a
64-thread kernel, no verdict only because purely local pcs are not dependency nodes;
resolved by excluding local memory from the HB model (Yanbo's advice), not by keying.
(3) I2 also corrupts the barrier-only clock (8 barrier-unordered pairs missing on 3
litmus traces), so buckets go into `barrier_only_pairs` too and §5 fact (ii) holds for
the code only after T9. (4) Policy `none` never repaired soundness (FastTrack's
first-race guarantee only). (5) The §3 deferred acquire needed `Check(r)` against the
joined clock; the §5 matrix needed DR over SC per pc pair — both fixed in the document.
(6) O2 evidence: acquires lower to `CCTL.IVALL` with no `MEMBAR`; no `BAR.SYNC` has an
adjacent fence. (7) 10 of 58 engine-timeout programs are barrier-only. Decisions taken:
R2 decides class, not verdict (A4); T5b before/parallel with T12; local memory excluded.
Housekeeping: delete the untracked `hb_proof.tex` in the checkout root (the tracked copy
is `design/proof/hb_proof.tex`); the T9-0 branch is merged (3ed5c9c), not pending.

**Status 2026-09-28** (T3b and T9 done on their branches; `origin/cuVein` at 1a3aea5 =
PR #4 merged; this file's 09-27/28 revision is local until committed). T3b: crs-cuda
recorded afresh is CLEAN in both modes (was RACE 155/7), 247,587 exit records, old
dumps keep every verdict (3,739 rows, 0 changed); `TV-barrier-completion-order` had
fired on 46 of 50 kept crs-cuda kernels, so the per-warp monitor did catch the case —
nothing for T11 there; two further checks added (`TV-record-after-exit`, no exit while
waiting: W3 and the exit half of W2, previously unchecked). T9: I1, I2 in both clocks,
I5 by exclusion, D12 and the `sc` column; T6's three strict xfails pass; oracle equals
the `Detect` reference on 32/32 re-recorded ScoR traces; 554 programs re-scored, no
pair lost, 26 new DR pairs on 15 programs (`fence_rtraw`, `blklock_waw` among them), 200
SC pairs on Indigo `CudaAtomic`, no program verdict moved at Race ∪ Latent; the bucket
state is ±40 MB and the O(threads²) clocks are untouched (T5b). `hb_races` is now
aggregated per (pc pair, kind, class, space, distance, async) with a count — the
unmerged buckets produced 1.7·10⁹ records; no verdict depends on it, but
`latent_census.py` and the engine==oracle comparison read the aggregated form. Not
covered by the re-score: 4 P1 1296n programs (Python oracle out of memory) and
P9-mr-cuda (>2.5 h) — T7's profiling of `sync_dominance.py`/the oracle moves forward if
either matters for the tables. **New fidelity finding (A2):** the Sanitizer callback
runs before the instruction, so an atomic's record is its issue point; when two RMW
windows on one location overlap, trace order can invert coherence order. Effect at
Race alone: `matrix-multiplication-norace-small` becomes an FP (a successful lock CAS
recorded five records before the unlock it read from); the inversion also manufactures
an edge in the other direction (a missed-race risk, unmeasured). Decision D15 below;
T13 measures the rate and tests the fix's feasibility.

**Merged 2026-09-28 (`cuVein` 6c34736).** T3b (0b64d34) and T9 (ebc464f) merged with the
conflicts resolved as ebc464f's message records (exit counting kept from T3b, aggregated
`hb_races` from T9, `check_pending_at_end()` before `tv_violation` is written);
`libsanalyzer` 75f46012 built from the merged tree and installed (the collector needed
no change); green set 238 passed + the one expected failure
(`test_relaxed_handoff_should_race`); crs-cuda clean on a fresh recording; evcand
re-score 3,621 rows unchanged. T13 merged (0a444e9). The proof's 09-27/28 edits that T9
had not already made (Definition "Records" local exclusion, A1's A2 caveat, the fence
inventory in Definition "Gate", note (c)'s attribution, the measured A2 rate and D15,
the order of work) are re-applied on the merged `.tex` (16 pages).

**T13's result, and what it decides.** Recording atomics after execution with the value
read is feasible on this toolchain (NVBit 1.8, sm_89, driver 580), and against those
values the Sanitizer's issue-point order inverted the lock hand-off in 0/155, 4/315
(1.3 %) and 52/1,275 (4.1 %) cases at 2, 4 and 16 contending warps — every inversion
inside overlapping windows, none outside. So A2 is violated at a rate that grows with
contention and is not negligible: D15's second clause applies, the `a2_uncertain` flag
is built (T14), and the offline window count over the kept dumps is the number the
paper cites for its own corpus (T13's rates are one lock under NVBit's timing). Two
T13 findings for later: `ptxas` warp-aggregates `atomicAdd` on a constant address into
one leader RMW plus shuffles (per-lane attribution must recognise the idiom); `RED` has
no destination register, so a release through an unused `atomicAdd` result stays at its
issue position even under NVBit. The value-recording collector is post-submission
(one tool per process; a full re-evaluation).

**Status 2026-09-29** (T10 and T14 done on their branches; Jeffery merges by hand — the
permission classifier flags agent pushes to `cuVein`). **Merge:** `git merge --ff-only
origin/cuVein`, then `git merge --no-ff origin/feat/a2-flag`, then `git merge --no-ff
origin/fix/sidecar-strength` (D9 adopted); `git merge-tree` reported no conflict between
the two; rebuild `libsanalyzer` from the merged tree and install that file (the collector
is unchanged; neither worktree's `wt_install` has the other's change); green set expected
287 passed + the one xfail. Then delete the agent worktrees (`.claude/worktrees/agent-*`,
`docs-0928-evening`) — home is at 38.0 of 39.9 GB. **Docs on merge:** `eval/README.md`
§"False-positive diagnosis": `--strong-ldst {token,generic,all,none}`, default `token`,
and the `hb_a2`/`a2_uncertain` field; `hb_proof.tex` §7 carries T10's labeling text, item
(4) done, and the A2 gap explanation (this revision).

**What T10 and T14 established.** The strength rule never changes whether a pair is
reported, only its class (strength enters `ms` only), so T10's 1,141 DR → SC moves lose
nothing; what moves is how ScoR reads against its labels (D2, amended). T14's flag is
concentrated where the windows matter: in the ScoR applications 57 % of DR instances are
flagged and 26 pc pairs entirely; in P1/P2/P3/P5/P6/P9 no reported pair has every instance
flagged — every report there is A2-robust, which is the sentence the paper needs. The
Sanitizer's own inversion rate on the lock litmus is 11 / 32 / 28 % at 2 / 4 / 16 warps,
7–25× NVBit's — the number D15 and the paper must quote; **T15 (2026-09-29) withdrew the
explanation given here on the 29th:** a key drawn last cuts inversions only ~12 %, and
T13's tool did not draw its key last either, so the callback's length is not what decides
the rate. What the litmus shows is schedule determinism: the one-block levels repeat
identically run to run, and two builds of the same collector give 11 / 32 / 28 % and
0 / 19 / 25 %, so each configuration lands in one schedule and the rate is that
schedule's. Why NVBit's single schedules sit lower at every level is **not established**;
two untested candidates — instrumentation density lowering effective contention (a delay
knob in the critical section), and the buffer-full handshake releasing parked warps in
bursts (inversion positions against `bpos` modulo the buffer size, from T15's dumps, no
GPU) — are optional tail steps of T4. Quote the range (0–32 % on one lock across builds
and contention) and the corpus statement, not a rate. After T10 the three ScoR programs
are clean with their pairs SC, so **on the 558 programs no Race-alone verdict depends on
A2**; the exposure is confined to the `sc` column and to ScoR under ScoRD's notion. Open on A2w (an RMW has taken effect by its thread's next record): the
Sanitizer callback does not wait for the atomic's result; not measured for `RED`.
**T11 lead** (from T10): `TV-record-after-exit` fires on ECL-GC — either the exit callback's
lane mask over-reports the exiting lanes under ITS, or exit and memory records reach the
dump through paths whose relative order is not the warp's; T11 decides which before
touching the check.

**Status 2026-09-30** (`cuVein` 7849a70: T5b b3bfdf3 and the rebased T12 merged, library
e527875d installed; `perf/late-seq` 55fe57c on the remote, not yet merged — Jeffery merges
it by hand, flag off, no verdict change). What T5b and T12 established: (1) the vector
clock is O(threads) after a barrier and the implementation equals the specification on
60/60 programs; the remaining timeouts split into two kinds — atomic chains with no
barriers (P9 gpp, fpc: every thread's clock genuinely different; a persistent map, not
built) and barrier-heavy kernels where the runtime is 56 % of the time (hotspot). (2) The
nine barrier-only timeout programs do not finish in scalar-clock mode either: the HB path
holds `hb_events` in host memory for the whole kernel and serialises it as text at the
end, so they die of RAM or of the 1,200 s cap while writing 100–252 GB, and the offline
pass would then parse it for hours. Storage is not the limit; host memory, serialisation
and parsing are. That is why T4 is now no-dump mode and on the critical path. (3) The
instance gate on T5b's clocks: the 8 ScoR fence races reported in the recorded run;
`reduction-norace` through its ticket and five `norace_*fence*` litmus (consumer spins on
the flag with no fence after it — no acquire under PTX, ordered under ScoRD's one-sided
fences; 4 SC, `hrd-indirect` DR) all under D11; CC push 1296n 6.9 → 1.3 GB; the DR-latent
census category empty (rtraw's data is volatile, so it is now `latent-sc` — a report under
ScoRD's notion, informational under PTX). (4) Beyond the brief, closed in the same
branch: the code's R1 certified same-pc pairs across warps in one barrier segment
(uts-norace-small, a false RACE through the `model_bug` row) — R1 now matches the proof
(no certificate for one region), `CUVEIN_R1_LOOP_SCOPE=1` is the ablation; `model_bug` is
an annotation on the class's verdict, so an SC pair with it is a Strong conflict; R3
declined the rtraw race only for a CAS acquirer — with many threads a failed CAS hops to
another thread's unlock and the chain landed on the reader's own unlock, certifying the
race; `_past_release` now fires on that landing (`CUVEIN_R3_LANDING=0` restores the old
rule). Stated, not fixed: R3 does not recognise a lock taken by `atomicExch` alone or
released by a plain or `volatile` store (proof §5, R3b); vector-clock mode still reports
the pair when the run shows it unordered. (5) Not re-scored: P9 fpc-cuda and mr-cuda (4 h
analysis cap, as in T9-0).

Remaining order: merge `perf/late-seq`; T17 (the rename, while `pc_dependency_analysis.cpp`
is quiet); T4 (no-dump mode) with T11 (`tv_check` — the trace-validity counts over every
kept store are still owed) and T16 (if decided) alongside; then the mode comparison on
every suite both modes now run, the tables at both operating points with the `latent`,
`sc`, `a2_uncertain` (and, if T16, "Race (sound)") columns and ScoR's ScoRD-notion column,
one baseline re-run and `BASELINES.md` regenerated, overhead in both modes; then a
one-day T6-style consistency pass on the proof after the last code change. After the
submission: the value-recording collector (A2), T1b on `h100`, T7, I6, the `bar.arrive`
flag, the access-size check, the §6 referee notes, the persistent map for barrier-free
atomic chains.

### B3. Decisions Jeffery must make (blocking)
- **D1** (T9) — **decided 2026-09-26: apply publish-then-tick** in oracle + engine.
  The race it recovers is the one worked through in B1 item 1 (a releaser's access
  *after* its release); T9-0 found it on a kept trace (`race_interblock_fence_rtraw`,
  reported today only as `latent`). The change adds reports wherever a thread touches
  shared data after a release without another synchronization; T9 reports the deltas.
- **D2** (T9, tables) — **follows from D8, extended 2026-09-27**: `latent` is no longer a
  positive, and neither is `sc`. Tables are given at two operating points, Race alone and
  Race ∪ Latent (the latter equals today's counting); `latent` and `sc` are informational
  columns, counted as neither TP nor FP; in scalar-clock mode the `sc` column also holds
  strong–strong pairs an atomic hand-off ordered (it cannot tell), which is one more named
  class of the mode comparison. Counts are taken from the class before `judge`'s
  `benign`/`warp-po-ordered` relabels. `make_tables.py` changes accordingly in T9.
  **Amended 2026-09-29 (after T10):** the primary counting is PTX's for every suite — DR
  counts, `sc` and `latent` informational, both operating points. ScoR (P4 applications,
  P5 litmus) is additionally shown under ScoRD's own notion — DR ∪ SC as reports, TP and
  FP alike, symmetric — for comparability with prior work; the report set is
  policy-independent, so this column costs nothing. The stale-label cases are named, not
  absorbed: labels ITS invalidates (F1's volatile warp-tail; iGUARD agrees on the reduction
  programs), labels the PTX model reclassifies (16 of 18 litmus races: reported, as SC),
  labels PTX contradicts (the reduction ticket idiom, under T12's gate). One paragraph in
  the paper and a per-kernel table in the supplement; ScoR predates Volta and the PTX
  memory model, and the paper says so.
- **D3** (T8) — **decided 2026-09-22: migrate the persisted strings as well.** T8 ships
  the converter and runs it over every result CSV, confirm file and kept-trace store
  (home and BeeGFS); readers keep a one-release compatibility path that warns.
- **D4** (T1b): the 8 cuHadron `bulkcpy`/`dsmem` targets become runnable on c29. Should
  the *other* tools (compute-sanitizer racecheck, iGUARD rebuilt with `ARCH=sm_90`,
  SuperCollider's own binaries) also be run there so the matrix row is complete?
  Recommended: yes — it is one sbatch on `h100` per tool.
- **D5** (T2): cuHadron `asyncmemcpy/*` is **not** out of reach of the current
  architecture — neither the GPU architecture (the tests build and ran on sm_86/89; they
  timed out on trace volume) nor the software one: the collector already intercepts every
  host `cudaMemcpy*` with direction, size, `isAsync` and stream
  (`compute_sanitizer.cpp:1189-1211`) and forwards it to every tool; `PcDependency`
  drops it at `evt_callback`'s `default:` (`pc_dependency_analysis.cpp:1567-1577`). What
  is out of the current *model* is host-side ordering: a memcpy is an access by a
  stream agent, ordered against kernels by stream order/events, not by in-kernel
  synchronization, and the engine resets per kernel launch. T2 builds the evidence and a
  prototype; the decision is whether the paper's scope includes host↔kernel and
  kernel↔kernel (`interkernel/*`, same mechanism) races. If yes, both categories move
  from "out of scope" to real rows, and the two shipped cuHadron tests need a reduced-size
  build or a new micro test to finish under the tracing budget.
- **D6** (T9, from `hb_proof.tex` §4 Remark "Why one bucket per key" and §7, I2): the `coherent()` conflict filter
  (`--strong-ldst generic`, the RC1 fix of 2026-09-17) makes vector-clock mode unsound
  with a single `last_write` per location — the three-thread counterexample of that remark
  (two unordered `.STRONG` stores, then a barrier, then a weak load) reports nothing.
  Options: (i) implement the buckets of `Detect` (§3: one entry per thread and
  (kind, strength, scope) key; litmus O6 (vi) as the test) — exact, more state per location; (ii)
  policy `none` for the paper's soundness claims and report the `generic` precision as a
  separate configuration — one flag, loses the RC1 precision. **Decided 2026-09-26:
  (i), buckets**, in T9 together with I1 and I5; policy `none` is not a paper
  configuration.
- **D7** (T3b/T6): exit records. `hb_proof.tex` §1 and §7 (I3) take route (a) of T3b —
  emit per-warp exit records into `hb_events`, subtract exited threads from the expected
  count in the model, and turn A3 from an assumption into a checked property.
  **Decided 2026-09-26: (a)**, plus the end-of-kernel `pending_barriers` check
  (proof §1, fifth monitor check) in T3b.
- **D8** (the paper; `hb_proof.tex` §5) — **resolved 2026-09-26: three verdicts.**
  ORDERED keeps its meaning "in every schedule" (granted only by R1/R2/R3 or by the
  barrier-only clock); RACE means "unordered in this execution" (`hb_races`, the
  theorems apply to it); what lies between is LATENT — a third verdict, reported,
  counted as neither TP nor FP, evaluated on its own. Vector-clock mode's Race ∪ Latent
  is scalar-clock's Race plus the vetoes (T9-0 confirmed this on 557/558 programs), so
  the T9 Part 2 superset argument stands. The census showed that after I1 and I4 the
  tier's own content is the rtraw kind (ordered in this run only by a fenced lock
  hand-off whose order the program does not force): one paragraph and a case study in
  the paper, confirmed by re-recording in the other acquisition order where possible;
  not a headline. Rationale and numbers: `hb_proof.tex` §5 "The latent tier",
  `eval/LATENT_CENSUS.md` §8.
- **D9** (T10) — **decided 2026-09-29: adopt the token rule.** A load or store is strong
  at the scope its `.STRONG.<scope>` token names, generic and address-spaced alike; the
  compiler emits the same instruction for `volatile` and `ld/st.relaxed.sys.global`, so no
  sidecar can separate them on facts. Atomicity stays the opcode's. `generic` remains as the
  code path for pre-T10 sidecars, not as a paper configuration (its numbers under ScoRD's
  notion equal `token`'s by construction).
- **D10** (T11): default of `YOSEMITE_HB_STRICT` in `HbClock` once the TV checks also
  run offline. Recommended: keep strict on by default unless T11's measurement shows it
  above a few percent of `HbClock`'s time. Default if unanswered: keep on.
- **D12** (T9, decided 2026-09-27): R2 decides the DR/SC class of a candidate pair and
  grants no verdict; ORDERED comes from R1, R3 and the barrier-only clock only, vetoed by
  `hb_races`; `model_bug` from R1 alone. Traded: scalar-clock mode reports every
  barrier-unordered strong–strong pair R3 cannot certify as `sc` (informational), in
  exchange for `sc` existing at all, `model_bug` staying a defect detector, and one
  semantics for both modes (`hb_proof.tex` §5).
- **D13** (T5b/T12, decided 2026-09-27): T5b directly after T9, T12 in parallel — the
  barrier-only timeout programs need T5b regardless of the gate.
- **D14** (T9, decided 2026-09-27, with Yanbo Zhao): local memory is excluded from the HB
  trace and the model rather than keyed per thread; the collector's tag stays as is.
- **D15** (A2, decided 2026-09-28): for the submission, A2 stays an assumption of the
  trusted base, stated as "the collector records at issue; A2 holds when RMW windows on a
  location do not overlap", with the measured rate (T13 step 4 on the litmus; an offline
  window count over the kept dumps if T13 finds the rate is not negligible) and the one
  affected verdict footnoted. If the count is material, a report-level flag
  (`a2_uncertain`: a DR whose only missing ordering is a chain edge between two RMWs
  with overlapping windows) is added as its own informational column, like `latent`
  and `sc`. The real fix — atomics recorded after execution with the value read, which
  pins coherence order — needs an after-instruction hook the Sanitizer patching API
  does not have; T13 tests it on NVBit; a collector on it is post-submission (it would
  force a full re-evaluation). **T13 (2026-09-28): feasible; NVBit saw 0–4 % inversions.
  T14 (2026-09-29): the Sanitizer's own rate on the same lock is 11 / 32 / 28 % at
  2 / 4 / 16 warps — this is the rate to quote; the flag is built and moves no verdict;
  outside the ScoR applications no reported pair depends on A2. T15 (2026-09-29): the late
  key cuts inversions ~12 % and is not adopted; the rate is schedule-determined (range
  0–32 % across builds and contention on one lock) and the NVBit gap is unexplained, so
  the paper quotes the range and the corpus statement: after T10 no Race-alone verdict on
  558 programs depends on A2. The certain clock (T16) is the sound operating point
  available without values.**
- **D16** (T16): whether the tables carry a third operating point, "Race (sound)" — the
  reports under the certain clock (chain edges accepted only when the RMW windows do not
  overlap), a superset of the execution's races under A2w by Lemma "Monotonicity". Cost:
  one column, completeness lost on contended hand-offs (the flagged population). Small,
  no GPU. Recommended: yes — it is the cleanest sentence the paper can make about the
  execution. Default if unanswered: build it behind a switch, report the column, decide on
  the numbers.
- **D17** (T17): the replacement name for `HbEngine`. Proposal `VectorClockAnalysis`
  (parallel to `PcDependency` in the same file); alternative `HbVectorClock` with
  `HbScalarClock` for `barrier_only_pairs`, symmetric with the docs. Jeffery's advisor
  asked for the rename; the paper never names the class. **Decided 2026-09-30: `HbClock`**,
  distinct from T5b's `VClock` (the clock value type it owns); derived names fixed:
  `hb_clock_*` / `HbClock::emit`, the `HB_STATS` object `hb_clock`,
  `setup/hb_clock_timeout_ids.txt` (old name a symlink), test names "HbClock ==
  specification"; `YOSEMITE_HB_NO_ENGINE` retired, not renamed (after T4 the scalar clock
  runs inside `HbClock` too).
- **D11** (T12, tables): a labelled-clean program the gated detector reports because one
  side of a hand-off has no fence of sufficient scope is a PTX race by the letter. Policy:
  report it, footnote it with the PTX reason and any agreeing baseline, do not relabel the
  suite. **Cases so far (2026-09-30):** `reduction-norace` (ticket `atomicInc`, no acquire
  after it; iGUARD agrees); the five `norace_*fence*` litmus (consumer spins on the flag
  with no fence after it: `hrd-indirect` a DR, four SC; no baseline reports them —
  footnote (9) in `make_tables.py`). All go in the stale-label table of D2's amendment
  under "labels PTX contradicts".

---

## C. Task briefs

### T0 — Storage: BeeGFS as the only trace store, and what the "keep all" run lost
Branch `infra/beegfs-store`. Model: Sonnet. Needs the login node, one `rtx4060ti16g`
node and one `normal` node (`srun --pty`). First task; every later GPU sweep depends on
it.

What the harness does today (read from the code, not observed on the cluster):
1. Only one sweep ever pointed the store at BeeGFS: `eval/baselines/setup/p_evcand.sh`
   (`BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/evcand`). Every other sweep —
   `p_rerun.sh`, `p_keep.sh`, `p_fpfix_eng.sh`/`p_fpfix_tr.sh`, the P7/P9 re-runs — sets
   `BASELINE_TRACE_DIR=/mnt/local/$USER/cvtraces` (node-local disk, 230 GB on c37 with
   201 GB taken by other users) and, where `/mnt/local` is root-owned (c2), falls back to
   `/tmp/$USER/cvtraces` on the node's root filesystem. Every `No space left on device`
   / `trace-disk-full` row in `eval/BASELINES.md` §1b and the lost
   `memcpy_htod_kernel_race-fixed` row are node-local scratch, not BeeGFS.
2. The one BeeGFS sweep ran `--keep-all --keep-all-cap-gb 20`. `_cap_kept()`
   (`eval/baselines/parallel.py:485-499`) **deletes** a program's kernel JSONs when they
   exceed the cap and only writes `trace_dropped` into that program's `meta.json`; the CSV
   row does not say so. The largest traces (P7/P9 apps at 93–113 GB, the P1 `cc_vertex_data`
   1296n engine dumps) were therefore discarded by the harness, not refused by BeeGFS.
   The home copies made by `--keep-mismatch` drop kernel JSONs above `--keep-cap-mb`
   (100/300 MB) the same way (`_keep_trace`, `:425-451`, reason `trace-too-large`).
3. `_store_root()` (`:51-79`) with `BASELINE_TRACE_DIR` unset falls through silently:
   `/mnt/beegfs/$USER` (skipped on any `OSError` from `makedirs`/`chmod 0o700`, e.g. an
   admin-created root-owned directory or an unmounted FS) → `/mnt/local/$USER` →
   `$ACCEL_PROF_HOME/eval/results/traces` in home (40 GB quota). The "persisting every
   trace overflowed the 40 GB home quota (11 GB for 117 programs)" incident quoted in
   `cmd_run`'s docstring (`:541-550`) is this fallback landing in home.
4. A timed-out rep's raw dump is deleted immediately (`_clean_deps`, `:207-209` and
   `:259`), so TIMEOUT programs never keep their partial dump; and a saved program
   transiently needs 2× its dump on the store (raw `dependency_*` dir plus the
   `shutil.copy` into `<id>/<mode>/`, `:211-215`, `:257`).
5. The code assumes BeeGFS is mounted on compute nodes only (`:61`, and the comment in
   `p_evcand.sh`). Unverified.

Steps
1. Verify the filesystem, on the login node and on one node each of `rtx4060ti16g` and
   `normal`: `mount | grep -i beegfs`, `df -h /mnt/beegfs`, `beegfs-ctl --getquota --uid
   $(id -u)` (and `--gid`), `ls -ld /mnt/beegfs/$USER`; a 20 GB `dd` write and a
   100 000-small-file write (`kernel_*.json`-sized) with timings; delete both. Record
   throughput, whether a quota exists, and on which nodes the mount is present.
2. Inventory the existing stores: `du -sh /mnt/beegfs/$USER/cuvein_traces/*`; every
   `meta.json` whose `trace_dropped` is set, whose `keep_reason` contains
   `trace-too-large`, or whose `modes.<mode>.saved` is false; `STORE_INFO.json` of each
   store. That list is the answer to "what failed".
3. Make BeeGFS the only store: `_store_root()` fails loudly instead of falling through to
   home; every `p_*.sh` exports `BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>`
   (never `/mnt/local`, never `/tmp`); `--keep-all` becomes the default with
   `--keep-all-cap-gb 0` meaning no cap (already true in `_cap_kept`); make
   `--keep-cap-mb 0` mean unlimited in `_keep_trace`; keep a timed-out rep's partial dump
   under `<id>/<mode>-partial-rep<k>/` (marked, never read as a verdict) instead of
   deleting it; `_save` moves instead of copies on the same filesystem; write `meta.json`
   before collection starts so a SIGKILLed shard leaves a readable marker.
4. Run the CPU analysis phase on `normal`/`max` reading BeeGFS (no GPU): add
   `setup/p_analyze_cpu.sh`; confirm `parallel.py analyze` never calls
   `blib.resolve_cuda_home()` (it does not today).
5. Since BeeGFS is not backed up, mirror each store's `STORE_INFO.json` and all
   `meta.json` files into `eval/baselines/store_index/<tag>/` in home (small), so a lost
   store is at least inventoried.
6. Re-collect the programs from step 2 into `cuvein_traces/full-<date>/` (both modes, no
   caps, 20-minute cap for P7/P9) on `rtx4060ti16g`, and confirm every `meta.json` shows
   both modes saved or an explicit partial/timeout marker.

Deliverable: `eval/STORAGE.md` (mount/quota facts, the dropped-trace inventory, the
policy, the exact commands) and a "Storage" paragraph in `eval/README.md`. Acceptance: a
`--keep-all` run of five programs including one whose trace exceeds 20 GB lands complete
on BeeGFS; `parallel.py analyze` of that store from a `normal` node reproduces the GPU
phase's verdicts; no `p_*.sh` references `/mnt/local` or `/tmp` any more.

### T8 — Rename the two modes, persisted strings included (todo 8)
Branch `rename/clock-modes`. Model: Sonnet. No GPU. After T0 (the converter must reach
every store).

Goal: **scalar-clock mode** replaces trace-only / no-engine, **vector-clock mode**
replaces engine mode — everywhere, including persisted strings (decision D3). One
release of compatibility *reads* (with a stderr warning) remains so that a store the
converter did not reach can still be re-scored; nothing writes the old names any more.

| what | old | new |
|---|---|---|
| collector env var | `YOSEMITE_HB_NO_ENGINE` set (`pc_dependency_analysis.cpp:775,779,1488,1493`) | `YOSEMITE_HB_MODE=scalar-clock` \| `vector-clock` (default `vector-clock` when `YOSEMITE_HB_TRACE=1`); the old variable still honoured with a deprecation warning |
| setters | `getall.sh`, `eval/driver.py`, `eval/baselines/blib.py`, `eval/baselines/parallel.py`, `python/scale_harness.py`, `eval/harness.sh` | export `YOSEMITE_HB_MODE` only |
| `eval/driver.py` | `--no-engine`, `--csv-suffix=-noengine`, `--detail-suffix` | `--mode scalar-clock\|vector-clock`; default suffix `-scalar-clock` |
| `run_cuvein.py --mode`, `$BASELINE_MODES`, `parallel.py` `MODES` | `engine,trace-only` | `vector-clock,scalar-clock` |
| CSV `mode` values (`blib.py:47-51`) | `engine`, `trace-only` | `vector-clock`, `scalar-clock` |
| CSV `oracle_verified` (`aggregate.py:137,170-171`) | `no-engine` | `scalar-clock` |
| CSV `notes` text (`driver.py:222,234`) | `mode=trace-only(no-engine)`, `no-engine-output(rc=…)` | `mode=scalar-clock`, `scalar-clock-output(rc=…)` |
| result files | `eval/results/E*-noengine.csv`, `E*-fixed-noengine.csv` | `E*-scalar-clock.csv` (`git mv`) |
| kept-trace layout (`parallel.py:224,257`) | `<id>/engine/`, `<id>/trace-only/`, `logs/engine_rep1.txt` | `<id>/vector-clock/`, `<id>/scalar-clock/`, `logs/vector-clock_rep1.txt` |
| confirm files (`run_cuvein.py:169-170`, `parallel.py:401-402`) | `<id>__cuvein__engine.json`, `"mode"` field | `<id>__cuvein__vector-clock.json` |
| `STORE_INFO.json` `modes` | `["engine","trace-only"]` | new names |
| `classify_fp_causes.py:99` (hard-coded `engine/`), `classify_residuals.py`, `make_tables.py` (`MODES`/`COLNAME`/`MATRIX_NAME`, lines 26-30, 767-778), `compare_fpfix.py` | old literals | new literals; render `cuVein (vector-clock)` / `cuVein (scalar-clock)` |
| `scale_harness.py` output fields | `engine_races_dedup`, `t_dump_engine_s`, `engine_eq_oracle`, … | `vector_clock_*` |
| tests | `test_scor_microbenchmark_trace_only`, `test_trace_only_verdict`, `_trace_only_copy` | `*_scalar_clock` |
| prose | `eval/README.md:62-68`, `eval/REPORT.md`, `eval/FIX_REPORT.md`, `eval/FP_DIAGNOSIS.md`, `eval/BASELINES_SUMMARY.md`, `HARDENING_REPORT.md`, `roadmap.md:65-92`, `getall.sh:28-51`, docstrings in `sync_dominance.py`/`hb_oracle.py`/`pc_dependency_analysis.cpp` | new names |
| unchanged | `kernel_N.json` keys (`hb_events`, `hb_races`, `hb_races_sync_only`, …), `HbEngine`, `hb_engine_*`, `barrier_only_pairs`, `hb_class` values | not mode names |

Steps
1. Write `eval/baselines/migrate_mode_names.py`: idempotent, dry-run by default,
   `--apply` to execute, one log line per change. It rewrites the `mode`,
   `oracle_verified` and `notes` columns of every CSV under `eval/results/` (including
   `superseded_*`, `prefix_*`, `fpfix*`, `evcand*`), renames the `-noengine` files, renames
   the per-mode directories, log files and confirm files in every store passed on the
   command line (home `traces_keep*`, `confirm*`, and each BeeGFS store from T0's
   inventory — run it from a node where BeeGFS is mounted), and rewrites `STORE_INFO.json`.
2. Code and docs per the table. Readers (`make_tables.py`, `classify_*`,
   `compare_fpfix.py`, `parallel.py analyze`, `sync_dominance.py`'s `oracle_verified`)
   accept the old strings for one release and print one deprecation line per file.
3. Run the converter with `--apply` on home, then on BeeGFS; commit the migrated CSVs.
4. Regenerate `eval/BASELINES_SUMMARY.md` and `eval/BASELINES.md` from the migrated data
   and diff against the previous versions: identical up to the labels.
5. Green set; `make_tables.py`, `classify_fp_causes.py`, `compare_fpfix.py --before …
   --after-glob …` on the migrated data must run without touching the compatibility path.

Acceptance: `grep -rn "trace-only\|no-engine\|noengine\|NO_ENGINE\|engine mode"
--include=*.py --include=*.sh --include=*.md --include=*.cpp --include=*.h --include=*.cu .`
returns only the compatibility shim and its deprecation notes; the migrated tables are
identical up to labels; a fresh five-program run writes only the new names. Report: the
converter's log summary and the table diff in the merge commit body.

### T6 — The model, the algorithm and the proof: review and verification (todo 6) — done
**Done 2026-09-26/27** (8d1e36e on `design/algorithms`, `design/T6_REVIEW.md`, PR #4
merged). Kept for reference; the brief below is what was run.
Branch `design/algorithms`. Model: Opus, in a fresh context. No GPU except for the test
kernels of step (c). T8 is merged (use the names vector-clock / scalar-clock).

**There is one document, nine pages:** `design/proof/hb_proof.tex` (PR #4, branch
`docs/proof-inputs`). §1 the trace model (records with kind/strength/scope, exit records,
instances whose expected count subtracts exited threads, well-formedness W0–W3,
assumptions A1–A3, the five monitor checks); §2 happens-before with the fence gate as a
parameter (trusting gate = the implementation; the instance gate = `fenced(p, p', s)` on
the thread's own previous/next record pcs, replacing the per-pc gate of the 09-24 draft),
the DR/SC verdicts, monotonicity; §3 one
algorithm `Detect(T, M)` with `M ∈ {vec, sync}` — vector-clock mode runs both instances,
scalar-clock mode runs `sync` only — with per-(thread, key) buckets, chain clock, publish
before tick; §4 the proofs (assembly, chain clock, clock invariant, HB test, complete,
sound, the `sync` instance as a corollary, why one bucket per key); §5 the verdict layer
(Static = R1/R2/R3 with R3's release point from the trace, the five-row matrix with the
SC row and LATENT as a third verdict, what scalar-clock misses (a)–(c), the latent tier
as measured by T9-0);
§6 fidelity, MM1–MM3, the per-profile certificate; §7 the implementation at 3331d35 as a
table of seven substitutions I1–I7 with their cost, Proposition "Missed class of I1", the
`check_e1_e2.py` evidence, and the order of work. It supersedes `hb_oracle_proof_v3.tex`,
`hb_defs_v4.tex`, `design/algorithms.md`, `design/algorithms.tex`,
`design/proof/algorithm1_reference.md` and `design/proof/README.md`, which were removed
from the branch; do not resurrect them. `pdflatex` (packages `algorithm`, `algpseudocode`,
`caption`, `enumitem`, `hyperref`). Next to it, `design/proof/check_e1_e2.py` runs the real
`hb_oracle.py` over hand-made dumps of the I1 and I2 cases; its docstring records the output.

The document was written on 2026-09-24 and revised on 2026-09-26 with the census's
findings; it has run against `check_e1_e2.py` and, through T9-0, against the kept traces
of 558 programs (verdict layer only). **T6's job is review and verification, not
authoring.** In order:
- (a) Read §3 against the code (`python/hb_oracle.py`, `HbEngine` in
  `sanalyzer/src/tools/pc_dependency_analysis.cpp`, `python/sync_dominance.py` including
  `barrier_only_pairs`, `_hb_class`, `judge`) and confirm that the code is exactly
  `Detect` with substitutions I1–I7 of §7 and nothing else; list every line the code
  contradicts. Fix the document, not the code. Check in particular: that the code's order
  is acquire → check → tick → publish (I1); that its state is one last write + one read
  per thread, not buckets (I2); that `barrier_only_pairs` is `Detect(T, sync)` with the
  shared-base representation; and that §5's matrix is `_hb_class` (the full clock never
  grants ORDERED).
- (b) Read §4 as a referee, **time-boxed to one day**: every case of the clock invariant
  (exit, read/write, non-completing arrival, completing arrival or exit, RMW) and the
  certificate's matching lemma. Anything that does not follow is a finding to write into
  §4 or §6, not to gloss. The proof is not on the paper's critical path; the code is.
- (c) Write `design/algorithms_check.py`: a ~40-line simulator of `Detect(T, vec)` with
  buckets, and run it on the 33 litmus traces (through `analyze()` outputs, not the GPU):
  with substitutions I1 and I2 switched on it must equal `hb_oracle.py`'s race set on every
  one; with them off it is the reference. Then the real-kernel strict xfails:
  `test_write_after_unlock_other_schedule` (I1, the rtraw pattern with block 0 first,
  forced with a spin on a flag) and the kernel of Remark "Why one bucket per key" (I2),
  traced on one `rtx4060ti16g` node; and the local-memory check of I5 (one kernel with
  spills: say whether `(local, addr)` collides across threads on the real collector).
- (d) D7 is decided (route (a)); confirm only that §1's wording of A3 and the fifth
  monitor check are what T3b implements, or say what is off.
- (e) Check the 2026-09-26 edits for consistency with the rest of the document: the
  instance gate (Definition "Gate") is a predicate on records — confirm every use of
  `rel`/`acq` in §4 reads correctly with that (they are only ever evaluated at the record
  in question, and the online deferral of the acquire join in §3 is exact); the SC row of
  the §5 matrix against `_hb_class` (today SC is dropped, so the row is dormant until
  T9); the R3 release-point amendment against `HBGraph.chain` (is the release point
  today region dominance? is there a write-before-lock check? T9-0 §4 says the former
  declined 23 race-free pairs); the fifth monitor check against `kernel_trace_flush`.

Acceptance: a fresh context reads only §3/§7 and the code and finds no statement the code
contradicts; the simulator matches `hb_oracle.py` on the 33 litmus traces with I1/I2 on;
the I1/I2 test files exist as strict xfails and the green set is otherwise unchanged.
Report: extend the *Status and scope* paragraph at the head of `hb_proof.tex` with what
was checked, by whom, on which revision, and the corrections made; commit on the branch
and open the merge of PR #4.

### T3 — crs-cuda: the HeCBench case SuperCollider calls race-free (todo 3)
Branch `triage/crs-cuda`. Model: Opus (+ Explore subagents). GPU: yes.

Context: in `eval/BASELINES.md` §P9 (line 5425) `crs-cuda` is the only P9 program where
cuVein reports (vector-clock 155 reports, scalar-clock 7) while SuperCollider's label and
run say race-free; racecheck (shared memory only) and iGUARD say CLEAN. The summary
attributes the vector-clock verdict to "pair mis-attribution in the engine + plain
conflicting accesses that did race in the run" and the scalar-clock one to "latent
report on a barrier/lock idiom". The question is whether this is a real race
SuperCollider missed (its HeCBench labels are the paper's flags, not an oracle —
`BASELINES_SUMMARY.md` footnote 6) or a cuVein false positive, and which class.

Steps
1. Locate the kept trace and confirm JSON: `eval/baselines/traces_keep*/P9-crs-cuda/`
   (per-mode dirs, `dots/`, `meta.json`) or the BeeGFS stores from T0's inventory, and
   `eval/baselines/confirm*/P9-crs-cuda__cuvein__*.json`. If the trace was not kept
   (the pre-T0 300 MB cap), re-run the program once per mode with `parallel.py run --id
   P9-crs-cuda --keep-all` under the T0 store.
2. Re-analyze the kept dumps with the **current** detector (the P9 row may predate the
   event-candidate change): `parallel.py analyze` into a scratch results dir; run
   `eval/triage.py` on the detail JSON; tabulate reports by (kernel, pc pair, space,
   race_type, hb_class, event_candidate, chain).
3. Attribute each report to source: the HeCBench binaries were built with `-lineinfo`;
   use `nvdisasm --print-line-info` on the extracted cubin to map pcs to
   `src/crs-cuda/*.cu` lines. Read the kernel(s).
4. For every distinct pc pair decide, with evidence: (a) genuine race (two threads,
   conflicting, no barrier/lock/atomic ordering in the source) — then also say whether
   it is a data race or an unordered strong conflict under the two-verdict definition;
   (b) ordered in every schedule by something the detector cannot see (fence-gated
   handoff, warp lock-step, `cp.async` wait — F4 makes cp.async users a false-positive
   risk, `FIX_REPORT.md:152`) — then name the mechanism and which rule should have
   caught it; (c) a detector bug — then a minimal failing test.
5. If (a): write a ≤40-line reproducer kernel `python/testdata/crs_pattern.cu` that
   isolates the pattern, confirm cuVein reports it and racecheck/iGUARD do not, and note
   why SuperCollider's redundant-read detection cannot see it. If (b) or (c): open the
   fix as a proposal (do not implement heuristics).
6. Cross-check the "did race in the run" claim: the vector-clock `hb_races` entries carry
   `a_tid`/`b_tid`; verify the two threads are in different warps/blocks as the source
   implies.

Deliverable: `eval/CRS_CUDA_TRIAGE.md` with the table, the source mapping, the verdict
per pair, and a one-paragraph statement suitable for the paper. If the label is wrong,
add a footnote hook in `make_tables.py` (do not silently change the P9 label).

**Outcome (merged d8eb112, 2026-09-23):** crs-cuda is race-free; every cuVein report
(155 vector-clock, 7 scalar-clock) came from exit-unaware barrier assembly — threads that
return before a `__syncthreads()` never arrive, the instance never completes, and every
store → barrier → load pair on `shared_data` stays unordered. Reproducer
`python/testdata/barrier_exited_threads.cu`, strict xfails in
`python/test_barrier_exit.py`; a TV scan of every kept store shows only crs-cuda's
verdict depends on it. The fix is T3b.

### T3b — Exit-aware barrier instance assembly (todo 3, the fix)
Branch `fix/barrier-exit-count`. Models: Sonnet (implementation), Opus (review). GPU:
crs-cuda fresh trace on `rtx4060ti16g` + the green set. Route (a) is decided (D7) and
the proof already contains it (revision 09-26/27, confirmed by T6 step (d)): Definition
"Instances" subtracts exited threads for whole-block instances, Lemma "Assembly" has
`exited_β`, A3 is a statement about the hardware. The code at 3331d35 drops the
collector's `BlockExit` records from `hb_events` (`hb_collect_events`,
`pc_dependency_analysis.cpp:961-962`) and uses `expected = thread_count or block_tc`.

Steps
1. Emit exit records into `hb_events`: the collector already produces
   `MemoryType::BlockExit` per warp with the exiting lanes (`BlockExitCallback`,
   `gpu_patch_pc_dependency.cu:215-249`, the same shape as an arrival — no new device
   code, only serialization); give them `type: "exit"` with block/warp/lane mask. The
   model subtracts exited threads from the expected count of every later **whole-block**
   instance of that block (count 0); a counted barrier keeps `expected = n`.
2. Implement identically in `HbEngine`, `python/hb_oracle.py` and
   `sync_dominance.barrier_only_pairs`; keep the TV monitor consistent (an exited thread
   arriving later is a TV violation; `TV-barrier-completion-order` must not fire for
   exited warps). Add the fifth check of the proof's §1, `TV-barrier-pending-at-end`
   (non-empty `pending_barriers` at the end of the kernel): in the engine it runs before
   `HbEngine::emit`, which is where `tv_violation` is written (`kernel_trace_flush` calls
   it through `hb_engine_emit`, `.cpp:1334`); `pending_barriers` is maintained regardless
   of `YOSEMITE_HB_STRICT`, so the check does not depend on strict. In scalar-clock mode
   the engine never runs (`.cpp:1036,1875`), so the check exists only offline: add it to
   `barrier_only_pairs` (which has no TV code today — the minimal form here; T11
   unifies). Old dumps without exit records keep today's behaviour (a dump-level marker,
   as T1a did with `hb_async`).
   Before changing anything, grep the kept crs-cuda `kernel_*.json` for `tv_violation` and
   say whether `TV-barrier-completion-order` fired there today — by W2 it should have
   (released warps issue post-barrier loads while the modelled instance is pending); if
   it did not, the per-warp `warp_waiting` row missed a genuine violation and that is a
   finding for T11.
3. Turn the strict xfails of `python/test_barrier_exit.py` into passing tests; add the
   positive control (a thread that exits *after* the barrier still counts).
4. Record crs-cuda afresh on a GPU with the new collector (a kept dump has no exit
   records, so no re-score can reach CLEAN): expected CLEAN in both modes, 0 TV
   violations, and `TV-barrier-pending-at-end` silent; then re-score the kept stores with
   the new oracle to confirm that dumps without exit records keep their verdicts (none
   should move). Green set unchanged.
5. Proof: nothing to add — update §7's I3 row to "matched" with the commit, and the
   monitor sentence of §1 if the offline placement differs from what it says.

Deliverable: `eval/CRS_CUDA_TRIAGE.md` §"Fix"; the P9 crs-cuda row regenerated.

### T2 — Host-memcpy (`cudaMemcpyAsync`) races: evidence, model, prototype (todo 2)
Branch `feat/host-memcpy`. Models: Sonnet (investigation + prototype), Opus (model
review). One GPU node for the runs.

Why this is not out of reach (the answer to D5's question): the collector already
intercepts every host `cudaMemcpy*`. `SANITIZER_CB_DOMAIN_MEMCPY` is enabled
(`nv-compute/src/compute_sanitizer.cpp:1307`) and `SANITIZER_CBID_MEMCPY_STARTING`
(`:1189-1211`) forwards (dst, src, size, `isAsync`, direction H2D/D2H/D2D/H2H, device)
through `yosemite_memcpy_callback` (`sanalyzer/src/sanalyzer.cpp:177-183`) as a
`MemCpy_t` event to every tool. `PcDependency::evt_callback`
(`pc_dependency_analysis.cpp:1567-1577`) simply has no case for it. The GPU architecture
is not the limit either: the `asyncmemcpy/*` tests build and ran on sm_86/89 and failed on
trace volume, not on capability. What is missing is a *model*: a host memcpy is an access
by a stream agent, ordered against kernels by stream order and events rather than by
in-kernel synchronization — and the engine currently resets its state per kernel launch.
The same mechanism covers `interkernel/*` (two kernels on different streams). The
in-kernel `cp.async` (LDGSTS) path is unrelated to this (`MemcpyAsyncCallback`,
`gpu_patch_pc_dependency.cu:141-150`, global READ + shared WRITE at one pc; handled by
T1a); no `cp.async` variant copies from host memory, so "cp.async H2D" is answered by
this task as: the H2D case is the host API, and it is reachable.

Steps
1. Evidence: run `memcpy_htod_kernel_race` and `kernel_memcpy_dtoh_race` (racy and fixed,
   `eval/baselines/bin/P6`) with the collector's `PRINT` of the memcpy callback enabled and
   record: the `Sanitizer_MemcpyData` fields (does it carry `stream`/`hStream`? — check
   `sanitizer_callbacks.h` in the toolkit), whether it fires at API-call time, and its
   position relative to `SANITIZER_CBID_LAUNCH_BEGIN`/`LAUNCH_END` of the racing kernel.
   Also list the stream/event synchronisation callbacks the Sanitizer API offers
   (`SANITIZER_CB_DOMAIN_SYNCHRONIZE`, events domain) — these are the HB edges of the
   host side.
2. Model (write it down before coding, in `design/host_memcpy_model.md`): a virtual agent
   per stream; a memcpy is one range access (WRITE over `[dst, dst+size)` for H2D/D2D
   destination, READ over the source for D2H/D2D); kernel launches are ordered after
   earlier work on the same stream and after events they wait on; two operations on
   different streams with no event/sync between them are concurrent. A kernel access
   races a memcpy iff the address lies in a range of an agent that is concurrent with the
   kernel's stream position. State the assumptions (pageable-host `cudaMemcpyAsync`
   staging; the default stream's legacy synchronisation; `cudaDeviceSynchronize`).
3. Prototype behind `YOSEMITE_HB_HOST_MEMCPY=1`, additive: `EventType_MEM_CPY` case in
   `evt_callback` recording the range + stream + a host sequence number; an interval set
   in `HbEngine` checked once per *location* on first access in a kernel (not per event —
   the `last_write` map already gives that hook), mirrored in `hb_oracle.py` from a new
   `host_ops` array in `kernel_N.json`; the static leg is untouched (a memcpy has no pc).
   Kernel-vs-kernel across streams is the same interval logic applied to the previous
   kernel's location shadow — prototype only if the memcpy part lands cleanly.
4. Volume: the two shipped tests are 2.6e8 / 1.3e10 accesses and time out for that
   reason alone. Add a reduced-size build (`build_cuhadron.py --small`, sizes as a
   compile-time define — say so in the manifest) or a 30-line micro test in
   `python/testdata/host_memcpy_race.cu` (racy: memcpyAsync on stream A while a kernel
   on stream B reads the buffer; fixed: `cudaStreamWaitEvent`). Verdicts: racy → RACE,
   fixed → CLEAN, both modes; engine == oracle.
5. Cost: with the flag on, run five P6 programs and confirm no verdict or timing change
   outside the new cases.

Deliverable: `design/host_memcpy_model.md`, `eval/HOST_MEMCPY_STUDY.md` (evidence, sizes,
results), the prototype behind the flag, the micro test. The decision to enable it by
default and to re-label the cuHadron `asyncmemcpy`/`interkernel` rows is D5.

### T1a — Apply the designed cp.async fix (todo 1, part a)
Branch `feat/cp-async-wait`. Models: Opus (design check), Sonnet (implementation), Opus
(verifier in a fresh context). GPU: yes, rebuild of `nv-compute` + `sanalyzer`.

The design is written in `eval/FIX_REPORT.md:138-165` (F4). Root cause: the LDGSTS
shared write is recorded as a synchronous store by the issuing lane, and the wait
(`DEPBAR`) is not instrumented, so racy and fixed builds of
`cuHadron/memcpy/shared_readwrite_race` produce identical traces. Expected effect: racy
→ 1 RAW, fixed → 0, E6a agreement 9/9.

Steps
1. Confirm the instruction ids in the installed header
   `$CUDA_HOME/compute-sanitizer/include/sanitizer_patching.h` (not vendored): the value
   of `SANITIZER_INSTRUCTION_PIPELINE_WAIT`, the callback signature, and list every
   enumerator so T1b can reuse the list. Record the header version.
2. Collector: register PIPELINE_WAIT for the `pc_dependency_analysis` tool only
   (`compute_sanitizer.cpp:275-294`); add `PipelineWaitCallback` via `EmitSyncEvent`
   (`gpu_patch_pc_dependency.cu:155-180`); add `MemoryType::PipelineWait` and an
   `ASYNC_COPY` bit on the LDGSTS shared write (`gpu_patch.h:12-35`, note `flags` is
   overloaded for barriers — pick a bit that cannot collide). Serialize both in
   `hb_collect_events` (`pc_dependency_analysis.cpp:686-730`): new event type
   `"pipeline_wait"` and a boolean `"async": true` on the write; old readers must ignore
   unknown fields.
3. Engine + oracle (same commit): attribute an async write to the virtual agent
   `t | ASYNC_BIT`. `tid_of` packs `(block << 10) | (warp << 5) | lane`
   (`hb_oracle.py:48-49`), so the block id occupies bits ≥ 10 with no fixed width —
   use a high bit no block id can reach (e.g. bit 62) and give `hb_races` entries an
   `"async": true` field with the issuing thread's id instead of leaking the virtual
   id into reports. On the thread's wait event `join_into(vc[t], vc[async(t)])`. Decide
   and document what the async agent's clock is at issue time (it must be ≥ the issuing
   thread's clock so the write is ordered after the thread's pre-issue accesses). Mirror
   in `barrier_only_pairs` (scalar-clock mode) — an async write must not be treated as
   the thread's own.
4. Static leg: `DEPBAR`/`LDGDEPBAR` become non-qualifying sync nodes with an
   `async_wait()` ordering source in `HBGraph`; the `0x90←0x70` edge must no longer be
   dropped as `intra_thread_only` when the writer is async.
5. Tests: `python/testdata/cp_async_wait.cu` with the read-before-wait and
   wait-before-read variants; assert racy → RAW, fixed → 0 in both modes; engine ==
   oracle; add to the green set. Tripwire from the design: if PIPELINE_WAIT does not fire
   for `DEPBAR.LE` on sm_86/89, the fixed build reports a race — then stop and report.
6. Re-run E2 memcpy/* (`eval/manifests/e2_fix.json`) and the P6 rows in both modes; run
   the green set; report verdict deltas.

Acceptance: F4 case caught, no other E2/P5/P6 verdict changes, green set passes, default
tool path byte-identical (diff a `pc_dependency_analysis` run without `YOSEMITE_HB_TRACE`
before/after). Report: `eval/CP_ASYNC_REPORT.md`; update the F4 row of
`eval/FIX_REPORT.md`.

### T1b — cp.async.bulk / TMA / distributed shared memory (todo 1, part b)
Branch `feat/cp-async-bulk`. Model: **Fable** for design and implementation — this is
the most complicated task in the queue (three completion mechanisms, a new location
space for distributed shared memory, collector + `HbClock` + oracle + static leg touched at
once); a fresh Fable context reviews and verifies. GPU: the `h100` partition (node c29,
sm_90; single node, 8-day limit, often busy — submit early, `sbatch --partition=h100`).
After T1a.

Steps
1. Build for sm_90 on c29: extend `eval/build_cuhadron.py` with `--arch sm_90` so the
   `bulkcpy` and `dsmem` categories (8 targets, `eval/baselines/setup/manifest.evcand.csv`
   rows 67-78, currently `[needs-sm90]`) are built; rebuild `nv-compute` for sm_90 as
   well (fatbin arch list). Confirm the collector's default path runs on H100 unchanged
   (one plain `pc_dependency_analysis` run, no HB) before touching anything.
2. Find out what fires: with T1a's enumerator list of `sanitizer_patching.h`, run the
   racy `bulkcpy/shared_readwrite_race` under `YOSEMITE_HB_TRACE=1` with a temporary
   catch-all patch (every `SANITIZER_INSTRUCTION_*` id registered to a counting
   callback) and record which ids fire for `UBLKCP`, `UTMALDG`, `SYNCS.*`
   (mbarrier ops) and `cp.async.bulk.commit_group/wait_group`. Also dump the SASS
   (`nvdisasm`) so `sync_dominance.classify` can learn the opcodes (unknown sync opcodes
   currently exit 2 — keep that tripwire, add the new tokens deliberately).
3. Design note `design/cp_async_bulk.md` (before implementing): the three completion
   mechanisms — bulk-group `commit_group`/`wait_group` (same shape as T1a's virtual
   async agent), mbarrier `complete_tx`/`try_wait` (the completing wait is on a barrier
   object: the async agent's clock joins the waiting thread at its successful
   `try_wait`; a `mbarrier.arrive` by other threads is a release on that object), and
   `shared::cluster` destinations (distributed shared memory: a location key that carries
   the cluster and the target CTA; thread ids of other CTAs in the cluster become valid
   conflict partners). If step 2 shows the Sanitizer exposes no patch point for one of
   them, say which and what a `%globaltimer`/NVBit alternative would cost; do not
   approximate.
4. Implement in serializer, `HbClock`, oracle, `barrier_only_pairs` and the static leg,
   gated by the instruction type only (no env flag — sm_86/89 binaries never emit these
   records). Tests: the 8 cuHadron targets (racy → RACE, fixed → CLEAN, both modes,
   `HbClock` == specification) plus a `python/testdata/cp_async_bulk.cu` micro test with mbarrier
   completion; E6a racecheck on the shared-memory cases for an independent check.
5. Evaluation rows: add the 8 targets to the P6 manifest with `arch=sm_90`; per D4, run
   racecheck, iGUARD (`make ARCH=sm_90`) and SuperCollider's own binaries on c29 so the
   cuHadron row of the matrix no longer carries `[needs-sm90]`.
6. Optional: compile the same tests for sm_120 and run on one `rtx5060ti16g` node to see
   whether non-cluster bulk copies work there (a second architecture for sweeps).

Deliverable: `design/cp_async_bulk.md`, the implementation, tests, the new matrix cells,
`eval/CP_ASYNC_REPORT.md` §"bulk". Acceptance: 8/8 cuHadron sm_90 targets correct in
both modes, `HbClock` == specification, green set unchanged on sm_89.

### T5a — Memory-footprint overhead (todo 5, measurement)
Branch `study/memory-footprint`. Model: Sonnet. GPU: three profiling runs.

Steps
1. Table from existing data, no GPU: per suite and mode, peak RSS (`peak_mb` in
   `eval/results/baselines-cuvein*.csv`, `peak_mem_mb` in `eval/results/E*.csv`) as
   min / median / geomean / max, against the sanitizer floor (~818 MB, `eval/REPORT.md`)
   and native RSS where recorded; include the OOM/TIMEOUT rows from
   `eval/baselines/setup/engine_timeout_ids.txt` with their last observed RSS. Put it in
   `eval/MEMORY_FOOTPRINT.md`; add the same table to `make_tables.py` so it regenerates.
2. Attribute the vector-clock engine's memory: add `YOSEMITE_HB_STATS=1` that prints at
   kernel end the sizes of `vc` (sum of clock entries), `released` (count and summed
   clock entries), `last_write`, `last_reads` (summed readers), `pending_barriers`,
   `_hb_events` (bytes), and `vs` bases (unique). Zero cost when unset. Run on
   `python/testdata/scale/tiled_gemm` N=256 (oracle 8.2 GB known), one ScoR app, and the
   Indigo3 `cc_vertex_data` 1296n program that reached 113 GB (`FP_DIAGNOSIS.md:225-232`),
   with a wall-clock cap. Also record `_hb_events` RAM vs JSON size on disk (the dump is
   held in RAM for the whole kernel: `pc_dependency_analysis.h:327`, written in
   `kernel_trace_flush`).
3. Confirm or refute the O(threads²) explanation from the numbers (`sync_group` copies
   the joined clock into every participant, `pc_dependency_analysis.cpp:154-158`; every
   release copies a full clock, `:359`).

Deliverable: `eval/MEMORY_FOOTPRINT.md` with the tables, the attribution, and the
projected effect of T5b; the `HB_STATS` hook merged (it is needed again by T5b/T4).

### T9-0 — Latent census (done 2026-09-26)
Branch `study/latent-census`, report `eval/LATENT_CENSUS.md`, script
`eval/baselines/latent_census.py` (`collect` from the BeeGFS stores on `normal` nodes,
`tables` on the login node). Measurement only; the detector was not changed. Its numbers
are cited in `hb_proof.tex` §5/§7, B2's status paragraph and D8; re-run `tables` after
T9 and T12 to report the moves. Merged (3ed5c9c).

### T9 — Vector-clock soundness: I1 + I2 (both clocks) + I5 (exclusion), R2 as class, the `sc` column (todo 9)
Branch `fix/publish-then-tick`. Model: Opus (Parts 1–2, review), Sonnet (Part 3
implementation), Sonnet subagent for the re-score script. T6 is done
(`design/T6_REVIEW.md` is the deviation table); D1, D6, D12 and D14 are decided. Part 4 of the earlier brief is done: `eval/LATENT_CENSUS.md`
(T9-0) is its result and is cited, not redone.

Terminology, as fixed in `hb_proof.tex` (the verification
convention): **sound** = misses no race (no false negatives), **complete** = every
report is a race (no false positives). Todo 9 is a **soundness** question. The fix in
question is the pair of changes from `FP_DIAGNOSIS.md` addendum 2 (2026-09-20):
event-stream candidates (`sync_dominance.py:740-749`, judged at 883-904, knob
`CUVEIN_EVENT_CANDIDATES`) and the CAS past-release gate (`_past_release`,
`sync_dominance.py:371`, knob `CUVEIN_R3_PAST_RELEASE`). They let scalar-clock mode
catch `race_interblock_none-lock_rtraw`, whose racing pair has no dependency edge
(edges keep only the last accessor). Question: does vector-clock mode still miss no
race — in particular, does it catch every race the scalar-clock mode now catches?

Start from `design/proof/hb_proof.tex` (PR #4) as reviewed by T6: §7 already states the
two soundness gaps (I1 tick-before-publish with the exact missed class `R_miss`; I2 the
single last write with SC dropped), the fidelity gap (I3), the gate (I4) and the async
agents (I7); §4 Corollary "The sync instance" is the second clock. T9 proves or refutes
them in the document's terms and measures them; it does not rediscover them.

Part 1 — the engine itself (Theorem "sound", location level)
1. The engine's `hb_races` did not change with the fix, so the theorem's *statement* is
   untouched — but its *algorithm* is not what runs: the checked-in publish/tick order
   (B1 item 1; §7, I1) makes the engine silent on a releaser's post-release
   access in the trace order shown there, which is precisely the indirect-reuse race of
   rtraw with block 0 first. Write this up as the soundness gap, with the trace table and
   the `R_miss` characterisation, in `design/soundness_event_candidates.md`; the corpus
   instance is `race_interblock_fence_rtraw` (T9-0 §3, evcand vector-clock dump, seq
   5–8) — use it as the regression test. The fix is Part 3. Do the same for I2: confirm
   the three-thread counterexample on the real oracle (T6's strict xfail) and state the
   lost class; D6 is decided (buckets).
2. Show what the location-level guarantee promises for a pair with no dependency edge:
   the theorem is about records, not edges, so "no edge" is irrelevant to the engine —
   any conflicting, HB-unordered pair on a location yields a report on that location.
   State that explicitly, since it is the reason the engine needs no candidate mechanism.
   Then extend §1–§2 by the async agents (I7: copy records of a virtual agent, commits
   as its ticks, generators (ISSUE) and (WAIT)) and re-check the theorems of §4 with them.
   All edits go into `hb_proof.tex`; there is no other proof document.
Part 2 — the composed vector-clock verdict vs the scalar-clock verdict
3. Argue (and then measure) that vector-clock mode reports a superset of scalar-clock
   mode on every trace: both judge the same candidate sets — the engine's
   `hb_races_sync_only` and the offline `barrier_only_pairs` are the same clock
   (`FP_DIAGNOSIS.md` 3b: "identical to the oracle's second clock on every corpus
   kernel") — with the same static rules; vector-clock mode additionally has `hb_races`,
   which can only turn `latent` into `structural`/`model_bug`, never remove a report
   (under D8, Race ∪ Latent of vector-clock = Race of scalar-clock plus the vetoes).
   T9-0 §6 measured this on the same trace: 557 of 558 programs agree; the exception is
   crs-cuda's `CUVEIN_BARRIER_PASS_MAX_LANES` cutoff (26 kernels above 5 M lane-accesses,
   6 vector-clock pairs never judged by scalar-clock); an absent `hb_races_sync_only` key
   and candidate-generation differences did not occur. State the three failure modes
   as the proof's §5 does ((a) R3 at pc level — the canary; (b) candidate generation;
   (c) the cutoff) and cite the census numbers; do not re-measure.
4. Done by T9-0 (`eval/LATENT_CENSUS.md`; script `eval/baselines/latent_census.py`).
   Re-run `latent_census.py tables` after Part 3 lands and report the moves: expected
   `fence_rtraw` latent → structural; the other nine unchanged until T12.
Part 3 — publish-then-tick (needs D1)
5. Implement, in `hb_oracle.py` and `pc_dependency_analysis.cpp` in the same commit:
   - I1: Algorithm 1's order — acquire-join, checks, publish `released[loc]` with the
     pre-tick clock, record the atomic at the pre-tick epoch, then tick.
   - I2: replace `last_write`/`last_reads` by buckets keyed `(thread, kind, strength,
     scope)` per location, each holding (epoch, pc); `Check` walks every other thread's
     buckets; report SC (`ms ∧ ¬both-RMW`) as its own class in `hb_races`. The
     `coherent()` filter of `--strong-ldst generic` goes away (SC is the report it was
     suppressing). No FastTrack-style collapse across threads (the soundness proof needs
     the replaced entry PO-related to its replacement); measure the bucket term with
     `HB_STATS` on T5a's three programs before/after.
   - I2, second clock: the barrier-only clock shares the last-write state
     (`design/algorithms_check.py` "SYNC-MISS": 8 barrier-unordered pairs absent on 3
     litmus traces), so the buckets go into `hb_races_sync_only` and
     `sync_dominance.barrier_only_pairs` as well; §5 fact (ii) holds for the code only
     after this.
   - I5 (D14): local memory leaves the model. In the HB trace path
     (`hb_collect_events`, gated by `YOSEMITE_HB_TRACE`) stop serializing
     `MemoryType::Local` records; in engine, oracle and `barrier_only_pairs` skip any
     `local` record before `Check`/bucketing, so kept dumps replay identically to new
     ones. Do not touch the collector's default path or the local-address tag at
     `gpu_patch_pc_dependency.cu:89` (it predates the project — FlagZhao `nv-compute`
     `cuVein` commit `ccefba0`; the dependency side reads it). Measure `hb_events` size
     before/after on `local_mem_blocks.cu` and on one P7 program whose vector-clock dump
     never finished — spills go through local memory.
   - Verdict layer (D12): R2 leaves ρ. In `_hb_class` the class of a candidate pair is
     DR if some instance is DR, else SC — from `hb_races` instances in vector-clock mode,
     from R2 at pc level with the largest observed distance otherwise (may demote SC → DR,
     never the reverse); the verdict rows are `hb_races` (Race/Strong conflict;
     `model_bug` only if R1), R1 ∨ χ (Ordered), ∉ barrier-only set (barrier-ordered),
     otherwise Latent (vector) / Race (scalar), each with its `sc` variant.
     `make_tables.py`: `latent` and `sc` informational columns, two operating points,
     counts from the class before `judge`'s relabels (D2).
   Tests already exist from T6 in `python/test_hb_substitutions.py` as strict xfails —
   `test_write_after_unlock_other_schedule` (I1: the pair in `hb_races`, class
   `structural`), `test_strong_stores_barrier_weak_load` (I2: (A, C) in `hb_races`),
   `test_local_memory_is_thread_private` (I5) — turn all three green and add the
   test file to the green set; keep `test_write_after_unlock_is_event_candidate`. Add one
   test for D12: a strong store meeting a strong load unordered in the run is `sc` in
   vector-clock mode and never `model_bug`. Both modes; engine == oracle ==
   `algorithms_check.py` with the I1/I2 switches off.
6. Re-score, no GPU: `hb_oracle.py` over every kept vector-clock `kernel_*.json` before
   and after, diff the race sets, `parallel.py analyze` with the new oracle output for
   the verdict deltas per program, then `latent_census.py tables`; then one GPU sweep of
   P5 (33 litmus) and E2 in both modes. Report every flipped verdict with its cause, TPs
   gained, FPs introduced, and the `HB_STATS` bucket term.

Deliverable: `design/soundness_event_candidates.md` (Parts 1–2, citing T9-0), the
I1/I2/I5 diff with the before/after table; update the table of §7 in `hb_proof.tex`
(I1, I2, I5 rows → "matched", with the commit) and the "code's `_hb_class`" sentence of
§5.

### T10 — Sidecar strength and scope (O1)
Branch `fix/sidecar-strength`. Model: Sonnet (implementer), Opus (review). No GPU:
re-score only. After T9 (the SC row must exist). Decision D9.

Context: the sidecar (`python/atomic_scope_sidecar.py`, consumed by the engine through
`YOSEMITE_ATOMIC_SCOPE_FILE` and by `sync_dominance.py`) classifies atomicity by RMW
opcode, so `LD/ST .STRONG.<scope>` (`cuda::atomic` relaxed loads/stores, `volatile`) is
weak. Under PTX §8.7.1 a strong–strong pair at sufficient scope is not a data race but
an unordered strong conflict; the graph-code false results (E0 reduction/F1, E1 Indigo3
`nobug`, E3 ECL) are exactly that (`learnings`), and the DR/SC split is wrong in both
modes until this is fixed.

Steps
1. Sidecar: emit `strength ∈ {weak, strong}` and `scope` for every memory pc from the
   SASS token (`.STRONG.{CTA,GPU,SYS}` on `LD/ST/ATOM/RED`; plain loads/stores weak;
   anything unrecognised weak — scope errs narrow, A4). Keep the existing RMW columns.
2. Engine and oracle read the new columns for `key(e)` and `ms`; `sync_dominance.py` R2
   uses the same table. Old sidecars without the columns keep today's behaviour.
3. Re-score E0/E1/E3 and the evcand store: expected the strong–strong pairs move DR →
   `sc`; list every other verdict that moves. Green set: `test_atomic_memory_model.py`
   gains one strong-load/strong-store litmus per scope.

Report: `eval/SIDECAR_STRENGTH.md` with the before/after table and the E0/E1/E3
explanation rewritten (the "benign race" explanation in `FIX_REPORT.md` was wrong).

### T11 — Trace-validity monitor: one module, offline CLI, no degrade path
Branch `fix/tv-monitor`. Model: Sonnet. No GPU. After T3b (the fifth check exists).
Decision D10.

Steps
1. Factor the TV checks (`TV-seq-monotonic`, `TV-barrier-overfill`,
   `TV-barrier-completion-order`, `TV-expected-nonzero-multiwarp`,
   `TV-barrier-pending-at-end`) into `python/tv_check.py`, used unchanged by
   `hb_oracle.py`, `barrier_only_pairs` and a CLI `tv_check <kernel_N.json>...`; identical
   results to `HbClock` on every kept dump (the checks use no clock).
2. `HbClock`: keep the checks behind `YOSEMITE_HB_STRICT`; delete the `expected == 0`
   per-warp degrade path (unreachable on launched kernels; unsound without strict) —
   an unknown count is a hard error. Measure strict on/off on T5a's three programs
   (D10).
3. I6, only if it is a small change: key the W2 row per lane rather than per warp;
   otherwise leave it and note it (no corpus firing is known: 0 violations on ScoR
   32/32, `HARDENING_REPORT.md`).
4. Run `tv_check` over every kept store and report violations per suite — the
   proved-in-effect number for the paper; today only ScoR (32/32, zero) is counted.

Report: `HARDENING_REPORT.md` §"Offline checking".

### T12 — I4: the instance gate, and R3's release point from the trace — done
**Done 2026-09-30** (rebased on T5b, merged 7849a70; `eval/INSTANCE_GATE.md` §9,
`design/instance_gate.md`; pre-rebase history on `feat/instance-gate-prerebase`). Kept for
reference; see the 09-30 status paragraph for what it changed beyond the brief.
Branch `feat/instance-gate`. Models: Opus (design and review), Sonnet (implementation).
No GPU for the measurement; one P4/P5 sweep at the end. After T9 and T10; in parallel
with T5b (D13). Decisions D11, D13.

Context: the engine's trusting gate treats every RMW as release and acquire, which
manufactures ordering that PTX does not give. T9-0 showed the cost: 8 of the 10
latent-only ScoR races are unordered under PTX and ordered by this gate — the verdicts
survived only because R3 checks fences — and `test_relaxed_handoff_should_race` is the
standing strict xfail. The per-pc gate of the 09-24 proof draft is **not** the fix: it
rejects the success-branch-fence idiom (`matrix-multiplication`'s block lock, the ticket
`atomicInc` of `reduction`) because the failure edge is a fenceless CFG path (T9-0
Finding 1). The proof's Definition "Gate" (revision 09-26) is the instance gate, and
§5's R3 amendment uses the same predicate.

Steps
1. Predicate: `fenced(p, p', s)` on the kernel CFG from the dots — every path from pc `p`
   to pc `p'` crosses a fence of scope ≥ `s`, where "fence" is the per-architecture
   inventory O2, with separate release-side and acquire-side sets. T6's scan of 293 sm_89
   CFGs is the starting point: release side `MEMBAR.SC.{CTA,GPU,SYS}`; acquire side
   `CCTL.IVALL` (an acquire load or RMW lowers to the access followed by `CCTL.IVALL`,
   **no** `MEMBAR` — a `MEMBAR`-only predicate sets `acq = 0` on every PTX acquire); a
   seq_cst fence is `MEMBAR.SC; ERRBAR; CCTL.IVALL`; `BAR.SYNC` counts as scope `cta` on
   both sides (none of the 461 barriers has an adjacent `MEMBAR`). Open: what, if
   anything, a `cta`-scope acquire emits; whether a path that starts or ends *at* a fence
   or barrier arrival "crosses" it (say yes, and say why). Emit into the sidecar the data
   the engine needs online: per RMW pc, the (previous-pc, next-pc) → fence-scope entries
   reachable within the kernel, or a compact reachability table — design note first
   (`design/instance_gate.md`), Opus.
2. Engine and oracle: `rel(r)` from the thread's previous record's pc; `acq(r)` from the
   thread's next record's pc — the oracle has the trace and evaluates directly. The
   engine defers, and the design note must carry T6's four points for it to be exact
   (proof §3, corrected): `Check(r)` is evaluated against `clk[t] ⊔ Ch_ℓ` with the
   difference held until `acq(r)` is known (a spinner's plain read of the lock word
   against the next owner's CAS must not become a spurious DR); `released[loc] = vc[t]`
   (`hb_oracle.py:333`, `.cpp:473`) becomes a join; no publish when `rel(r) = 0`; held
   pairs are resolved at kernel end (`acq(r) = 1` for a thread's last record). Gate
   (ATOM) only; `ms` untouched (A4).
3. R3 (`sync_dominance.py`, `HBGraph.chain`): the release point is the `PO`-next RMW of
   `u`'s thread after `u` from the trace, and "release-fenced" is `fenced(pc(u), pc(r), d)`;
   add the write-before-lock decline (u precedes, in its own thread, an acquire on the
   chain's location) symmetric to `_past_release`. Expected: the 23 `no-release-point`
   latent FPs of T9-0 §4 become `ordered`.
4. Measure before wiring: run the gated oracle over the kept stores (no GPU) and diff
   against T9-0's tables. Expected: the 8 ScoR fence races latent → structural;
   `race_interblock_none-lock_rtraw` stays latent; `matrix-multiplication-norace` clean;
   `reduction-norace` reported through the ticket idiom (D11: footnote, iGUARD agrees);
   `test_relaxed_handoff_should_race` passes (remove the strict xfail marker in the same
   commit); every other move listed with its cause. `HB_STATS` on T5a's three programs:
   unfenced RMWs no longer publish or join, so report the memory change — this decides
   how much T5b still has to do.
5. Wire it (engine + oracle + `barrier_only_pairs` unaffected), green set, one P4/P5
   sweep in both modes, `latent_census.py tables`.

Report: `eval/INSTANCE_GATE.md`; update §7's I4 row in `hb_proof.tex` to "matched" and
write the one-paragraph containment argument in §6 (the gate admits only PTX
release/acquire patterns).

### T13 — NVBit feasibility spike: can atomics be recorded after execution, with the value read? (one day)
Branch `study/nvbit-spike`. Model: Sonnet. GPU: one `rtx4060ti16g` node (sm_89, CUDA 13.3,
driver 580.82). **Time-boxed to one day. Measurement and report only: nothing in the
detector, the collector or the proof changes, and nothing is merged.** Independent of the
T3b/T9 merge; runs in parallel with it.

Context. The Sanitizer collector records a memory access at the callback, which runs
*before* the instruction, so a record's position is the issue point and an atomic
executes somewhere before the thread's next record. When two RMWs on one location from
different warps have overlapping windows, trace order and coherence order come apart
and assumption A2 of `hb_proof.tex` fails (T9: `matrix-multiplication-norace-small`, a
successful lock CAS recorded five records before the unlock it read from; D15). The
Sanitizer patching API has no after-instruction hook (verify in `sanitizer_patching.h`
and say so). NVBit has `IPOINT_AFTER` and can pass register values to the
instrumentation call. This spike answers three questions the paper's limitations
paragraph depends on, and nothing more: does NVBit run on this toolchain; does the
after-point yield an atomic's old value correctly; what does it cost. Do not build a
collector.

Environment. The compute nodes have no route to GitHub; the login node does. Download
on the login node, build and run on an allocated node:
- login node: fetch the newest NVBit release tarball from
  `https://github.com/NVlabs/NVBit/releases` (the Linux x86_64 build) into
  `~/incoming/nvbit/`, record the version and the CUDA/driver support stated in its
  README, and do the same for the release the `nv-nvbit` submodule pins if it differs.
  Nothing else runs here.
- compute node: `salloc -p rtx4060ti16g -x c54,c2 --time=8:00:00 --gres=gpu:1`, then
  every build and run through `srun` inside that allocation (the allocation is the whole
  day's budget; do not sbatch one job per step). Extract the tarball under
  `~/incoming/nvbit/<version>/` there, build `tools/mem_trace` and `atom_after` with the
  node's `nvcc` (CUDA 13.3), and keep the allocation until step 5 is done. Never load
  NVBit and the Sanitizer collector in the same process: run each measurement in a clean
  environment (no `YOSEMITE_*`, no `LD_PRELOAD` of `libsanalyzer`).

Steps
1. Inventory. Look at the `nv-nvbit` submodule (`.gitmodules` → `AccelProf/nv-nvbit`):
   what it contains, which NVBit release it pins, whether anything in it already traces
   memory. Compare that release with the newest one downloaded above; use the newest
   unless its README excludes driver 580 / CUDA 13.3, in which case try both and report
   which loads. If neither loads on the node, that is the blocker: stop after step 2's
   evidence and write the report.
2. Load test. Build NVBit's `tools/mem_trace` unchanged and run it on
   `ScoR/microbenchmarks/artifacts/race_interblock_fence_rtraw` (the binary the litmus
   suite already builds). Record: NVBit version, whether the tool loads under driver
   580.82 / CUDA 13.3, whether a trace is produced, and any warning it prints.
3. Value test. Write a small tool `atom_after` (copy `mem_trace`, ~100 lines changed):
   for every `ATOM*`/`ATOMS*`/`ATOMG*` (not `RED`, which returns nothing) insert a call
   at `IPOINT_BEFORE` with pc, lane mask and the memory address
   (`nvbit_add_call_arg_mref_addr64`) and a call at `IPOINT_AFTER` with pc and the
   **destination register's value** (`nvbit_add_call_arg_reg_val` on the instruction's
   destination operand). Emit one line per lane per call to the host channel with a
   sequence number taken by `atomicAdd` on a global counter, so before/after positions
   are comparable with the Sanitizer's. Test kernel `python/testdata/atom_values.cu`,
   three parts on one GPU run:
   - one warp, lane 0 only: `atomicAdd(&x, 1)` eight times — the after-values must be
     exactly 0..7 in order;
   - eight warps, all lanes: `atomicAdd(&x, 1)` once each — the after-values must be a
     permutation of 0..255 with no repeats (this is the coherence order, read off
     directly);
   - the matrix-multiplication lock idiom, 4 blocks × 4 warps contending one
     `atomicCAS(&lock, 0, 1)` / `atomicExch(&lock, 0)` with a fenced critical section:
     old values must alternate correctly (a successful CAS reads 0, the next successful
     CAS reads 0 only after an Exch), and every failed CAS reads 1.
   If the after-value is wrong or stale on the long-latency global atomics — the known
   risk with reading a destination register right after a memory instruction — try the
   same read at the next instruction's `IPOINT_BEFORE` and report which works.
4. A2 in vivo. On part three, using only the before-positions (the Sanitizer's view),
   count the same-location RMW pairs whose windows overlap, and how many of those the
   values show to be inverted relative to trace order. This is the first measured rate
   of A2 violations; report it per contention level (2, 4, 16 warps).
5. Cost. Wall-clock of `race_interblock_fence_rtraw` and one P4 app (`bfs`, or the
   smallest that traces quickly) under: native, the Sanitizer HB path
   (`YOSEMITE_HB_TRACE=1`, scalar-clock mode), `mem_trace`, and `atom_after`. One run
   each is enough for an order of magnitude; say if it isn't.

Acceptance: a yes/no for each of the three questions with the evidence; the numbers of
steps 4 and 5; the list of blockers; the source of `atom_after` and the test kernel
committed on the branch under `eval/nvbit_spike/`; the exact `salloc`/`srun` commands
and the NVBit version, so the result is reproducible from the login node. No file
outside that directory and `eval/NVBIT_SPIKE.md` changes.

Report: `eval/NVBIT_SPIKE.md` — one paragraph the paper can cite ("recording atomics after
execution with the value read is / is not feasible on this toolchain; observed inversion
rate; overhead ratio"), then the details. No `Co-Authored-By` trailer.

### T14 — A2 in the tables: the `a2_uncertain` flag and the offline window count
Branch `feat/a2-flag`. Models: Sonnet (implementation), Opus (review of the flag's
definition against the proof). No GPU: kept dumps only. After T9 (merged); in parallel
with T10 (it touches `_hb_class`, `make_tables.py` and a new offline script, not the
sidecar). Decision D15.

Context. The collector records an atomic at its callback, before the instruction
executes; an RMW's *window* is [its record, its thread's next record). When two RMWs on
one location from different warps have overlapping windows, trace order may invert
coherence order (A2), and a chain edge between them can run the wrong way: the true
edge missing (a false DR, T9's `matrix-multiplication-norace-small`) and a false edge
manufactured (a possible missed race). T13 measured the inversion rate at 1.3 % / 4.1 %
of hand-offs at 4 / 16 contending warps on the lock idiom (`eval/NVBIT_SPIKE.md` §4).
Nothing here changes a verdict: the flag is information on a report, and the count is
a number for the paper.

Steps
1. Definition, Opus first (half a page in `design/a2_flag.md`): a chain edge $r \to q$
   (successor RMWs on one location, `hb_proof.tex` Definition "Gate") is
   *order-uncertain* iff the two windows intersect, i.e. `seq(q) < seq(next record of
   r's thread)`. A reported DR pair is `a2_uncertain` iff, in the vector clock, the
   pair would be HB-ordered had every order-uncertain edge on the pair's location
   been reversed — approximate this conservatively as: the pair is unordered, and the
   two accesses' threads both hold RMWs on some location whose chain contains an
   order-uncertain edge between them, in either direction. State why the
   approximation can only over-flag, never under-flag, and what it costs.
2. Oracle and engine (same commit): record per RMW its window end when the thread's
   next record arrives; mark chain edges whose windows intersect; carry the flag on
   the aggregated race record (`hb_races[*].a2_uncertain`, a count of flagged
   instances alongside `count`). `barrier_only_pairs` unaffected (no ATOM edges).
3. Verdict layer: `_hb_class` passes the flag through; `judge` never changes a verdict
   on it; `make_tables.py` gives `a2_uncertain` its own column, counted as neither TP
   nor FP, at both operating points (D2's convention for `latent` and `sc`).
4. Offline window count, `eval/baselines/a2_window_count.py` over the kept dumps
   (evcand store, both modes' dumps where present): per program, the number of
   same-location cross-warp RMW pairs, the number with overlapping windows, and the
   number of those on locations whose RMWs release or acquire (an RMW followed in its
   thread by a plain access to another location, or preceded by one). Group by suite.
   This is the paper's number.
5. Re-score the evcand store with the flag: expected `matrix-multiplication-norace-small`'s
   four DR pairs flagged, no verdict moved, the flag rate per suite reported next to the
   window count. Test: the T9 kernel of `test_hb_substitutions.py` for the lock idiom,
   run with contention forced (16 warps), asserting the flagged count is > 0 and the
   unflagged DR count is 0 on the race-free variant.

Acceptance: no verdict changes on the evcand re-score; green set unchanged plus the new
test; the two numbers per suite (window overlap rate; flagged reports) in the report.

Report: `eval/A2_WINDOWS.md` — the definition, the corpus table, and the paragraph the
paper cites (A2's measured exposure on this corpus, with T13's in-vivo rates as the
calibration). Update `hb_proof.tex` §7's A2 paragraph with the corpus numbers. No
`Co-Authored-By` trailer.

### T15 — Late ordering key for the HB records (A2 mitigation, measured first) — done, not adopted
**Done 2026-09-29** (55fe57c, `eval/LATE_SEQ.md`): ~12 % fewer inversions, below step 4's
bar; off by default; the premise in the context paragraph below (that NVBit's tool drew its
key last) was wrong. Kept for reference; the dual-key dump it added is the instrument for
T4's optional A2-gap steps.
Branch `perf/late-seq`. Model: Sonnet. GPU: one `rtx4060ti16g` node, the lock litmus only.
After T14 (merged). Small; parallel with T5b and T12. Nothing is adopted until step 3 says so.

Context. T14 measured the Sanitizer collector inverting a lock hand-off in 11–32 % of cases
where T13's NVBit tool saw 0–4 %. The likely cause is where the ordering key is drawn: the
collector's callback takes its buffer index at the start (`GetBufferIndex`), then writes the
record, `__threadfence`s and increments the entry count (`IncrementNumEntries`, with the
doorbell wait), so the window between the key and the instruction contains a fence and a
second global atomic; a key drawn as the callback's last action leaves only the return and
the scheduling gap. HB-path only (`YOSEMITE_HB_TRACE`); the default collector path stays
byte-identical.

Steps
1. In the HB path, as the callback's last action before returning, draw a second key — an
   `atomicAdd` on a separate global counter, and, as a variant, `%globaltimer` — and store it
   in the record (a field the default path never reads; say which). Host side: order
   `hb_events` by the late key instead of the buffer index (stable; ties by buffer index),
   and mark the dump `hb_late_seq: 1`. Engine, oracle and `barrier_only_pairs` are unchanged
   (they consume `seq`).
2. Trace-validity: W0 (seq monotonic per thread) must still hold under the late key — a
   thread's own callbacks are sequential, so it does; assert it in `tv_check` on every dump
   of step 3.
3. Measure with T14's harness (`a2_window_count.py handoffs`, `lock_contention_a2.cu`, 5 runs
   × 3 levels, both key variants): inversion rate against the buffer-index key on the same
   runs (both keys are recorded, so one run gives both). Also the verdicts and `a2_uncertain`
   counts of the three ScoR programs that rest on flagged reports only, re-recorded once.
4. Adopt only if the rate drops by an order of magnitude at 4 and 16 warps and no TV check
   fires; otherwise report and leave the default off (`YOSEMITE_HB_LATE_SEQ=0`).

Report: `eval/LATE_SEQ.md`: the rates side by side, the ScoR re-recordings, the cost per
record, and the sentence for D15. No `Co-Authored-By` trailer.

### T5b — Shared-base main clock (todo 5, the fix) — done
**Done 2026-09-30** (merged b3bfdf3; `eval/MEMORY_FOOTPRINT.md` §7). Kept for reference;
the second acceptance bar is reassigned to T4 (see the 09-30 status paragraph).
Branch `perf/shared-base-clock`. Models: Sonnet (implementation), Opus (review). GPU:
the programs in `eval/baselines/setup/engine_timeout_ids.txt`. Directly after T9, in
parallel with T12 (D13). **On the critical path**: T9-0 §1 found no vector-clock dump
for P7, 8 of 9 P9 programs, 10 of 28 P4 apps and 23 P1 programs, so the reference mode
does not run on the realistic suites and the mode comparison is bounded until it does.
T6 classified the 58 timeout programs by SASS: 30 atomics + barriers, 8 atomics only,
10 barriers and no atomics (P7 heartwall, hotspot, lavaMD, particlefilter, pathfinder,
srad, stencil1d, P9 dxtc2, …), 10 neither; T5a measured the barrier-only regime
(tiled_gemm: all of `vc`'s 2.73 GB from `sync_group` copies). The 10 barrier-only
programs are the acceptance set — no gate can touch a barrier join.

The sync-only clock already uses a shared immutable base per sync group plus a scalar
own component (`pc_dependency_analysis.cpp:56-63,159-168`). Do the same for the main
clock `vc`: `struct MainClock { shared_ptr<const Clock> base; Clock delta; uint64_t own; }`
with lookup = max over (base, delta, own); `sync_group` allocates one base per group;
atomic acquire joins into `delta`; releases store a pointer to the base + a copy of the
(small) delta, not a full clock. Mirror the representation in `hb_oracle.py` only if the
oracle's exactness is preserved (the oracle may stay O(threads) per thread — it is the
spec, not the product; but its results must stay identical).

Acceptance: engine == oracle on the green set and on 10 kept traces of each pset via the
re-score path from T9; `HB_STATS` (T5a) shows `vc` bytes ≈ O(threads) after a barrier;
all 10 barrier-only programs of `engine_timeout_ids.txt` and at least half of the rest
finish under the 120 s cap; `tv_violation` still 0. Report `eval/MEMORY_FOOTPRINT.md`
§"After the fix".

### T4 — No-dump mode: both clocks during the run, aggregates only (reframed 2026-09-30)
Branch `feat/no-dump`. Design note: Opus. Implementation: Sonnet. GPU: the timeout set
first, then P7 and P9. After T5b, T12 and T17. **This is the critical path**: it is the only
route to vector-clock and scalar-clock verdicts on the realistic suites before the
submission.

Context. Nine of the ten barrier-only timeout programs, and by T9-0's count most of P7 and
P9, never finish in either mode. The cause is not analysis and not storage: the HB path
appends every record to an in-memory `hb_events` for the whole kernel and serialises it as
text JSON at kernel end (`hb_collect_events`, `kernel_trace_flush`), so those programs die
of host memory or of the 1,200 s cap while writing 100–252 GB, and the offline
scalar-clock pass would then parse it for hours (P9-mr-cuda: 4 h cap, twice). The
dependency-graph tool in the same file never keeps a record: it updates shadow state per
drained buffer and writes per-pc-pair aggregates at kernel end. Vector-clock mode's
runtime already works that way for its own clock; the dump is the extra.

Steps
1. Design note `design/no_dump.md` (Opus, before any code): enumerate exactly what
   `sync_dominance.py` and the harness read from `hb_events` today — `hb_races`
   (aggregated since T9), `hb_races_sync_only`, event-stream candidates, R3's per-pc
   release/acquire points (the PO-next and PO-previous RMW pcs of each access pc, per
   thread, as it takes them from the trace since T12), the A2 windows and flag, the
   trace-validity flags, `len(hb_events)` — and for each say whether the runtime can
   emit it as an aggregate at kernel end and what it costs. Candidates need no separate
   mechanism: the runtime checks every conflicting pair. Name anything that cannot be
   emitted and what the verdict layer loses without it.
2. Runtime (`YOSEMITE_HB_DUMP=0`): the scalar clock (`barrier_only_pairs`' clock, already
   present in T5b's layout) computed alongside the vector clock; at kernel end write a
   `kernel_N.json` with the aggregates of step 1 and no `hb_events`, marked
   `hb_aggregates: 1`. The default (`YOSEMITE_HB_DUMP=1`) is unchanged and lossless.
3. Reader: `sync_dominance.py` and `make_tables.py` accept an aggregates-only dump; the
   verdict layer runs unchanged on it. Parity: on 20 programs that can do both, the
   verdicts and classes from the aggregates equal those from the full dump.
4. Run the ten barrier-only timeout programs and then all of P7 and P9 in both modes
   under no-dump; report which finish, wall time and peak host memory against the
   dump runs, and the first vector-clock verdicts on those suites.
5. Optional, second half if time allows: streaming lossless encoding for the mid-size
   suites (write per drain, binary lanes as base/stride/mask, `hb_events_count`), one
   reader module `python/hb_events.py`, byte-identical oracle output on the kept traces.
6. Optional tail (the A2 gap, no GPU for the first): inversion positions of T15's dumps
   against `bpos` modulo the buffer size (the buffer-full handshake hypothesis); a delay
   knob in the lock litmus's critical section under this collector (the instrumentation-
   density hypothesis) — one node-hour. Skip both if the schedule is tight.

Acceptance: step 3's parity holds; at least the nine barrier-only programs produce
verdicts in both modes; `hb_events` is never written lossy. Report: `eval/NO_DUMP.md`.
No `Co-Authored-By` trailer.

### T16 — The certain clock: a sound operating point without values (decision D16)
Branch `feat/certain-clock`. Model: Sonnet; Opus for the one-paragraph soundness note. No
GPU: kept dumps. After T14 (merged). Small; alongside T4.

Context. Three clocks can be computed from one trace, differing only in which chain edges
they accept. The recorded clock accepts the trace's order (today); the possible clock
(T14's flag) accepts any order the windows allow; the certain clock accepts an edge between
two RMWs only when their windows do not overlap. Under A2w (an RMW has taken effect by its
thread's next record) every certain edge is a true coherence edge, so the certain clock's
happens-before is a sub-relation of the execution's and, by Lemma "Monotonicity", its
reports are a superset of the execution's races: sound with today's collector, complete
except on contended hand-offs.

Steps
1. `HbClock` and oracle: a switch (`YOSEMITE_HB_GATE_CERTAIN=1` / `--certain`) that refuses a
   chain edge `r → q` when `seq(q) < seq(next record of r's thread)`; T14's window
   bookkeeping already knows `nx(r)`. Both directions refused; nothing else changes.
2. One paragraph in `hb_proof.tex` §7 ("A2 observed to fail") stating the sub-relation
   argument and the assumption it rests on.
3. Re-score the kept stores under the switch: the "Race (sound)" column per program and
   suite next to Race and Race ∪ Latent; the programs whose sound verdict differs from the
   recorded one, with the class of the added reports (expected: the flagged population).
   Test: the 16-warp lock litmus, the sound column reports the critical sections the
   recorded clock orders.

Report: `eval/CERTAIN_CLOCK.md`; `make_tables.py` gains the column behind the switch.

### T17 — Rename `HbEngine` to the mode vocabulary (decision D17) — done
**Done 2026-09-30/10-01** (663a288; merged b6c9055; D17 = `HbClock`, see B3). The names, the
both-spellings readers in `python/hb_modes.py` and the checks are in the commit messages; the
install and its open green-set finding in the commit after the merge. Kept for reference.
Branch `chore/rename-vector-clock`. Model: Sonnet. No GPU; no value changes. After T12
(merged), before T4, while `pc_dependency_analysis.cpp` is quiet.

Steps
1. Inventory: `git grep -n -i engine` over code, tests, scripts, `eval/README.md`,
   CLAUDE.md; classify each hit as identifier, persisted field, env var, file name, or
   historical report (the reports stay as written).
2. Rename the class and its functions (`HbEngine`, `hb_engine_emit`, `HbEngine::emit`, the
   stats labels) to the chosen name (D17); test names of the form "engine == oracle" to
   "vector-clock implementation == specification"; `engine_timeout_ids.txt` to
   `vector_clock_timeout_ids.txt` with the old name kept as a symlink for the SLURM
   scripts until they are updated.
3. `YOSEMITE_HB_NO_ENGINE`: deprecated, honoured with a warning for one release
   (scalar-clock mode already implies it). Any persisted field spelled with "engine"
   (harness rows, JSON) gets a reader that accepts both spellings; check the re-score
   paths on one kept result per suite.
4. CLAUDE.md, `eval/README.md`, the proof's §3 correspondence paragraph and §7: "engine"
   replaced by the mode or the class name; the A4 rule "never mix vocabularies inside one
   file" now covers identifiers.

Acceptance: green set unchanged (305 + gate tests), re-score of one program per suite
identical, `git grep -i engine` returns only historical reports and the deprecation
shim. No `Co-Authored-By` trailer.

### T7 — Optional: speed up the offline analysis (todo 7)
Branch `perf/analysis-hotpath`. Model: Sonnet (profiling); Opus only if a port is
warranted. After T4.

Profile before rewriting: `sync_dominance.analyze()` loads the whole JSON
(`sync_dominance.py:633`) and the only O(events) pass is `barrier_only_pairs`; the
P9-mr case (113 GB, 1600 kernels, >4.5 h; `eval/baselines/setup/blockers.md`) is the
benchmark. Run cProfile on three of its kernels and on tiled_gemm N=512. If parsing
dominates, T4's binary format + streaming reader is the fix and no language change is
needed. If the barrier pass dominates, port only `barrier_only_pairs` to C++ (it is
`HbClock`'s sync-only pass; expose it as an offline mode of `HbClock` over the dump) and
keep the verdict logic in Python. A whole-script rewrite is out of scope unless the
profile shows the Python verdict loop itself above 30 % of wall time. Report:
`eval/ANALYSIS_PROFILE.md`.

# T14 — A2 in the tables: the `a2_uncertain` flag and the offline RMW window count

Branch `feat/a2-flag`, based on `cuVein` f127790 (the 2026-09-28 evening revision). Commits:
c1becbb (the definition, `design/a2_flag.md`, before any code), 2056042 (the flag in
`hb_oracle.py` and `HbEngine`, the verdict layer, the tables, the tests), f259a4a (the window
count and re-score runner), 34acb00 (SC instances too; the lock test independent of T10's
policy), a0969a9 (joins along moral-strength components), f534851 (per-row verdict comparison;
engine == oracle in `handoffs`), 1b6f8c9 (the results, `eval/results/t14-a2/`), then the commit
that adds this report and the proof's §7 paragraph. Hardware: RTX 4060 Ti 16 GB, sm_89 (GPU
runs on c1, c51, c53, c58; drivers 580.82.07, 580.95.05, 580.105.08), CUDA 13.3; CPU work on
`normal` nodes.
Private runtime (the T9 recipe, nothing installed): libsanalyzer `d0a611d29766cce4`
(`sanalyzer/wt_install`), collector `c91568838f133228` (the worktree's `lib/`, RPATH to it).
Labels: **proved-in-effect** (checked over N real traces), **tested** (a verdict asserted),
**unverified**.

## Summary (the paragraph the paper cites)

The Sanitizer calls our collector before each instruction, so an atomic's record marks its
issue, and where the windows of two RMWs on one location overlap — the window of an RMW runs
from its record to its thread's next record — the recorded order can invert coherence order
(assumption A2). On our own collector's traces of a race-free spin lock (the shape T13
measured with NVBit), a hand-off is recorded inverted exactly when the trace leaves two
adjacent critical sections unordered, and that happens in 53 of 465 hand-offs at 2 contending
warps, 306 of 945 at 4 and 1,054 of 3,825 at 16 (15 runs per level) — 11–32 %, where NVBit's
instrumentation, reading the values, saw 0–4 %. Across the kept traces of P1–P6, every one of
the 397 programs (vector-clock traces; 432 scalar-clock) in which two warps apply RMWs to one
location has at least one overlapping pair of windows, 359 (394) of them inside windows a later
record of the same thread closes; the median program has 30 % of its cross-warp same-location
RMW pairs overlapping. Every reported instance that the execution may have ordered — that some
coherence order consistent with the windows orders — carries an `a2_uncertain` flag. The flag
assumes only that an atomic has taken effect by its thread's next instrumented instruction; it
over-approximates those instances (checked against every such order on 10,000 random traces),
and it changes no verdict. On the re-scored vector-clock traces it marks
432,810 of 8.58·10⁹ data-race instances in 34 programs; three programs, all
labelled race-free (`matrix-multiplication` and both inputs of `rule-110`, ScoR), have a
Race-alone verdict that rests on flagged reports only, and the tables count them in their own
column, as neither TP nor FP.

## 1. Definition (`design/a2_flag.md`)

- **Window** of an RMW `r` of thread `t`: `[pos(r), nx(r))`, `nx(r)` = position of `t`'s next record
  of any kind (memory, arrival, syncwarp, exit, cp.async commit/wait; a `local` record is no
  record), `+∞` if none. Positions are (seq, lane); seq gaps (pre-T3b dumps drop exit records)
  are harmless.
- **A2w** (the flag's assumption): coherence order on each location is a linear order that puts `r`
  before `q` whenever `nx(r) ≤ pos(q)`. T13 saw no inversion outside overlapping windows (30 runs).
- **Target** F\*: the reported instances some A2w-consistent coherence order would order (either
  direction). The brief's thread-pair approximation can miss members of F\* (a block-leader lock
  spread by `__syncthreads`, hand-over-hand locking, an inversion between non-adjacent RMWs);
  the flag is therefore a clock.
- **Flag**: a sparse "possible" delta `pd` next to `vc`, following it through every recorded
  operation, plus a *late acquire* when an RMW's window closes: the join of the RMW's
  ms-connectivity component in its cluster (the RMWs on the location whose windows
  chain-overlap), including what the multi cluster before hands on. An instance is flagged iff
  `poss = vc ⊔ pd` orders it; a decision with an open RMW window on either side is held until
  the window closes. DR and SC instances alike (§6). Two singleton clusters in a row use the
  recorded chain only, so a kernel without overlapping windows gets no flag.
- **Soundness** (proof sketch in the note; **tested**, §5): F\* ⊆ flagged — under A1, A2w and A3 an
  unflagged instance is unordered in the execution's own happens-before, with the same class.
- **Pair-level**: a Race report (pc pair) is A2-uncertain iff every DR instance of it is flagged.
  **Tables**: at Race alone, a program whose this-run Race reports are all A2-uncertain moves to
  the `a2` column; at Race ∪ Latent only if, in addition, no latent report remains and each such
  report has an R1 or R3 certificate (reordered, one without would be Latent, still positive).
- **The other direction** (a manufactured chain edge hiding a race): not flagged — the flag marks
  reported instances only. Its exposure is bounded by the window count: none in a kernel
  without overlapping windows; otherwise the overlapping pairs on locations whose RMWs release
  or acquire are the hand-offs whose direction the trace does not fix (§3).

## 2. Calibration: the Sanitizer's own inversion rate

`python/testdata/lock_contention_a2.cu`, kernel `kcontend`: lane 0 of each warp takes a
device-scope CAS/EXCH lock with fenced critical sections (T13's lock), 16 acquisitions per
warp, 5 runs per level and job, the private runtime (`eval/baselines/setup/t14_handoffs.sh`;
logs `eval/results/t14-a2/handoffs_<job>.txt`). The critical sections run one at a time and each
begins after the successful CAS it spins on has returned, so the order of their read records is
their order; an adjacent pair is unordered on the trace exactly when the successful CAS was
recorded before the unlock it read from (`a2_window_count.py handoffs`). **Proved-in-effect** on
these 45 traces: every such instance is flagged, and each inverted hand-off gives exactly three
DR instances (RAW, WAR, WAW).

| contending warps | job 293129 (c51, 34acb00 runtime) | job 293145 (c53) | job 293414 (c58) | together | T13, NVBit, values |
|---|---|---|---|---|---|
| 2 (1 × 2) | 16 / 155 | 20 / 155 | 17 / 155 | 53 / 465 (11.4 %) | 0 / 155 |
| 4 (1 × 4) | 108 / 315 | 85 / 315 | 113 / 315 | 306 / 945 (32.4 %) | 4 / 315 (1.3 %) |
| 16 (4 × 4) | 353 / 1,275 | 349 / 1,275 | 352 / 1,275 | 1,054 / 3,825 (27.6 %) | 52 / 1,275 (4.1 %) |

(Job 293129 ran the 34acb00 runtime, libsanalyzer e946e20b329e5529, driver 580.95.05; jobs
293145 and 293414 the final one, d0a611d29766cce4, drivers 580.105.08 and 580.82.07. Denominators count every adjacent pair of critical sections,
as T13 did; a warp that takes the lock twice in a row cannot invert: 0, 10 and 11 such pairs in
job 293145, 0, 0 and 7 in job 293414.) The difference to T13's rates is not explained here —
the two instrumentations perturb the schedule differently, and T13's `atom_after` was not
faster than our collector overall (`eval/NVBIT_SPIKE.md` §5) — but for our collector's traces
NVBit's rates understate the exposure 7–25 times at 4–16 warps.

## 3. The window count over the kept dumps (step 4)

`a2_window_count.py count` over every program of the evcand store (P1–P6), both modes' dumps
(separate recordings), streaming the dumps; per program the counts are in
`eval/results/t14-a2/window_count.csv`, the tables in `eval/results/t14-a2/A2_TABLES.md`.
**Proved-in-effect** on 558 vector-clock and 593 scalar-clock program dumps (none failed).

| suite | dumps | programs with a cross-warp RMW pair | … with an overlap / on a sync location | overlapping cross-warp pairs | median per program | order-uncertain cross-warp successor edges | programs overlapping only via open-ended windows |
|---|---|---|---|---|---|---|---|
| P1 | vector (366) | 262 | 262 / 262 | 46,505,135 of 161,890,794 | 24.4 % | 2,865,232 of 5,920,046 | 0 |
| P2 | vector (58) | 41 | 41 / 37 | 611 of 15,711 | 100.0 % | 211 of 569 | 32 |
| P3 | vector (56) | 52 | 52 / 52 | 137,142,374 of 138,122,402 | 44.8 % | 106,445 of 780,353 | 0 |
| P4 | vector (18) | 18 | 18 / 18 | 23,126,835 of 4,639,212,649 | 25.3 % | 9,640,330 of 23,153,138 | 2 |
| P5 | vector (33) | 24 | 24 / 19 | 137 of 281 | 50.0 % | 74 of 119 | 4 |
| P6 | vector (27) | 0 | 0 / 0 | 0 of 0 | - | 0 of 0 | 0 |
| **all** | vector (558) | 397 | 397 / 388 | 206,775,092 of 4,939,241,837 | 29.9 % | 12,612,292 of 29,854,225 | 38 |
| P1 | scalar (388) | 285 | 285 / 285 | 328,498,343 of 551,389,306 | 23.5 % | 3,095,096 of 7,903,370 | 0 |
| P2 | scalar (58) | 41 | 41 / 37 | 603 of 15,714 | 100.0 % | 203 of 570 | 32 |
| P3 | scalar (58) | 54 | 54 / 54 | 205,949,252 of 207,872,802 | 45.4 % | 117,404 of 1,073,381 | 0 |
| P4 | scalar (28) | 28 | 28 / 28 | 886,646,517 of 5,950,931,035,952 | 13.4 % | 341,045,910 of 385,364,557 | 2 |
| P5 | scalar (33) | 24 | 24 / 19 | 137 of 281 | 50.0 % | 74 of 119 | 4 |
| P6 | scalar (28) | 0 | 0 / 0 | 0 of 0 | - | 0 of 0 | 0 |
| **all** | scalar (593) | 432 | 432 / 423 | 1,421,094,852 of 5,951,690,314,055 | 27.9 % | 344,258,687 of 394,341,997 | 38 |

Reading the table:
- *Cross-warp pairs* are same-location RMW pairs of different warps; *overlapping*: the later is
  recorded inside the earlier one's window. The pair-weighted rate is dominated by a few
  locations with millions of RMWs (the spinning locks of `matrix-multiplication-{racy,norace}-large`,
  scalar-clock dumps only: 168 M RMW records and 2.7·10¹² cross-warp pairs each, 92 % of all
  scalar-clock pairs); per program, the median overlap fraction is 29.9 % (vector-clock) and
  27.9 % (scalar-clock), the 90th percentile 100 %.
- Every program with a cross-warp same-location RMW pair has an overlap (397/397 vector-clock,
  432/432 scalar-clock); 388 (423) have one on a location whose RMWs release or acquire. The
  remaining 161 (161) programs have no such pair — for them A2w implies A2 and the flag is 0.
- The evcand dumps predate exit records (T3b), so a thread's last RMW has an open-ended window;
  38 programs overlap only through such windows (32 of them in P2). With exit records they would
  close at the exit.
- *Successor edges*, the brief's order-uncertain chain edges (consecutive RMWs on a location
  with overlapping windows): 12.6 M of 29.9 M successor edges in the vector-clock dumps are
  uncertain and cross-warp — the hand-offs whose direction the trace does not fix, the bound on
  the manufactured-edge risk.
- *Multi clusters (mixed)*: clusters of ≥ 2 RMWs, and those with a pair that is not morally
  strong (where the component join matters): 1,079 of 3.95 M (vector-clock), 77,917 of 8.92 M
  (scalar-clock). No kernel of the store has an exit record.
- P6 (cuHadron) has no RMW on a location shared by two warps.

## 4. The flag on the corpus (step 5)

`a2_window_count.py rescore`: every vector-clock kernel dump of T9's selection (the evcand and
`full-2026-09-22` stores as `latent_census.select_sources` picks them; 558 programs) through this
branch's `hb_oracle.py` (the a0969a9 file; it was on disk, unchanged since, before every
re-score job started) → the store `cuvein_traces/t14-after` (`hb_races` with `a2_uncertain`,
`"hb_a2": 1`), then `parallel.py analyze` of that store twice, with the base f127790 code (which
ignores the field) and with this branch's code. Per program: `eval/results/t14-a2/rescore.csv`;
the generated tables, with every program that has a flagged instance:
`eval/results/t14-a2/A2_TABLES.md`. **Proved-in-effect** on 558 programs, none failed (one P3
program exceeded the small array's 60 GB cap and was re-run alone, job 293189).

**The window count next to the flag, per suite** (vector-clock dumps; the window columns from §3;
"all flagged" = DR pc pairs with every instance flagged; the last column: programs whose
Race-alone positive rests on flagged reports only, by label; the window count covers the evcand
store, the re-score T9's selection — 366 against 365 P1 programs, and crs-cuda, P9, only in the
latter):

| suite | VC dumps counted | with a cross-warp RMW pair / an overlap / one in closed windows | median overlap | re-scored | DR instances | flagged | % | DR pc pairs / all flagged | programs with a flagged instance | Race-alone positives on flagged reports only (CLEAN / RACE label) |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 366 | 262 / 262 / 262 | 24.4 % | 365 | 8,481,582,346 | 3,877 | 0.000 | 1,170 / 0 | 15 | 0 / 0 |
| P2 | 58 | 41 / 41 / 9 | 100.0 % | 58 | 101,936 | 27 | 0.026 | 42 / 0 | 8 | 0 / 0 |
| P3 | 56 | 52 / 52 / 52 | 44.8 % | 56 | 9,575 | 0 | 0.000 | 14 / 0 | 0 | 0 / 0 |
| P4 | 18 | 18 / 18 / 16 | 25.3 % | 18 | 751,458 | 428,906 | 57.077 | 103 / 26 | 11 | 3 / 0 |
| P5 | 33 | 24 / 24 / 20 | 50.0 % | 33 | 16 | 0 | 0.000 | 13 / 0 | 0 | 0 / 0 |
| P6 | 27 | 0 / 0 / 0 | - | 27 | 97 | 0 | 0.000 | 5 / 0 | 0 | 0 / 0 |
| P9 | 0 | 0 / 0 / 0 | - | 1 | 98,324,936 | 0 | 0.000 | 155 / 0 | 0 | 0 / 0 |
| **all** | 558 | 397 / 397 / 359 | 29.9 % | 558 | 8,580,770,364 | 432,810 | 0.005 | 1,502 / 26 | 34 | 3 / 0 |

- The flag is concentrated where the windows matter: in P4 (the ScoR apps, spin locks and
  flag hand-offs) 57 % of the DR instances are flagged and 26 pc pairs have every instance
  flagged; elsewhere 3,904 instances in 23 programs (15 P1, 8 P2), and no pair.
- P1: 15 programs with a flagged instance, all RaceBug programs, no pair with every instance
  flagged — every P1 report is A2-robust. P2: 8 programs with 3–6 flagged instances each, none
  of a pair wholly; each has 3–4 RMWs whose only overlaps are open-ended windows (no exit
  records), the over-flag named in `design/a2_flag.md` §3. P3, P5, P6: no flagged instance.
- SC instances (under `generic`, the Indigo `CudaAtomic` strong load/store pairs of P1 and P3,
  T9): 56,767 of 24,011,081 flagged, in 16 P1 programs; none of the 200 SC pc pairs has every
  instance flagged.
- crs-cuda (P9, the pre-T3b dump, no RMW): 98.3 M DR instances, none flagged; still RACE, the
  exit-unaware false positive T3b fixed on fresh recordings.

**Verdicts** (vector-clock rows; verdict, report ids and class note compared):
- Base code (f127790) vs this branch on the same re-oracled dumps: 558 programs and 1,616 rows
  (id, rep; verdict, reports, report ids, notes without the a2 token) compared, **0 changed** — the flag changes no verdict (**proved-in-effect**).
- T9's committed re-score (T9 code on its own re-oracled dumps, `eval/results/t9-rescore/after`)
  vs this branch on t14-after: 554 programs and 1,604 rows (verdict, reports, report ids, class
  note) compared (T9 has no row for the four P1 1296n programs its oracle could not finish),
  **0 changed**.
- At Race ∪ Latent no program's positive rests on flagged reports only. At Race alone three do,
  all labelled race-free; in the tables they leave the FP count for the `a2` column:

| program | label | classes (this branch's note) | at Race ∪ Latent |
|---|---|---|---|
| `P4-matrix-multiplication-norace-small` | CLEAN | `structural:4;a2_uncertain=4:0` | stays RACE (FP): no R3 chain certifies the 4 pairs, so reordered they would be Latent |
| `P4-rule-110-norace-large` | CLEAN | `latent:13,structural:5;a2_uncertain=5:0` | stays RACE (FP): 13 latent reports (R3's release point, T12) |
| `P4-rule-110-norace-small` | CLEAN | `latent:1,structural:1;a2_uncertain=1:0` | stays RACE (FP): 1 latent report |

`make_tables.py`'s D2 table (`operating_points_section`, with the new `a2` columns) on these
rows (vector-clock; the function's pset list has no P2). With the base code's rows P4 reads
`5/9 / 9/9` at both points and `0 / 0` in both `a2` columns; with this branch's:

| pset | mode | Race u Latent FP / TP | a2 (R u L) FP / TP | Race alone FP / TP | a2 (R) FP / TP | latent | sc | n/a |
|---|---|---|---|---|---|---|---|---|
| P1 | cuVein-VC | 0/187 / 178/178 | 0 / 0 | 0/187 / 178/178 | 0 / 0 | 0 | 66 | 0 |
| P3 | cuVein-VC | 14/56 / 0/0 | 0 / 0 | 14/56 / 0/0 | 0 / 0 | 0 | 34 | 0 |
| P4 | cuVein-VC | 5/9 / 9/9 | 0 / 0 | 2/9 / 9/9 | 3 / 0 | 7 | 0 | 0 |
| P5 | cuVein-VC | 0/14 / 19/19 | 0 / 0 | 0/14 / 10/19 | 0 / 0 | 9 | 0 | 0 |
| P6 | cuVein-VC | 0/17 / 5/10 | 0 / 0 | 0/17 / 5/10 | 0 / 0 | 0 | 0 | 0 |
| P9 | cuVein-VC | 1/1 / 0/0 | 0 / 0 | 1/1 / 0/0 | 0 / 0 | 0 | 0 | 0 |

`P4-matrix-multiplication-norace-small` (the D15 case): its four DR pairs, 201,216 of 201,216
instances flagged, as step 5 expected. At Race alone it leaves the FP count (T9 made it an FP
there, `eval/T9_RESCORE.md` §2.3); at Race ∪ Latent it stays a false positive, as it was before
T9 (then as `latent`). The four pairs are volatile `LDG/STG.E.STRONG.SYS` data (T10: SC, §6).
`rule-110-norace-{small,large}`: the flagged pairs are volatile `STG.E.STRONG.SYS` →
`LDG.E.STRONG.SYS` hand-offs on `copy[]` (large: 0xd90/0x15d0, 0xdf0/0x1650, 0xe20/0x16d0,
0xed0/0x1750, 0x1050/0x1970 in `rule110Kernel`); the kernel's only RMWs are on the `comp[]`
flag words, which the owner sets with `atomicExch` (`ATOMG.E.EXCH`) and the neighbour polls
with `atomicAdd(…, 0)` (`ATOMG.E.ADD`) (`ScoR/benchmarks/rule-110/r110_kernel.cu:86-125`) —
RMWs of different warps on one word, in overlapping windows. Whether a given flagged instance
was really inverted cannot be told without the values (§9).

**Oracle cost.** Same dumps, one run each, different `normal` nodes: T9's re-score 31,566 s, this
one 23,643 s over the 554 programs both finished (×0.75); over the 63 programs T9 needed ≥ 60 s
for, ×0.67. T9's re-score ran its oracle before T9 aggregated `hb_races` (it wrote every
record): the four P1 1296n programs died of memory there and took 51–71 min at 7.9–8.6 GB
here. Where this oracle is slower, the kernels have large multi clusters (the late acquire
joins the component's clocks at every window close): ×5.28 on a P1 warp-level push program
(86.5 s → 456.6 s; 25 k RMW records, 4 k multi clusters), ×3.6 on a P3 `CudaAtomic` program
(145 k of its 148 k RMW records in 849 multi clusters). crs-cuda, without RMWs, took 6,335 s against
T9's 3,319 s (41.6 GB; not investigated).

## 5. Tests and parity

- **Green set** (CLAUDE.md A4, `eval/baselines/setup/t14_check.sh`), every trace re-recorded with
  the private runtime: 250 passed, 1 xfailed (`test_relaxed_handoff_should_race`, the I4 case),
  no failure, no skip (job 293144, c51, driver 580.95.05, libsanalyzer d0a611d29766cce4,
  collector c91568838f133228; log `eval/results/t14-a2/green_set_293144.txt`). The job ran the
  a0969a9 tree (its files written before the job started, committed after it unchanged; the
  build, job 293143, compiled that `pc_dependency_analysis.cpp`); f534851 and later touch no
  tested file. Earlier states of the branch: 249 + 1 xfail twice (jobs 292960, 293041).
  Baseline cited, not re-run: 238 + 1 xfail on the merged tree (48adefb).
- **Default tool path** (no `YOSEMITE_HB_TRACE`, A3): identical to the main runtime up to device
  addresses and dist on 2 ScoR programs, in all three check runs.
- **New tests** (`python/test_hb_substitutions.py`, all passing): hand-made traces for an inverted
  hand-off (flagged), no overlap (not flagged: the rtraw race), a decision held on the later RMW
  and on the earlier one (flagged / not flagged by the window's close), a scope mismatch (two
  block-scope RMWs of different blocks: not flagged), the block-leader lock through
  `__syncthreads` (flagged); a randomized check of 400 traces against every window-consistent
  coherence order; on the GPU, `test_lock_contention_every_dr_is_a2_uncertain` (step 5: the
  race-free lock with 16 contending warps, flagged count > 0, unflagged DR count 0, every Race
  verdict A2-uncertain), `test_lock_control_race_is_not_a2_uncertain` (a genuine race with
  closed windows: reported, not flagged) and `test_lock_contention_engine_matches_oracle`.
- **Randomized soundness check** (**tested**): the green-set test
  `test_a2_only_over_flags_randomized` (400 traces, seed 14) and a scratch copy of the same check
  with more traces (seeds 21–25, not committed): 10,000 random traces against the final flag (job
  293142, the a0969a9 oracle; 2–4 threads, 1–2 blocks, grid-, block- and none-scope RMWs on two
  words, plain and strong accesses), every window-consistent coherence order enumerated and
  `→co` computed by graph reachability: no reported instance that some order orders is left
  unflagged. 83,404 instances (6,346 SC), 6,577 flagged (157 SC), 5,852 of the flagged ordered
  by some order — 89 %. The earlier ms-blind join flagged 11,640 on the same traces (50 %
  ordered by some order); earlier DR-only versions were checked the same way, with no miss.
- **Engine == oracle for the new field** (**proved-in-effect**): the five engine==oracle
  comparisons of the green set (`test_sync_dominance.py` `_race_key`, `test_coherent_ldst.py`,
  `test_barrier_exit.py`, `test_cp_async.py` `test_engine_matches_oracle`,
  `test_hb_substitutions.py` `_engine_equals_oracle`) put `a2_uncertain` in the record key since
  2056042 and pass on every trace the green set records with the final runtime (the ScoR
  microbenchmarks, the coherent load/store, barrier-exit, cp.async and substitution kernels,
  and both lock kernels; the contention kernel had 507 of 507 DR instances flagged on the
  34acb00 runtime). Besides, the 15 lock traces of job 293414 (final runtime, c58): the engine's
  `hb_races`, `a2_uncertain` included, equal the oracle's on 15 of 15, with 1,446 flagged
  instances (`handoffs_293414.txt`, `engine_eq_oracle`).
- **Against T9's re-score** (**proved-in-effect**): 5,500 of 5,578 compared kernels have T9's
  instance count on every (a_pc, b_pc, kind, class, space) key and T9's second clock. On the
  other 78 (36 of them crs-cuda's) the key sets and the second clock are identical and T9's
  count never exceeds this one's (`a2_window_count.py t9keys`, job 293427): T9's t9-after dumps
  predate its aggregation and hold each distinct record tuple once; the aggregated count counts
  repeats.

## 6. DR and SC; the interaction with T10

D15 words the flag for a DR. It is computed for every reported instance, DR and SC alike: A2
concerns order, and the class is a static label the flag does not read. T10
(`fix/sidecar-strength`, unmerged; policy `token`) makes volatile `LDG/STG.E.STRONG.SYS`
accesses strong at `sys` scope, so a pair of them is SC instead of DR. **All numbers in this
report are under the base's policy `generic`.** After T10, the flagged pairs on volatile data
become SC and still carry `a2_uncertain` — among them the four `matrix-multiplication-norace-small`
pairs and the `copy[]` pairs of `rule-110-norace`. T10's own re-score
(`eval/SIDECAR_STRENGTH.md` on `fix/sidecar-strength`, "False positives removed") lists all three
programs of §4's `a2` column as leaving the Race columns in both modes, as SC reports
(informational, D2) — by T10's reclassification, not by the flag. So on the merged tree the `a2`
column is expected to lose those three; what else it holds under `token` is not measured here.
The lock test uses plain data, so its pairs are DR under both policies; T10's tests do not read
the flag.

## 7. For the merger

- **Files** likely to meet T10's hunks: `sanalyzer/src/tools/pc_dependency_analysis.cpp` (T10: the
  `my_coh` line in `process()`, members after `atom_scope`, `load_scopes`, `select_kernel`,
  `strong_scope`; T14: `Released`/`Race`/`Group`, the async functions, a block before `reset()`,
  `sync_group`, `conflict`, the window closes in `process()`, the RMW branch and publish,
  `stats`, `emit` — no overlapping hunk expected, several nearby); `python/hb_oracle.py` (T10: the
  docstring and `--strong-ldst` help; T14: none of those); `python/sync_dominance.py` (T10: the
  policy block, `coherent_scope`; T14: `_a2_flag` before `_observed`, two lines in `judge`);
  `python/test_hb_substitutions.py` (T10: the I1 fixture and its tests; T14: the module
  docstring, the key of `_engine_equals_oracle`, the new tests at the end — the I1 fixture is not
  used by T14); `python/test_coherent_ldst.py`, `python/test_sync_dominance.py` (T14: one line
  each, the engine==oracle key). A trial merge (`git merge-tree --write-tree`) of this branch's
  head with T10's `f2a5bde` reports no conflict.
- **Rebuild `libsanalyzer` from the merged tree** and install that one (the collector needs no
  change: RPATH); then the green set: 238 on the base, T14 adds 12 (250 here), T10 reports 275,
  so expect 287 passed and the one xfail if nothing interacts. Under T10's policy the flagged
  volatile pairs become SC (§6).
- `a2_window_count.py tables` needs the per-program JSONs copied to
  `eval/results/t14-a2/detail/` (gitignored; `build_logs`-style copy from BeeGFS).

## 8. Commands

```
# private runtime, green set, default path (GPU)
W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t14-build-%j.log eval/baselines/setup/t9_build.sh
W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t14-check-%j.log eval/baselines/setup/t14_check.sh
# the Sanitizer's inversion rate, and engine == oracle on its traces (GPU; three jobs)
W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t14-handoffs-%j.log eval/baselines/setup/t14_handoffs.sh
# window count and re-score (CPU)
W=<worktree> STEP=count sbatch --array=0-23 eval/baselines/setup/p_t14_a2.sh
W=<worktree> STEP=rescore SIZE=small FORCE=1 sbatch --array=0-23 eval/baselines/setup/p_t14_a2.sh
W=<worktree> STEP=rescore SIZE=big FORCE=1 sbatch --array=0-17 --exclusive eval/baselines/setup/p_t14_a2.sh
.env/bin/python eval/baselines/a2_window_count.py count --force --mem-gb 170 --id <3 largest>   # exclusive node
.env/bin/python eval/baselines/a2_window_count.py rescore --force --mem-gb 170 --id <1 P3>      # exclusive node
.env/bin/python eval/baselines/a2_window_count.py t9keys                                       # normal node
# verdicts: base code (git archive f127790 python eval/baselines eval/aggregate.py) and T14 code
W=<worktree> CODE=<base tree> WHICH=base sbatch --array=0-15 eval/baselines/setup/p_t14_analyze.sh
W=<worktree> WHICH=t14 sbatch --array=0-15 eval/baselines/setup/p_t14_analyze.sh
# the programs whose re-score finished after the analyze arrays, both codes
W=<worktree> CODE=<base tree> WHICH=base IDS=<id file> TAG=late sbatch eval/baselines/setup/p_t14_analyze.sh
W=<worktree> WHICH=t14 IDS=<id file> TAG=late sbatch eval/baselines/setup/p_t14_analyze.sh
.env/bin/python eval/baselines/a2_window_count.py tables                                       # login node
```

## 9. What remains unverified

- **A2w itself.** The flag assumes an RMW takes effect before its thread's next record; T13 saw no
  violation under NVBit (30 runs, one lock). The Sanitizer's callback need not wait for the
  atomic's result, and a `RED` (no destination register) may stay in flight longer; not
  measured.
- **Soundness** is a hand proof (sketch in `design/a2_flag.md`) plus the randomized check; the
  random traces have no barriers, exits or multi-lane records (those paths are covered by the
  hand-made tests only).
- **The over-flag on the corpus** cannot be measured without values; on random traces 11 % of the
  flagged instances are ordered by no window-consistent order.
- **Missing exit records**: the evcand dumps predate T3b, so last-RMW windows are open-ended
  (conservative); a fresh recording with exit records would close them.
- **P7/P9** (Rodinia, HeCBench) are not in the window count: the kept dumps are 100–300 GB
  partial prefix dumps (`full-2026-09-22`), hours each at the count's ~27 MB/s; and 8 of 9 P9 and
  all P7 programs have no vector-clock dump for the flag (T5b).
- **Scalar-clock rows** were not re-analysed: their dumps have no `hb_races`, so `_a2_flag` returns
  None and the note gains no token — unchanged by construction, not re-measured on the corpus.
- The manufactured-edge direction (a hidden race) is bounded (§3), not enumerated: that needs a
  "certain" clock, or the value-recording collector (D15, post-submission).
- T10 is not merged: the numbers under policy `token` are not measured (§6).

## 10. Same source, two collectors (T18, 2026-10-01)

The corpus example of A2: one program, one source, two builds of the collector, two different
complete traces. `race_interblock_none-lock_rtraw` (ScoR; block 0 `lock; read; unlock; data[0]=1`,
block 1 `lock; read; unlock`) recorded five times per runtime, vector-clock mode, one node (c58,
RTX 4060 Ti), `setup/t18_rtraw_schedules.sh`, verdicts by `eval/baselines/t18_rtraw_verdicts.py`:

| runtime | device code in the record callback | events | outcome (5 of 5 runs identical) |
|---|---|---|---|
| installed by T18 (collector c9b862f9, default fatbin a2d7368b = the pre-T15 device code) | none for the late key | 15 | one report: WAR, SC, `latent-sc`; `hb_races` empty (the run's lock hand-off ordered it); no instance, so nothing to flag |
| the runtime of 96698c1 (T15 collector f2933966, default fatbin e9634312 with the late-key code), rebuilt from the `*.pre-t18-*` backups as a private mirror | late-key branch + second `__syncwarp` | 14 | two reports: WAW DR `structural` and WAR SC `sc`; both `a2_uncertain`, flag equal to count (1/1 each) |

Both traces are complete (no record lost, `tv_violation` none). 96698c1 found the cause in the
records: the earlier runtime has block 0 spin five times on the lock CAS before it enters, the
later one four, and the fourth CAS (recorded before block 1's unlock) is the one that
succeeds -- a successful lock CAS whose trace position precedes the unlock it read from, i.e. an
inversion of coherence order by overlapping RMW windows (A2). The program, the binary and the
hardware are the same; only the time the callback spends before the instruction differs, and
each build lands in one schedule (T15, schedule determinism). The extra reports of the second
schedule are exactly the ones the flag exists for: every one is `a2_uncertain`.

What this does and does not show. It shows that a litmus verdict on a lock idiom is not a
property of the program under this collector, and that the flag marks precisely the reports that
move. It does **not** show that the first schedule's single report is A2-robust: with no
`hb_races` instance the pair has nothing to flag, and its `latent-sc` class rests on the run's
hand-off order -- the order A2 makes uncertain. So "both traces flagged" does not hold: the T15
schedule's reports are flagged, the pre-T15 schedule's one report is latent and unflagged.

Consequence for the tests (`python/a2_aware.py`): the litmus assertions check that the reports
which are not `a2_uncertain` match the label, and that any extra report carries `a2_uncertain`
equal to its count; the project's own litmus kernels force the hand-off order with a flag spin.
The four tests that failed after the T17 install pass on the installed runtime and on the same
runtime with `YOSEMITE_HB_LATE_SEQ=atomic` (305 passed, 2 skipped, each).

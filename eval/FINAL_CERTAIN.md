# X2 — the sound column: P4 and P5 recorded under the certain clock

Branch `eval/final-certain` from `cuVein` 4094187 (X0 merged; the code freeze). Unmerged — Jeffery
merges. Written 2026-10-14. Nothing under `sanalyzer/`, `nv-compute/` or `python/hb_oracle.py`
changed; the changes are in the harness (`eval/baselines/`) and the generated tables.
Labels: **proved-in-effect** (an invariant checked over N real traces), **tested** (a specific
verdict asserted), **unverified**.

| | |
|---|---|
| runtime (installed, d38d057) | libsanalyzer `2201fcb7d57ae783`, collector `ee78cb899e8a0a65`, fatbin `a2d7368bc1c61986` (printed at the head of every job log) |
| sweep | job 311939, node **c74** (RTX 4060 Ti 16 GB, sm_89, driver 580.82.07, CUDA 13.3, EPYC 7302P, 125 GB), 2026-10-13 17:09–21:11, 4 h 01 m, COMPLETED; harness commit 65dbd23 |
| same-trace check | job 312216, node c26 (`rtx4060ti8g`, RTX 4060 Ti pinned with `pin8g.sh`, sm_89, driver 615.71.09), 2026-10-14 |
| stores (BeeGFS) | `/mnt/beegfs/fzheng4/cuvein_traces/final-certain`, `…/final-certain-recorded`, `/mnt/beegfs/fzheng4/x2-same-trace` |
| rows | `eval/results/final-certain/`, `eval/results/final-certain-recorded/`, `eval/results/final-certain-invariant/` (`per_program.csv`, `added_pairs.csv`, `same_trace.json`) |
| confirm details | `eval/baselines/confirm_final_certain/`, `…/confirm_final_certain_recorded/` (gitignored; regenerable with `parallel.py analyze` from the stores) |

## Summary

**Sentence for the paper.** *Recorded under the certain clock — an atomic hand-off is taken only
when the two RMWs' issue windows do not overlap, so no race of the run is missed under A2w — the
61 ScoR programs keep every verdict at Race alone but one: P4 (applications) 14/14 TP, 2/14 FP, as
under the recorded clock; P5 (litmus + canary) 4/19 TP, 1/14 FP against 3/19, 1/14. The one move,
`race_interblock_none-lock_rtraw`, rests on a report the recorded run's lock hand-off orders — the
plain stores inside the two critical sections — while the rtraw pair itself is a strong conflict:
on these suites the sound operating point costs nothing at Race alone and gains no real race.*

1. **Step 2 (policy markers), proved-in-effect: 0 violations.** All 369 kernel JSONs of the certain
   store carry `hb_gate_policy: certain`, all 4,260 `hb_races` records `gate_policy: certain`, all
   369 `hb_stats` blocks `gate_policy: certain`, all 61 `meta.json` asked for `certain`, and all 183
   rows (120 CLEAN, 63 RACE, no TIMEOUT/ERROR) note `gate_policy=certain`. The recorded store: 369 /
   3,338 / 369 / 61 / 183 the same with `recorded`, and no row carries a `gate_policy` note. This
   needed a harness fix first (§1): before it, only rows *with reports* carried the note, so a
   CLEAN certain row read as a recorded one and dropped out of the sound column.
2. **Step 3 (the invariant), proved-in-effect on 61 programs: 0 violations** at the pc-pair level —
   every pc pair the recorded run reports as a Race or a Strong conflict, the certain run reports as
   well. Three programs first showed as violations at the harness's dedup key; in each the *same* pc
   pair is reported under both policies with another memory-space label (the label is the current
   pc's space and flips with the pair's orientation, §3). The certain clock adds **23 pc pairs on 8
   programs: 1 DR, 22 SC**; every instance of 22 of them is `a2_uncertain`; the exception (one SC
   instance on `reduction-norace-small`) is a schedule effect, shown on one trace in §4.
3. **Verdicts**: 1 of 61 moves at either point — `race_interblock_none-lock_rtraw`, CLEAN → RACE.
   c74 lands in X4's schedule B (the hand-off windows overlap; 3 of 7 chain edges refused): the
   rtraw pair (0x140 / 0x340) becomes a Strong conflict (WAR, SC, 1 instance, flagged) and the DR
   that makes the program RACE is the `dummy` WAW 0x170 / 0x2f0 inside the two critical sections
   (1 instance, flagged) — ordered by the fenced lock in every schedule. X4's correction of
   `eval/CERTAIN_CLOCK.md` holds on this sweep (§6).
4. **Step 4 (the column)**: `make_tables.py --certain-results eval/results/final-certain` writes
   section 3 of `eval/BASELINES_SUMMARY.md` — Race u Latent / Race alone / **Race (sound)** per suite;
   P4 14/14, 2/14, 0, 0 and P5 4/19, 1/14, 0, 0 under the certain clock; the other suites read
   `= Race alone` with footnote (b) citing `eval/CERTAIN_CLOCK.md`'s re-score; footnote (c) names
   the rtraw positive as resting on A2-uncertain reports only. **X1's P4/P5 rows** (61 programs,
   vector-clock) **agree in verdict with this job's recorded leg on 61 / 61** at Race u Latent and
   at Race alone; report counts differ on two programs (schedule).
5. **Cost**: the certain run costs what the recorded run costs — tool wall summed over all reps
   5,673 s against 5,710 s (0.993×), per program 0.85–1.34×, peak RSS 0.99–1.15×.

## 1. What ran

`eval/baselines/setup/p_final_certain.sh` (one job, one node, two legs in sequence):

| leg | `YOSEMITE_HB_GATE_POLICY` | store | rows | confirm | wall |
|---|---|---|---|---|---|
| 1 | `certain` | `cuvein_traces/final-certain` | `eval/results/final-certain/` | `confirm_final_certain/` | 6,979 s |
| 2 | `recorded` (set explicitly) | `cuvein_traces/final-certain-recorded` | `eval/results/final-certain-recorded/` | `confirm_final_certain_recorded/` | 6,910 s |

Both legs: `parallel.py run --pset P4,P5 --reps 3 --confirm --timeout-floor 1200 --timeout-cap 1200`,
`BASELINE_MODES=vector-clock`, `BASELINE_HB_DUMP=0` (no-dump: `HbClock`'s aggregates; verdicts from
them since X0), `YOSEMITE_HB_STATS=1`; every other HB knob unset. `blib.base_env` copies the
environment and pops only the mode/trace/scope/dump knobs, so `YOSEMITE_HB_GATE_POLICY` and
`YOSEMITE_HB_STATS` reach the collector, which reads the policy once at start
(`eval/CERTAIN_CLOCK.md` §3); the dumps confirm it (step 2).

**Deviation from the brief: `--timeout-floor 1200`.** The harness's per-program timeout is
`min(max(10 × native, floor), cap)`; with the default floor (120 s) the ScoR apps of sub-second
native time are killed at 120 s, not at the 1,200 s cap. `matrix-multiplication-norace-large` took
900–968 s per rep under the certain clock (946–1,036 s recorded) and would have been a TIMEOUT in both
legs. X1 runs with the same floor = cap for the same reason, so the two sweeps are comparable.
`FLOOR=120` restores the harness default.

**Harness fix (commit 65dbd23), needed for step 2.** `run_cuvein.classes_note` appends
`gate_policy=certain` only when a row has reports, so a CLEAN, TIMEOUT or ERROR row of a
certain-policy run carried no marker, `make_tables` loaded it as a recorded row, and
`--certain-results` dropped it: the sound column would have counted only the programs with reports.
Now `parallel.py` records the requested policy (and `YOSEMITE_HB_STATS`) in `meta.json`;
`analyze_one` notes `gate_policy=<p>` on every vector-clock row of a non-recorded run, cross-checked
against the policies the analysed kernel JSONs carry (`_analyze_reports(with_policy=True)`); a
disagreement is noted `gate_policy=mismatch(...)`, which `make_tables` never reads as certain; the
confirm JSON gains `gate_policy`. Recorded rows stay unnoted, so every existing store re-scores
unchanged. `run_cuvein.run_one` does the same.

## 2. Step 2 — the policy markers

`eval/baselines/final_certain.py check` (in the job, on c74):

```
check …/final-certain policy=certain: 61 programs, 369 vector-clock kernel JSONs, 4260 hb_races records;
  183 vector-clock rows {'CLEAN': 120, 'RACE': 63}; HB_STATS (hb_stats.hb_clock) in 369 of 369 kernel JSONs;
  hb_chain summed {'edges': 388728891, 'uncertain': 361125875, 'unsafe': 239015, 'refused': 361364890, 'open': 0, 'xwarp': 344024588}
check: 0 violations
check …/final-certain-recorded policy=recorded: 61 programs, 369 vector-clock kernel JSONs, 3338 hb_races records;
  183 vector-clock rows {'CLEAN': 123, 'RACE': 60}; HB_STATS (hb_stats.hb_clock) in 369 of 369 kernel JSONs;
  hb_chain summed {'edges': 387607425, 'uncertain': 360064572, 'unsafe': 199777, 'refused': 0, 'open': 0, 'xwarp': 343398278}
check: 0 violations
```

What `check` asserts: every `meta.json` asked for the leg's policy and is no-dump; every
vector-clock kernel JSON has `hb_gate_policy` = the policy, no `hb_events`, and `hb_stats.hb_clock.
gate_policy` = the policy; every `hb_races` record has `gate_policy` = the policy; every
vector-clock row of the leg notes `gate_policy=certain` (certain leg) or carries no `gate_policy`
(recorded leg). The certain clock refused 93.0 % of the 388.7 M chain edges (0 open-ended: every
dump has exit records); the recorded leg's counters show the same population (360.1 M uncertain of
387.6 M), none refused.

## 3. Step 3 — the invariant and the per-program table

`final_certain.py invariant`: per program, the certain run's reported pc-pair set — Race reports
(class `structural` / `model_bug`) and Strong conflicts (class `sc`) from the confirm details — must
contain the recorded run's. The same at Race u Latent (`latent`, `latent-sc` included) is listed as
a note. For the pairs the certain run adds, the certain store's `hb_races` aggregates give the
instances and how many are `a2_uncertain`.

**Result: 61 programs comparable, 0 violations at the pc-pair level, 0 at Race u Latent.**

*The dedup label.* Run first at the harness's dedup key (pc pair + memory space), three programs
showed a "lost" pair: `graph-connectivity-racy-large` (recorded `shared:0x3f0-0x5d0` WAW, certain
`global:…`), `graph-connectivity-racy-small` (the reverse) and `uts-racy-large` (three SC pairs to
0x3090, recorded `global` RAW, certain `shared` WAR). In each the same pc pair with the same class
is reported under both policies; only the label differs: `aggregate._dedup_key` takes the memory
space of the report's *current* pc, which flips with the pair's orientation in the run (the
race type flips with it). The brief's invariant is over the pc-pair set, so `final_certain.py`
keys on the unordered pc pair and counts label flips separately: 5 pairs on 3 programs.

**What the certain clock adds (`added_pairs.csv`): 23 pc pairs on 8 programs.**

| program | added pairs | class | instances | `a2_uncertain` |
|---|---|---|---|---|
| P4 `reduction-norace-large` | 4 | SC | 1,152 | 1,152 |
| P4 `reduction-norace-small` | 6 | SC | 801 | 800 (§4: the one unflagged instance is the schedule) |
| P4 `reduction-racy-large` | 2 | SC | 160 | 160 |
| P4 `reduction-racy-small` | 2 | SC | 160 | 160 |
| P4 `rule-110-norace-large` | 5 | SC | 65,593 | 65,593 |
| P4 `rule-110-norace-small` | 1 | SC | 272 | 272 |
| P5 `norace_interblock_lock_waw` | 1 | SC | 1 | 1 |
| P5 `race_interblock_none-lock_rtraw` | 2 | 1 SC (0x140/0x340, WAR; recorded: `latent-sc`), 1 DR (0x170/0x2f0, WAW) | 2 | 2 |

So the certain clock adds what `eval/CERTAIN_CLOCK.md` §5 found on the kept dumps: SC pairs on the
volatile data of `reduction` and `rule-110` and on `norace_interblock_lock_waw` (T16's main set
also had two interwarp block-lock litmus; here they add nothing), and on rtraw an SC plus the
`dummy` DR. `matrix-multiplication-norace-small`'s 4 SC pairs are reported by the recorded run as
well here (`sc:4` in both legs). No pair of P4 `1dconv`, `graph-*`, `matrix-multiplication`, `uts`
or of the other 31 P5 programs is added.

**Verdicts at both operating points.** Race alone and Race u Latent are computed by `make_tables`'
own functions from the rows. One program moves at each point, the same one:
`P5-race_interblock_none-lock_rtraw`, CLEAN (recorded) → RACE (certain). No verdict is lost.
Unflagged instance counts of the common pairs differ between the two recordings on 10 programs
(the four `uts` programs on nearly every pair, `matrix-multiplication-racy-*` on 6 pairs each, four others on 1–2): two recordings, two schedules (§4).

The full per-program table is in the appendix; the programs with any difference:

| program | label | Race alone rec / cert | R u L rec / cert | Race u SC pairs rec / cert | added (DR / SC) | added unflagged instances | label flips | chain edges refused / total (certain) |
|---|---|---|---|---|---|---|---|---|
| P4-graph-connectivity-racy-large | RACE | RACE / RACE | RACE / RACE | 8 / 8 | 0 (0 / 0) | 0 | 1 | 2,293,669 / 2,361,152 |
| P4-graph-connectivity-racy-small | RACE | RACE / RACE | RACE / RACE | 8 / 8 | 0 (0 / 0) | 0 | 1 | 1,697 / 3,422 |
| P4-reduction-norace-large | CLEAN | RACE / RACE | RACE / RACE | 15 / 19 | 4 (0 / 4) | 0 | 0 | 13,327 / 17,725 |
| P4-reduction-norace-small | CLEAN | RACE / RACE | RACE / RACE | 13 / 19 | 6 (0 / 6) | 1 | 0 | 2,146 / 3,267 |
| P4-reduction-racy-large | RACE | RACE / RACE | RACE / RACE | 17 / 19 | 2 (0 / 2) | 0 | 0 | 12,717 / 17,949 |
| P4-reduction-racy-small | RACE | RACE / RACE | RACE / RACE | 17 / 19 | 2 (0 / 2) | 0 | 0 | 1,986 / 3,011 |
| P4-rule-110-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 5 / 10 | 5 (0 / 5) | 0 | 0 | 17,190 / 1,968,266 |
| P4-rule-110-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 2 | 1 (0 / 1) | 0 | 0 | 225,905 / 491,656 |
| P4-uts-racy-large | RACE | RACE / RACE | RACE / RACE | 80 / 80 | 0 (0 / 0) | 0 | 3 | 9,326,082 / 11,089,714 |
| P5-norace_interblock_lock_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 1 | 1 (0 / 1) | 0 | 0 | 3 / 6 |
| P5-race_interblock_none-lock_rtraw | RACE | CLEAN / RACE | CLEAN / RACE | 0 / 2 | 2 (1 / 1) | 0 | 0 | 3 / 7 |

(`reduction-norace-*` is RACE under both policies: the ticket `atomicInc` with no acquire after it,
D11, footnote (9) of table 1.)

## 4. Same trace: the differences that are not the policy

The two legs are two recordings, so a difference between them can be the policy or the schedule.
On one trace T16 proved and tested the shape of the difference: the certain clock reports a superset,
and every instance it adds is `a2_uncertain` (`eval/CERTAIN_CLOCK.md` §1, §4). Two observations of
§3 do not have that shape: the added SC pair 0xa20 / 0x1680 of `reduction-norace-small` with one
**unflagged** instance, and the unflagged-instance counts of common pairs that differ on 10
programs. `eval/baselines/setup/x2_same_trace.py` (job 312216, node c26 — `rtx4060ti16g` was fully
allocated by X1 — `rtx4060ti8g`, the RTX 4060 Ti pinned, driver 615.71.09, the installed runtime)
recorded 9 of the programs involved 3 times under each policy **with the lossless dump**
(`YOSEMITE_HB_DUMP=1`; otherwise the harness's own extraction and environment) and replayed every
dump with `python/hb_oracle.py` (frozen) under both policies:

| check | result |
|---|---|
| recordings / kernel dumps | 54 / 330 (`reduction-norace-small`, `matrix-multiplication-racy-small`, `rule-110-racy-small`, `graph-coloring-racy-large`, `graph-connectivity-racy-large`, `uts-racy-small`, `uts-norace-small`, `race_interblock_none-lock_rtraw`, `norace_interblock_lock_waw`) |
| `HbClock` == oracle under the dump's own policy (T16's parity key with counts and `a2_uncertain`; sync pairs; `hb_chain`) | **330 / 330** |
| same dump: oracle(certain) ⊇ oracle(recorded) at the aggregate key with counts, equal sync pairs, equal unflagged instances per key | **330 / 330** |
| instances over all dumps, oracle(recorded) → oracle(certain) | 31,436,637 → 31,446,315; unflagged 31,435,298 under both: every one of the 9,678 added instances is `a2_uncertain` |

**The reduction pair is the schedule.** HbClock reports 0xa20 / 0x1680 (SC, 1 instance, unflagged)
in all three recordings made under the **recorded** policy and in one of the three made under the
certain policy; where it appears, it appears under both replays of that dump. In the sweep it
happened to be present in the certain leg and absent from the recorded one; on c26 it is present
in more recorded-policy recordings than certain-policy ones. Its presence does not follow the
policy, and on each dump both replays agree on it. Per program and policy, the three recordings give
**one** pc-pair set (`reduction-norace-small` under the certain policy: two) but **three different**
unflagged-instance profiles for 6 of the 9 programs under either policy (`matrix-multiplication-
racy-small`, `rule-110-racy-small`, `graph-coloring-racy-large`, `graph-connectivity-racy-large`,
`uts-racy-small`, `uts-norace-small`; `reduction-norace-small` one under recorded, two under certain;
the two P5 litmus one): instance counts vary run to run under one policy, which is what §3's
common-pair differences are.

So the cross-recording differences of §3 are the schedule, the policy's own effect is exactly the
flagged population on every dump examined, and the invariant holds on one trace with no exception
(**proved-in-effect** on 330 kernel dumps of 9 programs). `race_interblock_none-lock_rtraw` on c26:
0 → 2 instances, both flagged, on all 6 dumps — c26 lands in X4's schedule B like c74. The larger
programs with differing counts (`uts-*-large`, `matrix-multiplication-racy-large`) were not
re-recorded with the dump; the attribution there is by the same mechanism (§9).

## 5. Step 4 — the column, and X1

`make_tables.py --certain-results eval/results/final-certain` (login node) regenerates
`eval/BASELINES.md` and `eval/BASELINES_SUMMARY.md`. The summary gains **section 3, "cuVein
(vector-clock) at three operating points"** (`sound_points_section`, written only when
certain-policy rows are loaded; without the option both files are byte-identical to HEAD's
`make_tables.py` on the same data, **tested** by `cmp` before and after the change): per suite, in
table 1's cell format, Race u Latent, Race alone and Race (sound). P4: **14/14, 2/14, 0, 0**; P5:
**4/19, 1/14, 0, 0**; every other suite `= Race alone (b)`. Footnotes: (a) the X2 recording and
its schedule caveat; (b) the other suites by `eval/CERTAIN_CLOCK.md` §5–6 (the kept dumps of 594 +
97 programs, reports added only on ScoR, no verdict of P1, PI, P3, P6, P7, P9 moves; four P7/P9
programs recorded under both policies, CLEAN under both; programs without a kept vector-clock dump
are not covered); (c) the Race (sound) positives every Race report of which is `a2_uncertain` —
here `P5-race_interblock_none-lock_rtraw` — generated from the certain row's own notes.
`eval/BASELINES.md`'s D2 table gains T16's `Race (sound)` / `R u L (sound)` / `n (sound)` columns
from the same rows.

**The recorded columns of the committed tables are stale for this purpose.** `eval/results/
baselines-*.csv` predate T9: at Race alone most of their cuVein rows are `n/a` (no class note), so
the committed section 3 shows P4 / P5 Race alone as `0/0` / `-` with 14 / 19 `n/a`. The table the
paper uses is the one regenerated after X1's rows are merged into `eval/results/` (X1's
`p_final_post.sh`): rerun `make_tables.py --certain-results eval/results/final-certain` then. With
X1's P4/P5 rows as the recorded columns (computed with the same function, login node) the rows read:

| test suite | Race u Latent | Race alone | Race (sound) |
|---|---|---|---|
| ScoR applications — 28 program-inputs (7 codes) | 14/14, 2/14, 0, 0 | 14/14, 2/14, 0, 0 | 14/14, 2/14, 0, 0 (a) |
| ScoR micro-benchmarks + canary — 33 programs | 3/19, 1/14, 0, 0 | 3/19, 1/14, 0, 0 | 4/19, 1/14, 0, 0 (a) |

and identically with this job's recorded leg in place of X1's. (P5's 16 other labelled races are
Strong conflicts under T10's token rule — D2, amended — hence 3/19 at both recorded points.)

**X1 against this job's recorded leg** (`verdict_diff.py` on X1's `wt-x1/eval/results/final/*.csv`
as of 2026-10-14 01:20, all 61 P4/P5 programs present):

```
verdict_diff.py '…/wt-x1/eval/results/final/*.csv' 'eval/results/final-certain-recorded/*.csv' \
    --pset P4,P5 --mode vector-clock --collapse --verdict-only
A: 61 rows  B: 61 rows  common: 61  only-A: 0  only-B: 0  differing: 0  (fields compared: verdict, race-alone)
```

Identical verdicts at both points on 61 / 61. With report counts compared (`--collapse` without
`--verdict-only`) two programs differ: `graph-coloring-racy-small` 13 (X1, c51) vs 12 (c74) and
`graph-connectivity-racy-small` 9 (X1, c78) vs 10 (c74) deduped reports, both RACE — schedule
differences between nodes and runs, not verdicts. X1's rows were read from its worktree while X1
was still running (none of its P4/P5 vector-clock rows is a TIMEOUT, so its 5,400 s long pass should
not replace them); if X1's post-processing overrides any P4/P5 row, rerun the command.

## 6. The rtraw program, and `eval/CERTAIN_CLOCK.md`

`eval/CERTAIN_CLOCK.md` (§0 and §5) says the certain clock turns `race_interblock_none-lock_rtraw`
"from Latent into a Race (a TP gained) … reports the rtraw pair as a `structural` DR plus an SC
pair". X4 (`eval/FINAL_RTRAW.md` §4, branch `eval/final-rtraw`) showed that this is wrong in detail
and that it depends on the node. This sweep confirms X4 on c74, which lands in X4's schedule B (the
hand-off windows overlap, as on c62 / c77):

| | recorded leg (c74) | certain leg (c74) |
|---|---|---|
| rtraw pair 0x140 / 0x340 | `latent-sc` (Latent, SC) | **Strong conflict** (WAR, SC, 1 instance, `a2_uncertain` 1/1) |
| `dummy` 0x170 / 0x2f0 (inside the critical sections) | not reported | **Race** (`structural`, WAW, DR, 1 instance, `a2_uncertain` 1/1) |
| chain edges refused | 0 of 7 | 3 of 7 |
| program at Race alone / R u L | CLEAN / CLEAN | RACE / RACE |

The program-level RACE under the certain clock — the P5 "+1 TP" of the sound column — rests on the
`dummy` pair, which the fenced lock orders in every schedule; it is the certain clock's completeness
price on a contended hand-off, and the rtraw pair itself is a strong conflict (informational under
PTX counting, a report under ScoRD's notion). On a node in X4's schedule A (c58) the certain clock
accepts the hand-off and the program stays CLEAN. Footnote (c) of the new summary section names
this positive. The correction of `CERTAIN_CLOCK.md` itself is left to Jeffery (X4 drafted the text
in `FINAL_RTRAW.md` §4); this branch does not edit T16's report.

## 7. Cost of the certain run

Same node, same job, the two legs back to back (c74, Zen 2 host):

| | certain | recorded |
|---|---|---|
| leg wall (61 programs, native + extraction + 3 reps + analysis) | 6,979 s | 6,910 s |
| tool wall, sum over all 183 rows | 5,673 s | 5,710 s |
| per program, median-rep wall ratio certain / recorded | min 0.850, median 1.023, max 1.338 | |
| largest programs (median rep) | `matrix-multiplication-norace-large` 919 s, `-racy-large` 485 s, `uts-racy-large` 181 s | 959 s, 461 s, 177 s |
| per program, peak RSS ratio | 0.986 – 1.149 | |

The extremes are small programs (`rule-110-*-large` and `graph-connectivity-norace-large`, ~20–26 s,
1.29–1.34×; `matrix-multiplication-norace-small` 0.85×); one run per rep, so the per-program ratios
carry run-to-run noise. Consistent with `eval/CERTAIN_CLOCK.md` §6 (±1 % on four P7/P9 programs).

## 8. Commands

```
# worktree (runtime dirs symlinked to the main checkout: lib build .env ScoR cuHadron nv-compute/lib,
# eval/baselines/{corpora,bin,inputs,setup/tools})
git worktree add .claude/worktrees/wt-x2 -b eval/final-certain cuVein
# the sweep: both legs, then steps 2 and 3 on the node (BeeGFS)
sbatch eval/baselines/setup/p_final_certain.sh                          # job 311939, c74
#   = for leg in certain recorded:
#     YOSEMITE_HB_GATE_POLICY=$leg BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag> \
#     BASELINE_MODES=vector-clock BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
#     .env/bin/python eval/baselines/parallel.py run --pset P4,P5 --reps 3 --confirm \
#         --timeout-floor 1200 --timeout-cap 1200 --tag <tag> --results-dir eval/results/<tag> \
#         --confirm-dir eval/baselines/<confirm>
# steps 2 and 3 again from a normal node after the pc-pair fix of final_certain.py
srun -p normal -n 1 -c 2 -t 00:30:00 .env/bin/python eval/baselines/final_certain.py check \
    --store /mnt/beegfs/fzheng4/cuvein_traces/final-certain --results eval/results/final-certain --policy certain
srun -p normal -n 1 -c 2 -t 00:30:00 .env/bin/python eval/baselines/final_certain.py invariant \
    --certain-store /mnt/beegfs/fzheng4/cuvein_traces/final-certain \
    --recorded-store /mnt/beegfs/fzheng4/cuvein_traces/final-certain-recorded \
    --certain-confirm eval/baselines/confirm_final_certain \
    --recorded-confirm eval/baselines/confirm_final_certain_recorded \
    --certain-results eval/results/final-certain --recorded-results eval/results/final-certain-recorded \
    --out eval/results/final-certain-invariant
# section 4: the same-trace check (rtx4060ti16g was fully allocated by X1)
PIN8G=1 sbatch -p rtx4060ti8g -w c26 eval/baselines/setup/x2_same_trace.sh   # job 312216
# step 4
.env/bin/python eval/baselines/make_tables.py --certain-results eval/results/final-certain
.env/bin/python eval/baselines/verdict_diff.py '<X1>/eval/results/final/*.csv' \
    'eval/results/final-certain-recorded/*.csv' --pset P4,P5 --mode vector-clock --collapse --verdict-only
```

## 9. What remains unverified

- **A2w** — the soundness of the certain clock rests on it (an RMW has taken effect by its thread's
  next record); unchanged from `eval/CERTAIN_CLOCK.md` §8, not measured here.
- **The sound column on the other suites** is the re-score of `eval/CERTAIN_CLOCK.md`, not a
  recording: programs without a kept vector-clock dump (most of P7 and P9, the PI programs outside
  its exits set) are covered by neither. Footnote (b) says so.
- **One node.** Every certain-policy verdict here is c74's schedule. rtraw's verdict is known to be
  node-dependent (X4: CLEAN on c58); the other 60 programs were not recorded under the certain
  clock on a second node. X1's recorded rows (c51, c78, …) agree in verdict with c74's recorded leg.
- **Cross-recording differences** are attributed to the schedule by §4's same-trace check on 9 of
  the programs involved; the larger ones (`uts-*-large`, `matrix-multiplication-racy-large`,
  `reduction-*-large`) were not re-recorded with the dump (trace volume), the attribution there is
  by the same mechanism, not shown on their own traces.
- **The dedup label flip** (§3) is explained by `aggregate._dedup_key`'s use of the current pc's
  space; not traced to the individual accesses (whether the pair touched shared memory in one run
  and global in the other, or only the orientation differs). It changes no verdict.
- **The committed tables' recorded columns** are the pre-T9 baseline rows; the paper's table needs
  the regeneration after X1's merge (§5).
- **Default tool path**: untouched (no collector or `sanalyzer` change); not re-diffed.

## 10. Files

- `eval/baselines/parallel.py`, `eval/baselines/run_cuvein.py` — the gate-policy note (§1).
- `eval/baselines/setup/p_final_certain.sh` — the sweep.
- `eval/baselines/final_certain.py` — `check` (step 2), `invariant` (step 3).
- `eval/baselines/setup/x2_same_trace.{py,sh}` — §4.
- `eval/baselines/make_tables.py` — section 3 of the summary (`sound_points_section`, `_verdict_view`).
- `eval/baselines/verdict_diff.py` — `--pset`, `--mode`, `--verdict-only`, `--collapse`.
- `eval/results/final-certain/`, `eval/results/final-certain-recorded/` — the rows (one shard CSV each).
- `eval/results/final-certain-invariant/` — `per_program.csv`, `added_pairs.csv`, `same_trace.json`.
- `eval/BASELINES.md`, `eval/BASELINES_SUMMARY.md` — regenerated with `--certain-results`.

## Appendix — per-program table (61 programs)

From `eval/results/final-certain-invariant/per_program.csv` (`final_certain.py invariant`). Race u SC pairs = the pc pairs reported as a Race or a Strong conflict; chain counters are the certain run's `hb_chain` summed over the program's kernels.

| program | label | Race alone rec / cert | R u L rec / cert | Race u SC pairs rec / cert | added (DR / SC) | added inst. unflagged | label flips | chain refused / edges (certain) |
|---|---|---|---|---|---|---|---|---|
| P4-1dconv-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 4,078,600 / 4,194,298 |
| P4-1dconv-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 4,078 / 4,090 |
| P4-1dconv-racy-large | RACE | RACE / RACE | RACE / RACE | 5 / 5 | 0 (0 / 0) | 0 | 0 | 4,080,193 / 4,190,202 |
| P4-1dconv-racy-small | RACE | RACE / RACE | RACE / RACE | 1 / 1 | 0 (0 / 0) | 0 | 0 | 4,075 / 4,086 |
| P4-graph-coloring-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 391,048 / 526,496 |
| P4-graph-coloring-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 10,683 / 20,899 |
| P4-graph-coloring-racy-large | RACE | RACE / RACE | RACE / RACE | 12 / 12 | 0 (0 / 0) | 0 | 0 | 487,445 / 675,680 |
| P4-graph-coloring-racy-small | RACE | RACE / RACE | RACE / RACE | 12 / 12 | 0 (0 / 0) | 0 | 0 | 13,300 / 20,269 |
| P4-graph-connectivity-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1,642,337 / 1,706,527 |
| P4-graph-connectivity-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1,591 / 3,068 |
| P4-graph-connectivity-racy-large | RACE | RACE / RACE | RACE / RACE | 8 / 8 | 0 (0 / 0) | 0 | 1 | 2,293,669 / 2,361,152 |
| P4-graph-connectivity-racy-small | RACE | RACE / RACE | RACE / RACE | 8 / 8 | 0 (0 / 0) | 0 | 1 | 1,697 / 3,422 |
| P4-matrix-multiplication-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 6 / 6 | 0 (0 / 0) | 0 | 0 | 160,180,912 / 169,399,376 |
| P4-matrix-multiplication-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 4 / 4 | 0 (0 / 0) | 0 | 0 | 4,759,232 / 4,890,464 |
| P4-matrix-multiplication-racy-large | RACE | RACE / RACE | RACE / RACE | 8 / 8 | 0 (0 / 0) | 0 | 0 | 159,420,496 / 168,476,896 |
| P4-matrix-multiplication-racy-small | RACE | RACE / RACE | RACE / RACE | 6 / 6 | 0 (0 / 0) | 0 | 0 | 4,779,680 / 4,900,384 |
| P4-reduction-norace-large | CLEAN | RACE / RACE | RACE / RACE | 15 / 19 | 4 (0 / 4) | 0 | 0 | 13,327 / 17,725 |
| P4-reduction-norace-small | CLEAN | RACE / RACE | RACE / RACE | 13 / 19 | 6 (0 / 6) | 1 | 0 | 2,146 / 3,267 |
| P4-reduction-racy-large | RACE | RACE / RACE | RACE / RACE | 17 / 19 | 2 (0 / 2) | 0 | 0 | 12,717 / 17,949 |
| P4-reduction-racy-small | RACE | RACE / RACE | RACE / RACE | 17 / 19 | 2 (0 / 2) | 0 | 0 | 1,986 / 3,011 |
| P4-rule-110-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 5 / 10 | 5 (0 / 5) | 0 | 0 | 17,190 / 1,968,266 |
| P4-rule-110-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 2 | 1 (0 / 1) | 0 | 0 | 225,905 / 491,656 |
| P4-rule-110-racy-large | RACE | RACE / RACE | RACE / RACE | 20 / 20 | 0 (0 / 0) | 0 | 0 | 17,176 / 1,966,299 |
| P4-rule-110-racy-small | RACE | RACE / RACE | RACE / RACE | 4 / 4 | 0 (0 / 0) | 0 | 0 | 225,836 / 491,133 |
| P4-uts-norace-large | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 54 / 54 | 0 (0 / 0) | 0 | 0 | 8,694,608 / 10,539,586 |
| P4-uts-norace-small | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 18 / 18 | 0 (0 / 0) | 0 | 0 | 340,365 / 383,764 |
| P4-uts-racy-large | RACE | RACE / RACE | RACE / RACE | 80 / 80 | 0 (0 / 0) | 0 | 3 | 9,326,082 / 11,089,714 |
| P4-uts-racy-small | RACE | RACE / RACE | RACE / RACE | 29 / 29 | 0 (0 / 0) | 0 | 0 | 338,451 / 379,098 |
| P5-canary | RACE | RACE / RACE | RACE / RACE | 1 / 1 | 0 (0 / 0) | 0 | 0 | 4 / 4 |
| P5-norace_interblock_atom | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1 / 1 |
| P5-norace_interblock_fence_raw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 2 |
| P5-norace_interblock_lock_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 1 | 1 (0 / 1) | 0 | 0 | 3 / 6 |
| P5-norace_interwarp-block_fence-atom_hrd-indirect | CLEAN | RACE / RACE | RACE / RACE | 3 / 3 | 0 (0 / 0) | 0 | 0 | 13 / 16 |
| P5-norace_interwarp-block_fence_hrf-indirect | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 10 / 10 | 0 (0 / 0) | 0 | 0 | 13 / 15 |
| P5-norace_interwarp_blkatom | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1 / 1 |
| P5-norace_interwarp_blkfence_raw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 3 |
| P5-norace_interwarp_blklock_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-norace_interwarp_dev-blkatom | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1 / 1 |
| P5-norace_interwarp_dev-blklock_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-norace_interwarp_fence_raw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 3 |
| P5-norace_intrawarp_none-blkatom | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 0 / 0 |
| P5-norace_intrawarp_none-blklock-no-tf_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 0 / 1 |
| P5-norace_intrawarp_none-blklock_waw | CLEAN | CLEAN / CLEAN | CLEAN / CLEAN | 0 / 0 | 0 (0 / 0) | 0 | 0 | 0 / 1 |
| P5-race_interblock_blkatom | RACE | RACE / RACE | RACE / RACE | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 0 |
| P5-race_interblock_blkfence_raw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 3 |
| P5-race_interblock_blklock_waw | RACE | RACE / RACE | RACE / RACE | 4 / 4 | 0 (0 / 0) | 0 | 0 | 2 / 2 |
| P5-race_interblock_fence_rtraw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 4 |
| P5-race_interblock_lock-blkfence_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 3 / 6 |
| P5-race_interblock_lock-no-stf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 3 / 6 |
| P5-race_interblock_lock-no-tf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 2 / 5 |
| P5-race_interblock_none-atom_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 0 |
| P5-race_interblock_none-lock_rtraw | RACE | CLEAN / RACE | CLEAN / RACE | 0 / 2 | 2 (1 / 1) | 0 | 0 | 3 / 7 |
| P5-race_interblock_none-lock_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 1 |
| P5-race_interwarp_blklock-no-stf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-race_interwarp_blklock-no-tf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-race_interwarp_dev-blklock-no-stf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-race_interwarp_dev-blklock-no-tf_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 1 / 4 |
| P5-race_interwarp_none-atom_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 0 |
| P5-race_interwarp_none-blkatom_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 0 |
| P5-race_interwarp_none-blklock_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 1 |
| P5-race_interwarp_none-lock_waw | RACE | CLEAN / CLEAN | CLEAN / CLEAN | 1 / 1 | 0 (0 / 0) | 0 | 0 | 0 / 1 |

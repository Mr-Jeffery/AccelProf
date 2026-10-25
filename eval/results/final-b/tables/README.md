# X1b's tables (`eval/results/final-b/tables/`)

Jeffery, 10-24: "Build the paper's tables from X1b's merged results into X1b's own directory, leaving
X1's tables untouched, and tell me what changes against X1's." X1's tables (`eval/BASELINES.md`,
`eval/BASELINES_SUMMARY.md`), X1's `eval/results/baselines-{disagreements,fp-causes}.csv` and X1's
revision pin (`eval/baselines/setup/cuvein_rev.status`) are unchanged.

## How they were made

`eval/baselines/setup/p_final_b_tables.sh` (job 320385, c22, 10-24 22:27–22:29) runs X1's table steps
of `p_final_post.sh` with unchanged code: `classify_endpoints.py --confirm`, `classify_fp_causes.py
--confirm --traces`, `cuvein_rev.sh`, `make_tables.py`.
- The three Python scripts find every input and output from their own file (HERE = their directory, APH =
  two levels up). Copies of them therefore run inside a sandbox, `~/x1b/tables_sandbox_b`. Its
  `eval/results` holds X1b's merged CSVs (`final-b/merged/baselines-cuvein.csv`,
  `final-b/merged/baselines-diagnose.csv`) and links to every other entry of the worktree's
  `eval/results` (the other tools' CSVs, read only). The four cuVein-derived files are written there and
  copied here.
- Confirmation details: `~/x1b/confirm_final-b-merged` (the post job's view of the merged rows).
- Trace view for `classify_fp_causes.py`: `/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-view`, built
  with X1's code: 4,725 ids; from the 5,400 s stores vector-clock 9, scalar-clock 2; from the 84,600 s
  stores vector-clock 10, scalar-clock 8.
- Revision pin (`cuvein_rev.status`, label final-2026-11): runtime checkout at f551ca0 (cuVein), 0-line
  working-tree diff, libsanalyzer `5a20fd14ab6c6806`, collector `b746b4dd23e90f46`.

| file | what |
|---|---|
| `BASELINES.md`, `BASELINES_SUMMARY.md` | X1b's versions of `eval/BASELINES.md` and `eval/BASELINES_SUMMARY.md` |
| `baselines-disagreements.csv`, `baselines-fp-causes.csv` | X1b's versions of X1's `eval/results/` files |
| `cuvein_rev.status`, `cuvein_rev/final-2026-11.diff` | the revision pin |
| `x1_vs_x1b.md` | every changed table cell against X1's files (`final_b_compare_tables.py`) |
| `overhead_shared_vs_own.md`, `overhead_by_cpu.md` | the two overhead checks below |
| `job-320385.txt` | the job's log, with the method check and the X1-untouched checks |

**X1's files untouched** (job log): 0 tracked changes under `eval/results`, `eval/BASELINES*.md` and
`eval/baselines/setup`; the other tools' 209 CSVs equal `final-b/merged/other_tools.sha256.after`.

**Method check.** The same steps on X1's own inputs (`~/x1b/tables_sandbox_x1`, X1's confirm dir and
trace view) reproduce:
- X1's `BASELINES_SUMMARY.md` and `baselines-fp-causes.csv`, byte for byte.
- X1's `baselines-disagreements.csv` as the same 47,152 lines in a different order. The rows follow
  the directory order in which `glob` returns `eval/results/baselines-*.csv`.
- X1's `BASELINES.md`, except §3's "First 2000 of 47151 disagreement rows" listing (lines 5671–7670),
  which shows the first 2,000 rows in that order. So `x1_vs_x1b.md` skips that listing and compares
  the two CSVs as multisets of rows.

## What changed against X1's tables

Verdict-based cells change only through the 5 changed (id, mode) verdicts of FINAL_SWEEP_B.md §9:
- P5-race_interblock_none-lock_rtraw, CLEAN → RACE in both modes;
- P7-haversine vector-clock, CLEAN → TIMEOUT;
- P7-particlefilter vector-clock, RACE → TIMEOUT;
- P9-expdist scalar-clock, TIMEOUT → RACE.

**`BASELINES_SUMMARY.md` table 1** (and BASELINES.md §2c), cuVein columns only:

| row | mode | X1 | X1b |
|---|---|---|---|
| ScoR micro-benchmarks + canary | vector-clock | 3/19, 1/14, 0, 0 | 4/19, 1/14, 0, 0 |
| ScoR micro-benchmarks + canary | scalar-clock | 2/19, 0/14, 0, 0 | 3/19, 0/14, 0, 0 |
| HeCBench overhead set | vector-clock | -, -, 1, 0 | -, -, 3, 0 |
| HeCBench SuperCollider 10-app subset | scalar-clock | 2/3, 0/5, 2, 0 | 3/4, 0/5, 1, 0 |
| All pre-registered labelled suites | vector-clock | 1938/2108, 20/1569, 0, 16 | 1939/2108, 20/1569, 0, 16 |
| All pre-registered labelled suites | scalar-clock | 1937/2108, 19/1569, 0, 16 | 1938/2108, 19/1569, 0, 16 |
| SuperCollider-matched suites | scalar-clock | 52/61, 1/70, 2, 16 | 53/62, 1/70, 1, 16 |

The other tools' cells and every FP cell are unchanged. The notes column follows:
- rtraw leaves both FN lists;
- the P7 vector-clock failures become "hb-state-memory (2); hb-clock-hang (1)";
- P9 scalar-clock "time-cap (1)".

**Overhead** (`BASELINES_SUMMARY.md` table 2, BASELINES.md §2a geomean×, §2b, §4, §4a): every cell
changes. Two separate effects:
1. **The shared native.** `make_tables.py` divides every runner's wall by the id's minimum native wall
   over all runners that timed our build (cuVein, iGUARD, the sanitizer runners). X1b's cuVein native
   walls enter that minimum.
   - So the other tools' slowdowns move although their CSVs did not change: for example, racecheck on
     Indigo3 goes from geomean 3.7× to 3.3×, and iGUARD on all suites from 2.3× to 2.2×.
   - The minimum is another runner's native in 4,167 of 4,868 ids (X1: 4,004).
   - §2b also normalises the superseded revisions by the current run's native, so their geomean× change too.
2. **cuVein is slower on the short-program suites, and not because of the host mix.**
   - Against cuVein's own same-node native (`overhead_shared_vs_own.md`), the geomeans rise almost as
     much as in the tables: PI vector-clock 4.5× → 6.0× (tables: 5.1× → 6.9×), and all suites
     vector-clock 4.9× → 6.5× (tables: 5.5× → 7.5×).
   - cuVein's own native walls did not move: X1b/X1 median 1.00 (p10 0.81, p90 1.24) over 9,418 (id, mode).
   - Paired over the (id, mode) keys whose rows ran on the same CPU type in both recordings
     (`overhead_by_cpu.md`), the median X1b/X1 slowdown is:

     | suite | vector-clock | scalar-clock | keys (vc / sc) |
     |---|---|---|---|
     | PI | 1.27 | 1.29 | 2,906 |
     | P1 | 1.32 | 1.33 | 125 |
     | P3 | 1.43 | 1.37 | 18 |
     | P5 | 1.70 | 1.26 | 10 |
     | P4 | 1.23 | 1.11 | 10 |
     | P6 | 1.08 | 1.08 | 13 / 11 |

   - Whether the runtime (f551ca0 against 4094187) or the environment (BeeGFS load, for example)
     causes the rise is not separated.
   - The long HeCBench programs got faster in scalar-clock (N = 16): HeCBench overhead set 1152.2× →
     230.0×, and the SuperCollider 10-app subset 1052.5× → 512.6× (paired: P7 0.10 over 4 keys, P9 0.39
     over 2).

**Other sections of BASELINES.md** (all in `x1_vs_x1b.md`):
- **§1b, residual classes:**
  - vector-clock hb-state-memory 2 → 3;
  - the vector-clock no-kernel-in-cap row (X1's expdist) gives way to hb-clock-hang;
  - scalar-clock time-cap 2 → 1;
  - "cuVein-attributable" rows 0 of 38 → 2 of 42: haversine and expdist vector-clock, both
    `hb-clock-hang`.
  - `hb-clock-hang` is `classify_residuals.py`'s name for a vector-clock TIMEOUT below 32 GB whose
    scalar-clock row resolved. haversine wrote 59–61 of 100 kernels (FINAL_SWEEP_B.md §3), so it is
    not a stall.
- **§2a:**
  - TP +1 and FN −1 in each mode (pre-registered sets).
  - Matched sets, scalar-clock: TP 52 → 53, err/TO 2 → 1.
  - cuVein vs SuperCollider, P9 scalar-clock: both RACE 2 → 3.
- **§2b, verdict transitions against the superseded revisions:**
  - CLEAN → RACE +1 per mode (rtraw);
  - TIMEOUT → CLEAN vector-clock −1 (haversine);
  - TIMEOUT → RACE scalar-clock +1 (expdist);
  - a new RACE → TIMEOUT row (particlefilter vector-clock).
- **§2c, accuracy and D2:**
  - P5 TP 3/19 → 4/19 (vector-clock) and 2/19 → 3/19 (scalar-clock).
  - P9 scalar-clock 2/3 (2 err) → 3/4 (1 err).
  - The vector-clock rtraw detection counts in D2's a2 (uncertain) tier: a2 (R) TP 0 → 1.
- **Per-program tables:**
  - The verdict changes are the 5 above.
  - Report counts change in P1 (3 rows), PI (110 rows, 146 cells) and P4 graph-coloring racy small
    (RACE(13) → RACE(12) in both modes). This is the "same verdict, different report set" of
    FINAL_SWEEP_B.md §9.
- **§3 disagreements:**
  - 47,151 → 47,128 rows. 1,437 are only in X1's CSV and 1,414 only in X1b's, over 240 programs; many
    are a RAW ↔ WAR flip of the same pair.
  - Per (tool_a, tool_b, category, mechanism): cuVein-SC vs iGUARD 752 → 775, cuVein-SC vs racecheck
    17,555 → 17,533, cuVein-VC vs iGUARD 752 → 753, cuVein-VC vs racecheck 17,591 → 17,566 (all
    weak-vs-weak / none). The other groups are unchanged.
- **FP causes:** `baselines-fp-causes.csv` is unchanged (127 rows, the same multiset).
- **§4b, memory:** scalar-clock peaks are higher at N = 16 (FINAL_SWEEP_B.md §4). For example:
  - P1 scalar-clock max 985 → 1,613 MB;
  - P6 scalar-clock max 65.9 → 93.0 GB;
  - P7 scalar-clock median 6.2 → 14.0 GB (× floor 7.28 → 16.43);
  - P9 scalar-clock median 1.9 → 3.7 GB.

  Vector-clock peaks barely move, except in P7, where the set of finished programs changed.

**The +1 P5 detection** is lock_rtraw, whose one report is the `dummy` WAW pair inside the critical
sections. The coordinator's triage (`../triage_rtraw.md`, FINAL_SWEEP_B.md §9) finds it a false report from
A2-inverted recordings; how to count it is Jeffery's call.

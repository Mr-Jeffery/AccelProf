#!/usr/bin/env python3
"""Assemble eval/COLLECTOR_ONLY_TABLES.md from the generated per-item markdown files (run from the worktree root)."""
D = "eval/results/collector-only-tables"
def rd(n): return open(f"{D}/{n}").read().rstrip() + "\n"
H = """# Collector-only tables (C3)

Branch `eval/collector-only-tables`, cut from `origin/eval/final-tables` (d484e42). Nothing recorded, no GPU, no detector or rule change, cuRacePaper not edited, C1/C2 branches read only (not merged). Every number below is computed from kernel JSONs (item 9, 10) or results CSVs (all other items) by the scripts in `eval/baselines/setup/co_tables/`; the CSVs are in `eval/results/collector-only-tables/`.

Third mode = collector-only (CO): no HbClock, verdicts from the static certificates alone; a conflicting reuse pair no certificate orders is Race or Strong-conflict, never Latent. Sources: X1b (`final-2026-11`, vector-clock and scalar-clock), C1 (`eval/collector-only` 0c28634, `final-2026-11-co`), C2 (`eval/collector-only-realworld` 016d93f, real-world recall and candidates). `make_tables.py` gained only the third mode (`--collector-only`); with the flag off its output equals X1b's, and with it on, the vector-clock/scalar-clock columns are unchanged (`co_strip_compare.py`; the 13 remaining diff hunks are single-column separator artifacts of the comparison).

## Which paper cell each table fills

| paper cell | table below |
|---|---|
| Table 6.1 (tab:eval-accuracy) and the aggregate row | Table 6.1 section |
| tab:eval-accuracy-union, tab:eval-countings | union/countings section |
| tab:eval-litmus | litmus section |
| tab:eval-recall, candidate counts | Item 4 |
| fig_slowdown (fig:eval-slowdown) | fig_slowdown section |
| tab:eval-memory | memory section |
| cost table (FINAL_TABLES.md section (a)) | Item 6 |
| app:eval-noverdict | no-verdict section |
| program-level comparison (not in the paper) | Item 8 |
| tab:eval-shapes (X5's 1,021 pairs) | Item 9 |
| sec:onerun "Is one run enough?" | Item 10 |

## Findings

1. Every vector-clock and scalar-clock cell of Table 6.1, the union table, the countings table and the litmus table recomputes to the paper's value (check section after the tables).
2. Mismatches with the paper (reported, not edited): the slowdown figure's HeCBench "other 14" and "All" cells (paper 1349.0/249.7 and 7.5/7.1; recomputed values are in the fig_slowdown table); the memory table's HeCBench scalar-clock median (paper 14.0 GB, recomputed 5.39); the real-world fixed-build clean count (paper 21, 20 recomputed from T21b's `main` flavor); candidate count 16 against the paper's 18.
3. Collector-only on race-free programs: 224 false reports in Indigo 1.3 (paper-style FP 224/1,260), against 0 for vector- and scalar-clock; 229 race-free programs are Race in CO and Clean in SC (listed in `item8_race_free_co_race_sc_clean.csv`). Pair-level cause (Item 9): 1,016 of the 1,138 CO-only pairs are the barrier-ordered pairs of X5's shapes table (S1, a subset of X5's 1,021), 96 have no edge in the scalar-clock recording (schedule-dependent edge) and 26 are ordered in SC by an R3 certificate chain that CO lacks. Pairs fitting none of the reasons: 0.
4. CO is Clean where SC is Race for 28 programs (appendix list in Item 8), 26 of them in PI, all unlabelled or racy-labelled; no race-free program is Clean-in-CO-only.
5. Real-world recall: CO detects 21 of 25 scored data-race components (SC/VC 25 of 26), 5 of 5 strong-conflict components as in the paper.
6. Footnotes: amrex-1 (buggy and fixed) is pending (CO re-analysis running) and is left out of every CO count. C2's aggregate `COLLECTOR_ONLY_REALWORLD.md/.csv` still shows hecbench-hungarian-1, raft-1 and colmap-new-1 as NOT-SCORED/ERROR while its per-set recall.csv files hold the re-analysis rows; Item 4 uses the per-set files. lock_rtraw is counted as recorded (Race, a false report) in X1b [^rtraw]. lightgbm-new-1/2 are unscored. 18 programs have no scalar-clock recording and 3 analyses hit their time cap in Item 9; 17 CO ERROR rows are in C1's report (sm_90 programs and `P9-atomicCAS-cuda`).

[^rtraw]: `race_interblock_none-lock_rtraw` is a race-free-labelled false report in X1b; counted as recorded.

"""
parts = [H, rd("co_tables1.md"), "\n", rd("item4.md"), "\n", rd("cost_co.md"), "\n", rd("item9.md"), "\n", rd("item10.md")]
open("eval/COLLECTOR_ONLY_TABLES.md", "w").write("\n".join(parts))
print(sum(len(p) for p in parts))


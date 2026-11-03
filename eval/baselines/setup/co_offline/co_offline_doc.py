#!/usr/bin/env python3
"""Assembles eval/CO_OFFLINE.md from the generated files in eval/results/co-offline/ (tables/, parity_shards.md, merged_report.md) and the
narrative below.  The narrative's numbers are copied from those files (the section each comes from is named next to it)."""
import csv

R = "/home/fzheng4/wt-c4/eval/results/co-offline"
T = f"{R}/tables"
rd = lambda p: open(p, encoding="utf-8").read().rstrip("\n")
out = []
A = out.append
A("""# CO-R: collector-only, re-scored (C4)

Branch `eval/co-offline`, cut from cuVein f551ca0 (`eval/collector-only-tables` 1c97571 fast-forwarded in, c45e1b3 cherry-picked for `test_collector_only.py`). Not merged. No GPU, no recording: X1b's scalar-clock kernel JSONs (`final-2026-11`, `-long`, `-long-sc`, `-24h-sc`) and the real-world scalar-clock recordings of T21b / T21c re-analysed on `normal` nodes.

**CO-R** = the verdict layer run on the scalar-clock kernel JSONs with the barrier-ordered rule off (`CUVEIN_BARRIER_ORDER=0`, `sync_dominance.analyze(barrier_order=False)`). Everything else is as in scalar-clock mode: the candidates (cuVein's edges plus the event-stream candidates from hb_sync_pass), the edge rescue (observed distances from hb_sync_pass), the RMW points (hb_rmw_points) and all three certificates. A conflicting pair no certificate orders is Race or Strong conflict; there is no Latent. "cuVein edges only" = C1's collector-only run (separate recordings, no sync pass).

Numbers in this file come from kernel JSONs through the CSVs / jsonl in `eval/results/co-offline/` (named per section); a number that could not be obtained is stated as missing.

## Findings

1. **Parity (rule on):** 0 differences between the re-analysis with the rule on and X1b's own CSVs, on verdict, reports_dedup, report_ids, report_lines and the classes note: 14,157 (id, mode, rep) rows in 122 shard files (112 main + PI, 2 long-sc, 8 24h-sc), 0 shard files missing; merged with X1b's rule, 14,111 scalar-clock rows against 14,111, 0 differences (`parity_shards.md`, `merged_report.md`).
2. **Table 6.1 aggregate row, CO-R:** 1,958/2,082 recall, 246/1,548 false-positive rate, 16 ERR; scalar-clock 1,934/2,082 and 18/1,548; cuVein edges only 1,956/2,082 and 246/1,548.
3. **Program level, CO-R against scalar-clock (same recordings):** 254 programs go Clean to Race (Indigo 1.3 248: 24 racy-labelled, 224 race-free; ScoR applications 4 race-free; HeCBench other 1 unlabelled; HeCBench SC's 10 1 race-free); 0 programs go Race to Clean; 0 other differences. 229 race-free-labelled programs are Race in CO-R and Clean in scalar-clock.
4. **Pair level:** CO-R reports 1,016 pairs in 893 programs that scalar-clock orders; scalar-clock ordered every one by the barrier clock in every launch. All 1,016 have a cuVein edge (a); 0 are extended or rescued edges (b). They are the same 1,016 pairs as C3's S1: no pair in one set and not the other. The shape counts equal X5's.
5. **Real-world:** CO-R detects the four data-race components that the edges-only run missed (CCCL top-k, Ginkgo range-minimum, Kokkos rw_sum, RAFT select_k), and PCL's data-race half. Details, and the llama.cpp-open-2 difference, in section 2.
6. **CO-R against C1:** 4,679 of 4,709 programs have the same verdict; 28 are Clean in C1 and Race in CO-R, 0 the other way, 2 other differences. 551 pairs fall in "other" (455 CO-R only, 96 C1 only): these are findings, listed in section 5.

## Run state

- Re-analysis job 323878 (c76, 5:32:03, COMPLETED): X1b's shard counts (48 main, 64 PI, 2 long-sc, 4+2+2 for 24h-sc), each program analysed serially with the rule on and off, both analysis times recorded (`final-b*/analysis-time-*.csv`). All 122 shards wrote the on CSV, the off CSV (`baselines-cuvein-bo0-*`) and the timing CSV.
- Pair-level pass: 28 shards over the 4,725 programs; 4,707 recordings analysed (18 have no scalar-clock recording). Three recordings hit the 3,600 s cap in the first pass (P7-srad-cuda, P9-tridiagonal-cuda, P9-mr-cuda) and were re-run with a 16,200 s cap (job 324010, 4:54:28): all three finished, both halves.
- Real-world heavy ids (hecbench-hungarian-1 buggy and fixed, colmap-new-1, raft-1 buggy and fixed): job 323983 (c26, 7:47:57). Analysis walls 20,982 s and 23,749 s (hungarian buggy, fixed), 23,392 s (colmap-new-1), 4,694 s and 4,669 s (raft-1 buggy, fixed); all rc=0.
- Analysis cap 84,600 s. Merge rule: X1b's (FINAL_SWEEP_B.md section 1 (i)): the first pass, overridden per (id, mode) by the 5,400 s pass and by the 84,600 s pass for the keys X1b kept (8 keys; an ERROR leaves the earlier rows). Partial-row rule (a run a cap stopped keeps the reports it wrote, Race if it holds one, else unfinished): P7-particlefilter-cuda (3 reps) is `partial(rc=1)` with 31 race reports in both halves, so Race in both.

### Rows that stay TIMEOUT / ERROR

- `P7-stencil1d-cuda` rep 1 and `P9-atomicCAS-cuda` rep 1: scalar-clock TIMEOUT (cap=84600) in X1b; TIMEOUT in both halves here.
- 16 runner-level rows with no recording (`missing-exe`, ERROR): `P6-bulkcpy-*` (12) and `P6-dsmem-*` (4); they are the ERR count of the cuHadron row.
- Real-world: `amrex-1` buggy and fixed (scalar-clock analysis ERROR at 82,800 s in T21b; buggy ERROR, fixed has no row) not re-run; `lightgbm-new-1` and `lightgbm-new-2` unscored.

## Parity report (rule on, against X1b)

""")
A(rd(f"{R}/parity_shards.md"))
A("\n## Merge report\n")
A(rd(f"{R}/merged_report.md"))
A("""

## 1. Tables: Table 6.1, union, three countings, litmus (CO-R next to vector-clock, scalar-clock and "cuVein edges only")

`make_tables.py --co-offline` (with `--collector-only`) adds a fourth cuVein column "collector-only, re-scored" (CO-R) from `merged/baselines-cuvein-cor.csv`. It is run in two sandbox trees (C3's method, `p_co_offline_tables.sh`): A = `--collector-only`, B = `--collector-only --co-offline`; `co_offline_strip_compare.py` removes every CO-R column, row, note segment and sentence clause from B and compares it with A: **0 diff lines** (the other columns are byte-identical). The outputs are `mt/BASELINES_A.md` and `mt/BASELINES_B.md` (and the summaries). A leak was found and fixed in `make_tables.py` on the way: CO-R rows would have fed the native-wall denominator of the revision-delta section; they are now excluded there and in `_ratios`. The overhead and memory sections leave the column out.

""")
A(rd(f"{T}/co_offline_tables.md"))
A("""

### Race-free-labelled programs that are Race in CO-R (with their pairs)

All 248 race-free-labelled programs that are Race in CO-R; `scalar-clock` shows which of them scalar-clock calls Clean (the 229 programs this change creates) and which are Race in scalar-clock too (19). Pairs = space:lo-hi:type. Source: `tables/race_free_cor_race_all.csv`.

<details><summary>248 programs</summary>

| suite | program | scalar-clock | CO-R reports | pairs |
|---|---|---|---|---|""")
for r in csv.DictReader(open(f"{T}/race_free_cor_race_all.csv", encoding="utf-8")):
    A(f"| {r['suite']} | `{r['id']}` | {r['sc_verdict']} | {r['cor_reports']} | {r['cor_report_ids'].replace('|', '/')} |")
A("\n</details>\n")
A("""
## 2. Real-world recall (T21b) and candidates (T21c)

CO-R = the real-world scalar-clock recordings re-analysed with the rule off, attributed by `rw_attribute.py` and scored by `rw_score.py`, the scripts that produced `eval/results/realworld/recall.csv` and `realworld_t21c` (run from copies of their branches under `~/c4rw`; the only edit is `RW_MODES`). Results: `realworld/recall.csv`, `realworld_t21c/recall.csv`. T21c is scored with `--exclude lightgbm-new-1,lightgbm-new-2`, as T21c did.

**Confirmed (CO-R DETECTED):** CCCL top-k (cccl-3 DR), Ginkgo range-minimum (ginkgo-5 DR), Kokkos rw_sum (kokkos-5 DR), RAFT select_k (raft-1 DR), and PCL's data-race half (pcl-new-1 DR). Refuted: none.

""")
A(rd(f"{T}/co_offline_recall.md"))
A("""

Other differences from scalar-clock: the fixed builds `kokkos-5` (CLEAN to RESIDUAL), `llamacpp-2` and `pytorch-1` (CLEAN to STILL-REPORTED) change as in the edges-only run; in the candidate set `llamacpp-open-2` buggy is MISSED in scalar-clock and DETECTED in CO-R, and its fixed build is CLEAN in scalar-clock and STILL-REPORTED in CO-R (n_race 16 in both builds), so that detection does not separate the buggy build from the fixed one.

## 3. Program level, CO-R against scalar-clock

The program-level table, the by-label table, the race-free list and the "other differences" lines are in section 1 (block "Program level"). Files: `tables/program_level_summary.csv`, `tables/program_level_diffs.csv`.

""")
pairs = rd(f"{T}/co_offline_pairs.md")
head, tail = pairs.split("## CO-R against the collector-only run of C1")
A(head.replace("## Pair level", "## 4. Pair level", 1))
A("""
## 5. CO-R against C1 (cuVein edges only), per suite

Pairs: reported pairs of CO-R (scalar-clock recording, rule off) against reported pairs of C1 (separate recording). A CO-R-only pair is classed by its tags in CO-R: `e` = event-stream candidate with no edge (extended edge), `r` = edge rescued by the sync pass, neither = other. A C1-only pair is classed RMW points when CO-R orders it by an R3 chain (the `c` flag, from hb_rmw_points), otherwise other.
""")
A(tail)
A("""

### Anything in "other" is a finding

- **CO-R only, C1 has no record of the pair (435 pairs: Indigo 1.3 431, Indigo3 1, ScoR applications 2, cuHadron 1):** the pair has a cuVein edge in X1b's recording (it is not an extended or rescued edge) and no edge in C1's separate recording, so C1 never judged it. Cause not established beyond the two recordings differing.
- **CO-R only, C1 orders the pair (20 pairs: P4 `uts-*` 19, P5 `race_interblock_none-lock_rtraw` 1; C1 tag `ORDERED:None`):** C1 orders the pair by a certificate, CO-R does not. `race_interblock_none-lock_rtraw` is the program C1 misses and scalar-clock reports (litmus table). The mechanism is not established in this run.
- **C1 only, CO-R has no record of the pair (96 pairs: Indigo 1.3 87, Indigo3 7, ScoR applications 1, cuHadron 1):** the converse; no edge in X1b's recording.
- The pair sets are per recording; C1 and X1b are different runs of the same programs, so the pair set differs with the schedule.

""")
A(rd(f"{T}/co_offline_extra.md"))
A("""

## 6. What this cannot see

CO-R re-scores recordings that were taken with the barrier clock on. Extended edges and rescues that the barrier clock ordered were dropped at run time, so they are not in the kernel JSONs and CO-R cannot report them: CO-R's false positives are a lower bound of what a collector-only run reports (the (b) class above is 0 for this reason, not because such pairs do not exist). It measures no run time and no memory (the recordings are the scalar-clock ones), so Figure 6 and the memory table keep C1's numbers, labelled "cuVein edges only". The pair-level analysis times are not overhead figures.

## Pool-safety

The env toggle behind `parallel.py analyze --both-barrier-orders` (`CUVEIN_BARRIER_ORDER`, set around `analyze_one` in `cmd_analyze`) is not pool-safe and must move into `_analyze_reports` when this branch is rebased onto X7 Part A.

## Files

`eval/results/co-offline/`: `final-b*/` (shard CSVs, both halves, timing), `merged/` (merged on / off / `baselines-cuvein-cor.csv`), `parity_shards.md`, `merged_report.md`, `pairs/` (per-program pair records, on and off), `realworld/`, `realworld_t21c/` (CSVs, attribution, `recall.csv`), `mt/` (sandbox BASELINES A and B), `tables/`. Scripts in `eval/baselines/setup/co_offline/` and `p_co_*.sh`.
""")
open("/home/fzheng4/wt-c4/eval/CO_OFFLINE.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(len("\n".join(out)))

# M4 — trace-validity (TV) counts over the X1b stores

Branch `eval/tv-counts` from `origin/eval/final-tables` (d484e42), worktree `/home/fzheng4/wt-tv`, unmerged for
Jeffery. Written 2026-10-26. **No recording, no GPU.** One CPU job on partition `normal` (321683, 24 array
tasks, c0/c1/c23/c46 excluded, all COMPLETED; log `eval/x_logs/tv-scan-321683.log`) read the kernel JSONs of the
X1b stores. Runtime: `cuVein` f551ca0 (`FINAL_SWEEP_B.md` §0). Script `eval/baselines/setup/tv_scan.py`
(`p_tv_scan.sh` is the job script). Every number below is in a CSV in `eval/results/tv-counts/` (§6).

**Result: 0 kernels of 73,135 have a non-empty `tv_violation`. No check fired in any suite or mode. 0 kernels
had a syncwarp instance that never completed. There is no firing to classify.**

## 1. What the field can and cannot say

Read from `sanalyzer/src/tools/pc_dependency_analysis.cpp` at f551ca0:

- `tv_fail()` keeps **only the first** violation of a kernel (`if (tv_violation.empty()) tv_violation = msg`;
  line 1446). The JSON field is one string per kernel, written only when non-empty (line 2466). So "firings
  per check" below means kernels whose *first* violation is that check. A later firing in the same kernel is
  not visible. Because the total is 0, nothing is masked here.
- The checks the runtime emits: `TV-record-after-exit`, `TV-barrier-completion-order`,
  `TV-barrier-overfill`, `TV-expected-nonzero-multiwarp`, `TV-barrier-pending-at-end`, and (T24)
  `TV-syncwarp-completion-order`, `TV-syncwarp-pending-at-end`. **`TV-seq-monotonic` is not emitted by the
  runtime**: its comment (line 2083) says the event sequence is monotonic by construction, and only the offline
  oracle checks it. Its column in the CSV is therefore 0 by construction, not by observation.
- All checks except the two `*-pending-at-end` ones run only when `strict` is on. `strict` is on unless
  `YOSEMITE_HB_STRICT=0` (line 3317). `p_final.sh` unsets every inherited `YOSEMITE_*` variable (line 53), so
  X1b ran strict. I did not read a `meta.json` or log to confirm the variable was absent in every job.
  The two `*-pending-at-end` checks run whatever the setting.

## 2. Syncwarp instance that never completes (Section 8.2)

I did not find "Section 8.2" in `cuRacePaper/*.tex` (`grep` for `8.2` finds nothing about it), so I took the
case from the detector: T24's `eval/SYNCWARP_INSTANCE.md` (the "A3 analogue at runtime") and the code. An
instance is the open `pending_syncwarps` entry for (block, warp, pc). It completes when the lanes that arrived
cover `sync_mask` minus the exited lanes and minus the lanes absent from the block (`sw_complete`,
`sw_expected`). **An instance that is still open at the end of the kernel is reported as
`TV-syncwarp-pending-at-end`** (`check_pending_at_end`, line 1055), whatever the strict setting.

That check name is the detector's own counter for the case. It is computable from the JSONs.

**Kernels with `TV-syncwarp-pending-at-end`: 0 of 73,135 (0 of 51,499 vector-clock, 0 of 21,636
scalar-clock).** The same check can be masked by an earlier first violation in the same kernel; there is none.
Not computed: how many of these kernels contain a syncwarp record at all (the field does not say). For scale,
`WARPSYNC_JOIN_GAP.md` counts 8,720 of 497,823 kernel JSONs (all kept stores, not only X1b) with
diverged-warp syncwarp records.

## 3. Stores read

Store root `/mnt/beegfs/fzheng4/cuvein_traces/`. Layout `<store>/<id>/<mode>/kernel_*.json`. The first pass and
the PI pass share one store (`FINAL_SWEEP_B.md` §1, store row). Kernel JSONs per store are in
`tv_store_counts.csv`; ids with a kernel directory per store are from `tv_by_store_id_mode.csv`.

| store | pass | mode | ids with kernel JSONs | kernel JSONs |
|---|---|---|--:|--:|
| `final-2026-11` | first pass + PI pass | vector-clock | 4,690 | 12,097 |
| `final-2026-11` | first pass + PI pass | scalar-clock | 4,699 | 18,455 |
| `final-2026-11-long` | 5,400 s | vector-clock | 7 | 7,632 |
| `final-2026-11-long-sc` | 5,400 s | scalar-clock | 2 | 1,326 |
| `final-2026-11-24h-vc` | 84,600 s | vector-clock | 9 | 31,771 |
| `final-2026-11-24h-sc` | 84,600 s | scalar-clock | 6 | 1,855 |
| **total** | | vector-clock / scalar-clock | | **51,500 / 21,636** |

- `final-2026-11-dryrun` (2 ids, 4 kernel JSONs per mode) is excluded from every count (the dry run, not part
  of the final recording). Its 8 kernel JSONs have no violation either (`tv_by_store_id_mode.csv`).
- `final-2026-11-view` is a view over the stores, not a store; not read.
- All kernel JSONs are complete files (end with `}`): `incomplete_files` is 0 in every row.
- 4,757 (store, id) directories with a `meta.json` were enumerated and sharded, 4,754 without the dry run.

**De-duplication.** A kernel is (id, mode, kernel file name). When one appears in two stores, one copy is
counted, taken from the later pass by this preference: 84,600 s, then 5,400 s, then the first pass (the
merge rule of `FINAL_SWEEP_B.md` §1 (i): a long pass replaces its (id, mode)). Result: **1** kernel file is
present in two stores (vector-clock); the two copies agree (both empty; `DEDUP_DIFFER` = 0 in
`tv_store_counts.csv`). The raw 51,500 vector-clock kernel JSONs become **51,499** unique kernels; scalar-clock
21,636 has no duplicate. (`FINAL_TABLES.md` (c) says 21,636 and 51,500, the raw counts; they agree with this
scan's raw counts.) A kernel recorded in a long pass but with a different file name from the first pass would
count twice; I did not check that no id appears in both a first-pass and a long-pass store with different
kernel sets. `tv_by_store_id_mode.csv` has the per-(store, id, mode) counts for that check.

## 4. Counts per suite and mode

Suite = the id's prefix (`P1` ... `P9`, `PI`). Columns: kernels recorded, kernels with an empty
`tv_violation`, kernels with a non-empty one, then the firings per check. All check columns are 0
(`tv_counts_by_suite_mode.csv`).

| suite | mode | kernels recorded | empty `tv_violation` | non-empty |
|---|---|--:|--:|--:|
| P1 | vector-clock | 5,052 | 5,052 | 0 |
| P1 | scalar-clock | 5,049 | 5,049 | 0 |
| P3 | vector-clock | 727 | 727 | 0 |
| P3 | scalar-clock | 727 | 727 | 0 |
| P4 | vector-clock | 336 | 336 | 0 |
| P4 | scalar-clock | 333 | 333 | 0 |
| P5 | vector-clock | 33 | 33 | 0 |
| P5 | scalar-clock | 33 | 33 | 0 |
| P6 | vector-clock | 38 | 38 | 0 |
| P6 | scalar-clock | 38 | 38 | 0 |
| P7 | vector-clock | 7,790 | 7,790 | 0 |
| P7 | scalar-clock | 7,893 | 7,893 | 0 |
| P9 | vector-clock | 33,393 | 33,393 | 0 |
| P9 | scalar-clock | 3,433 | 3,433 | 0 |
| PI | vector-clock | 4,130 | 4,130 | 0 |
| PI | scalar-clock | 4,130 | 4,130 | 0 |
| **all** | vector-clock | **51,499** | **51,499** | **0** |
| **all** | scalar-clock | **21,636** | **21,636** | **0** |

Firings per check, every suite and both modes: `TV-seq-monotonic` 0 (not emitted, §1),
`TV-barrier-overfill` 0, `TV-barrier-completion-order` 0, `TV-expected-nonzero-multiwarp` 0,
`TV-record-after-exit` 0, `TV-barrier-pending-at-end` 0, `TV-syncwarp-completion-order` 0,
`TV-syncwarp-pending-at-end` 0, any other string 0.

This agrees with `FINAL_SWEEP_B.md` §6 (c) ("`tv_violation`: none") and its `final_sanity.py` check. This scan
is an independent read (byte search of every kernel JSON, not `json.load`), and adds the per-check table.

## 5. Firings and their classification

None. The list is empty (`tv_firings.csv` has a header only), so no firing needed a program, kernel or a
known-case/new classification.

Known cases, for the record, and why they do not appear:

- **ECL-GC exit-mask case.** CLAUDE.md (T11 lead) and `SIDECAR_STRENGTH.md` §9 describe it: on the
  re-recorded ECL-GC, 28 lanes of block 0 warp 3 exit, then the remaining 4 execute `__syncwarp()` with the
  full mask; the old `TV-record-after-exit` read the syncwarp's named mask and fired. T24 changed W3 to read
  `active_mask` for a syncwarp record (`SYNCWARP_INSTANCE.md`, "W3 ... decision"): a lane named in the mask
  may have exited, and the join excludes it. So under f551ca0 this pattern is not a violation. I took the
  ECL-GC kernels to be the `P4-graph-coloring-*` ids (name match, not checked against the source): 141
  scalar-clock and 144 vector-clock kernel JSONs in the first-pass store, all empty.
- **crs-cuda** (`TV-barrier-completion-order` on 46 of 50 kept kernels before T3b, CLAUDE.md) is fixed by T3b; the
  P9 crs-cuda kernels in X1b are empty.

I did not run a positive control on a real old firing (the old kernel JSONs are multi-GB dumps and the job
was cancelled). The scanner was checked on a synthetic kernel JSON with a `TV-syncwarp-pending-at-end`
string containing escaped quotes (detected, name parsed) and on one without the field (empty).

## 6. Files

`eval/results/tv-counts/`:
- `tv_counts_by_suite_mode.csv`: per suite and mode, kernels, empty, non-empty, one column per check
  (`TV-seq-monotonic` ... `TV-syncwarp-pending-at-end`), `other`, `incomplete_files`; the `ALL` rows are the
  totals. Every number of §2 and §4.
- `tv_store_counts.csv`: kernel JSONs per store and mode, duplicates dropped, `DEDUP_DIFFER`.
- `tv_by_store_id_mode.csv`: per (store, pass, suite, id, mode): kernel JSONs, non-empty, incomplete, bytes.
- `tv_firings.csv`: every firing (empty).
- `tv_per_kernel.csv.gz`: one row per kernel JSON (73,144).

Code: `eval/baselines/setup/tv_scan.py scan` (job 321683, `p_tv_scan.sh`) then `tv_scan.py agg`.

## 7. Text for `FINAL_TABLES.md`

`FINAL_TABLES.md` has sections (a) cost, (b) limitations, (c) coverage, (d) September rows; it has no
"table 3(a)". Suggested place: a new subsection at the end of **(c) Coverage**, after the paragraph that ends
"... none of the 51,500 vector-clock ones" (it can replace that sentence's `tv_violation` clause). Text:

> **(c.1) Trace-validity checks.** In all 73,135 distinct kernel JSONs of the X1b stores (51,499 vector-clock,
> 21,636 scalar-clock; first, PI, 5,400 s and 84,600 s passes, one kernel counted once), `tv_violation` is
> empty. No check fired in any suite or mode: `TV-barrier-overfill`, `TV-barrier-completion-order`,
> `TV-expected-nonzero-multiwarp`, `TV-record-after-exit`, `TV-barrier-pending-at-end`,
> `TV-syncwarp-completion-order` and `TV-syncwarp-pending-at-end` each 0. No kernel had a syncwarp instance
> that never completed (`TV-syncwarp-pending-at-end`). `TV-seq-monotonic` is checked only by the offline oracle,
> not by the runtime. The field keeps the first violation of a kernel only. Source:
> `eval/results/tv-counts/tv_counts_by_suite_mode.csv`.

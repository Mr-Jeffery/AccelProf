# X3 — the final tables

Branch `eval/final-tables` from `cuVein` f551ca0, worktree `/home/fzheng4/wt-x3`, left unmerged for Jeffery.
Written 2026-10-25. **No new runs**: every number below is read from files already in `eval/results/` (or
`eval/x1_follow/`) on this branch, by CPU-only jobs on partition `normal` (scripts and outputs in
`eval/results/final-tables/`, job logs `eval/x_logs/x3-*.log`). A number that could not be obtained is
written **missing**. Legend as CLAUDE.md A4: **proved-in-effect** = an invariant checked over the stated
stores; **tested** = a specific result asserted; **unverified** = said so. Cross-host walls are not
like-for-like (19 nodes, three CPU types, two RAM sizes, five drivers: `FINAL_SWEEP_B.md` §0).

## 0. Inputs and runtimes

**X1b replaces X1 as the primary input.** X1b (`origin/eval/final-sweep-b` 94fde73, merged into this branch
by commit f7e48cf) is the whole sweep recorded again with the same harness (`parallel.py`, `blib.py`,
`run_cuvein.py`, `setup/p_final*.sh`; the only knob that differs is scalar-clock at 16 shards) on the final
runtime. X1 predates T22 cont., T23 and T24, so its scalar-clock rows are serial and its verdict layer is
older. X1's rows stay in `eval/results/baselines-cuvein.csv`; they are used here only as the comparison
("before") column of §(a) and §(b), never as a result. `git merge-tree` against `origin/cuVein` reported no
conflict before the merge.

| input | files on this branch | runtime | role |
|---|---|---|---|
| **X1b**, 2026-10-22 02:12 – 10-24 21:56 (4,725 ids x 2 modes; 5,400 s and 84,600 s passes; scalar-clock sharded N=16) | `eval/FINAL_SWEEP_B.md`, `eval/results/final-b/merged/baselines-cuvein.csv`, `final-b/tables/`, `final-b/triage_rtraw.md` | f551ca0: libsanalyzer `5a20fd14ab6c6806`, collector `b746b4dd23e90f46`, fatbin `a2d7368bc1c61986` (built from e0e6431 = T22 cont. + T23 + T24) | primary |
| X1, 2026-10-13/16 | `eval/FINAL_SWEEP.md`, `eval/X1_FOLLOW.md`, `eval/results/baselines-cuvein.csv`, `eval/x1_follow/` | d38d057 (built from ba99486): libsanalyzer `2201fcb7`, collector `ee78cb89`, fatbin `a2d7368b` | "before" only |
| X2 (certain clock; P4 + P5, vector-clock only), 2026-10-13/14 | `eval/FINAL_CERTAIN.md`, `eval/results/final-certain/`, `final-certain-recorded/`, `final-certain-invariant/` (checked out from `origin/eval/final-certain` 7979869, not merged) | **d38d057, before T22 cont. / T23 / T24** (job 311939 on c74) | own section only; never mixed into X1b's columns |
| T23 and its follow-up | `eval/R3_CLOSURE.md`, `eval/results/t23/scan/final-2026-10-24h-vc/` (checked out from `origin/fix/r3-same-loc-closure` 6140129, not merged) | T23 merged in f551ca0 | the re-score statement in §(c) |
| T22 cont. | `eval/SHARDED_SYNC.md`, `eval/results/t22c-*` | perf build (not the installed binary; the same sources, merged into f551ca0) | cost columns of §(a); before/after of §(b) |
| X4 (rtraw) | `eval/FINAL_RTRAW.md`, `eval/results/final-rtraw/` | its own (see report) | schedule vocabulary for the lock_rtraw row |
| WARPSYNC join gap (`origin/eval/warpsync-join-gap` 3e96b5f, not brought in) | none | pre-T24 | **history only**: it measured a join gap, T24 then changed the rule; no number from it is used here |

The 16 `needs-sm90` programs (`P6-bulkcpy-*`, `P6-dsmem-*`) have no binary on the sm_89 hosts: ERROR in both
modes in every input, never run.

## (a) Cost per warp-level record

"Records" is the row's `events=` (`hb_events_count`, warp-level records; the lane-level count is
`hb_lanes_count`); for collector-only runs it is the analyzer's drained-record count, which X1_FOLLOW §1 shows
equal to X1's `events=` for heartwall, knn and the P6 program. us/record = tool wall / records. Rows that are
TIMEOUT, ERROR or `partial(...)` are not points of a fit. Scripts: `eval/results/final-tables/cost_table.py`
(log `eval/x_logs/x3-cost-*.log`); outputs `cost_rows.csv`, `cost_fit.csv`, `cost_table.md`.

Columns and runtimes:
- **collector-only** (`YOSEMITE_HB_TRACE` unset; `-n 1` and default workers): X1-follow, d38d057, EPYC 8124P (`eval/x1_follow/collector/*.json`). Only four programs have such a run; nbody and bfs: **missing**.
- **scalar-clock serial N=1**: X1, d38d057, one rep at the pass that decided the key (`baselines-cuvein.csv`).
- **scalar-clock N=1 / N=16, T22-cont perf build**: SHARDED_SYNC.md II.10 step C (`eval/results/t22c-c-<id>-n{1,16}/`), one run each, hosts named in the cell table of `cost_rows.csv`.
- **scalar-clock sharded N=16, X1b**: f551ca0, median of the 3 reps (1 rep at 84,600 s).
- **vector-clock**: X1 (d38d057) and X1b (f551ca0).

Wall in seconds, with us/record in parentheses. Native wall is the X1b scalar-clock row's.

| program | records | native (s) | collector `-n 1` | collector default | scalar serial N=1 (X1) | scalar N=1 (perf build) | scalar N=16 (perf build) | **scalar N=16 (X1b)** | vector (X1) | **vector (X1b)** |
|---|---|---|---|---|---|---|---|---|---|---|
| P7-heartwall | 8,071,484,636 | 0.872 | 2,345.1 (0.2905) | 626.4 (0.0776) | 32,057.2 (3.972) | 57,990.5 (7.185) | 4,663.9 (0.578) | **5,728.7 (0.710)** | 35,574.7 (4.407) | **61,435.9 (7.611)** |
| P9-knn | 11,144,912,500 | 12.001 | 3,304.1 (0.2965) | 835.0 (0.0749) | 44,762.4 (4.016) | 46,577.1 (4.179) | 7,567.6 (0.679) | **9,680.4 (0.869)** | 57,215.7 (5.134) | **58,674.2 (5.265)** |
| P7-nbody | 320,355,120 | 14.144 | missing | missing | 8,015.0 (25.02) | 3,783.0 (11.81) | 387.4 (1.209) | **391.0 (1.221)** | 8,197.6 (25.59) | **11,252.4 (35.12)** |
| P7-bfs | 7,436,165 | 1.371 | missing | missing | 1,506.5 (202.6) | 39.5 (5.318) | 13.9 (1.867) | **12.1 (1.625)** | 6,289.9 (845.8) | **11,500.6 (1,547)** |
| P1-BFS_CUDA_E_Topo_Determ_…_Atomic_…-slower_atomic-100n | 1,017–1,019 | 0.271 | 1.477 (1,449) | 1.060 (1,036) | 0.868 (851.8) | missing | missing | **2.626 (2,582)** | 0.868 (851.8) | **1.573 (1,547)** |
| P6-interkernel-global_readwrite_race-fixed | 1,000,004 | 0.770 | 3.871 (3.871) | 3.553 (3.553) | 4.926 (4.926) | missing | missing | **5.478 (5.478)** | 5.578 (5.578) | **6.933 (6.933)** |

Hosts of the walls above, from `cost_rows.csv`: heartwall X1b scalar c24, vector c75; knn X1b scalar c74,
vector c64; nbody X1b scalar c41, vector c24; bfs X1b scalar c74, vector c44; the X1 walls are on c52 / c58
(heartwall), c66 / c62 (knn), c66 / c62 (nbody), c74 / c51 (bfs). **Every pair of columns compares different
hosts.** The only same-node-type pairs are within SHARDED_SYNC II.10 (scalar N=1 vs N=16: 12.4x heartwall,
6.2x knn, 9.8x nbody, 2.8x bfs, one node type each; cross-node for heartwall and knn). The two short programs
are dominated by the fixed start-up (their us/record is not a per-record cost: X1_FOLLOW §1).

**Fitted law, wall = intercept + slope x records** (ordinary least squares, `cost_fit.csv`; n points):

| column | runtime | n | intercept (s) | slope (us/record) | R^2 |
|---|---|---|---|---|---|
| collector-only, `-n 1` | d38d057 | 4 | -1.757 | 0.2946 | 0.9998 |
| collector-only, default workers | d38d057 | 4 | 4.128 | 0.07542 | 0.9995 |
| scalar-clock serial N=1 | d38d057 (X1) | 6 | 1,989 | 3.807 | 0.9828 |
| scalar-clock N=1 (perf build) | perf build | 4 | 3,242 | 4.882 | 0.8584 |
| scalar-clock N=16 (perf build) | perf build | 4 | 18.36 | 0.6426 | 0.9880 |
| **scalar-clock sharded N=16** | f551ca0 (X1b) | 6 | -23.26 | 0.8166 | 0.9871 |
| vector-clock | d38d057 (X1) | 6 | 2,913 | 4.595 | 0.9737 |
| **vector-clock** | f551ca0 (X1b) | 6 | 5,993 | 5.470 | 0.9239 |

The six-program fits are leveraged by heartwall and knn (about 10^10 records each) and the intercepts of the
serial and vector columns (thousands of seconds) are not start-up times: bfs (203 and 846 us/record) and nbody
(25 us/record) lie far above the line in those columns. They are the superlinear cases of §(b). The
collector-only fits have 4 points on one host type each.

Whole-sweep fits over every complete (id, mode) row of the merged file (a row with TIMEOUT, ERROR or
`partial(...)` is excluded; the same fit for X1 is in `cost_fit.csv`):

| scope | column | n | intercept (s) | slope (us/record) | R^2 |
|---|---|---|---|---|---|
| all | scalar-clock sharded N=16 (X1b) | 4,706 | 3.741 | 1.320 | 0.7057 |
| all | vector-clock (X1b) | 4,704 | 11.92 | 6.256 | 0.9100 |
| all | scalar-clock serial N=1 (X1) | 4,705 | 5.066 | 4.082 | 0.9243 |
| all | vector-clock (X1) | 4,705 | 9.833 | 5.077 | 0.9112 |

By suite, X1b (scalar N=16 | vector):

| suite | n (scalar / vector) | scalar intercept s, slope us/rec, R^2 | vector intercept s, slope us/rec, R^2 |
|---|---|---|---|
| P1 | 400 | 2.041, 1.672, 0.31 | 0.774, 29.24, 0.53 |
| P3 | 60 | 2.109, 6.471, 0.06 | 1.902, 29.61, 0.47 |
| P4 | 28 | 2.184, 0.698, 0.89 | -0.829, 48.73, 0.49 |
| P5 | 33 | 1.725, 9,420, 0.009 | 1.867, 38,270, 0.07 |
| P6 | 34 | 4.742, 1.719, 0.99 | -158.6, 29.89, 0.94 |
| P7 | 12 / 11 | 537.8, 1.616, 0.60 | 2,066, 6.132, 0.89 |
| P9 | 9 / 8 | 473.5, 0.979, 0.88 | 1,537, 5.880, 0.92 |
| PI | 4,130 | 1.453, 5.420, 0.03 | 0.980, 46.56, 0.11 |

Facts: on the suites whose programs run 1-5 s (P1, P3, P5, PI) the wall is a start-up of about 1-2 s and records
explain little (R^2 below 0.55 everywhere); there the "law" is the intercept. The slope is determined by P6,
P7 and P9, where the records are 10^6-10^10.

## (b) Limitations, by mechanism

Walls and peaks are from the X1b merged CSV unless another file is named. Peak = the harness's summed-VmRSS
peak. `hb_stats` values are read from the kernel JSONs in the BeeGFS stores by `hb_stats_dump.py`,
`hb_series.py`, `hwm_changes.py` (logs `eval/x_logs/x3-q1-*`, `x3-q2-*`, `x3-q3-*`, `x3-q4-*`; the values are
quoted below).

| program (mode) | row | mechanism, from the files | what it was doing at the kill |
|---|---|---|---|
| **P7-particlefilter (vector-clock)** | TIMEOUT at 5,400 s, 3 reps, c43 (125 GB), peak 124.1-125.4 GB, 3 kernels (`coverage_partial_rows.csv`). X1: RACE (31), c64, rc 1 at 5,313-5,331 s, 185.3-185.4 GB, 3 kernels | **buckets term.** Kernel 0 (`kernel_likelihood`), 400,128 threads: `buckets.entries` 143,400,320 (358.4 per thread; 4.66 per location), `locations` 30,803,036, `groups` 60,403,164, `buckets.bytes` 4,016,387,168 (`bytes_est` 14,864,533,272); `vc.bytes_est` 42,598,336. Kernels 1 and 2: 1,564 and 2,806,256 entries. RSS (`hwm_kb`) after each of the 3 finished kernels is 5.03-5.05 GB. The "hot locations" count behind 143.4 M entries is not in `hb_stats`: **missing** | in the 4th launch, which has no kernel JSON and no kernel-end `hb_stats`: RSS rose from about 5 GB to 124-125 GB (X1b) / 185 GB (X1); growth inside it is not attributable (**missing**). SHARDED_SYNC §7: at N = 32 on a 755 GB node the scalar-clock run was OOM-killed in kernel 4 at 915 s, 757.8 GB |
| P7-particlefilter (scalar-clock, N=16) | RACE (31) kept, `partial(rc=1)`, c64, 234-242 s, 189.5-189.7 GB, 3 kernels | same buckets (`bytes` 4,016,880,880, entries 143,400,320) plus 16 shards' sync clocks (`vs.bytes_est` 262,142,976 at 400,128 threads) | OOM (SIGKILL inferred) in the 4th launch |
| **P7-bfs** (scalar-clock) | X1 1,506.5 s (5,400 s pass, c74); T22-cont perf build: 1,841.5 s -> 39.5 s with the two fixes at N=1 (c40; `t22c-cold-P7-bfs-cuda-n1`, `t22c-c-P7-bfs-cuda-n1`), 13.9 s at N=16; **X1b 12.1 s** (c74, RACE 31) | the bfs shape: every thread of the grid writes one flag word, so each Check walked all earlier writers of the word; the early exit in Check (Fix 2) removed it (SHARDED_SYNC II.0, II.9) | cap not reached after the fixes. Before: TIMEOUT at 1,200 s after 17 of 24 kernels (X1_FOLLOW §4) |
| P7-bfs (vector-clock) | X1 6,289.9 s (c51); **X1b 11,500.6 s** (c44, RACE 31) | the fixes are scalar-clock only (II.0); vector-clock runs Part I's code, so no before/after exists; the bisect puts its crossing at T9 (per-location buckets, X1_FOLLOW summary). The two walls are cross-host, the change is not attributed | finished |
| **P7-nbody** (scalar-clock) | X1 8,015.0 s (c66, 24 h pass); perf build 3,783.0 s at N=1 with the fixes, 387.4 s at N=16; **X1b 391.0 s** (c41, CLEAN) | broadcast-read shape: 1,024,096,000 slots on 112,000 locations (9,144 per location), about 90 % of CPU self time in the location's slot array (80 % insertion) (X1_FOLLOW §3); Fix 1 (adaptive tail) took the launch period from 800 s to 266 s at N=1 (SHARDED_SYNC II.8) | cap not reached after the fixes. Before: TIMEOUT at 1,200 s after 3 of 30 kernels |
| P7-nbody (vector-clock) | X1 8,197.6 s (c62); **X1b 11,252.4 s** (c24, CLEAN, peak 29.0 GB) | vector-clock code unchanged; cross-host | finished |
| **P9-expdist** (vector-clock) | TIMEOUT at 84,600 s, **nkernels 0**, peak 21,016.5 MB, rc 124 (X1: 86,400 s, 0 kernels) | not established. Under scalar-clock the first kernel is `distance<float>` (82,511,264 records, 11,789,856 locations, 316,221,984 entries, `buckets.bytes` 8,504,932,784; `t22c-d84600-P9-expdist-cuda-n16/kstats.txt`) | no kernel JSON in 84,600 s; the store's log tail shows only the tool's start line, so the run was inside, or before the end of, the first launch. Which phase: **missing** |
| P9-expdist (scalar-clock) | X1: TIMEOUT 86,400 s with 32 kernels, peak 9,912 MB. **X1b: RACE (22) at 2,696.8 s**, 40 kernels, 1,650,046,572 records, 13.8 GB | finished at N=16 | -- (18 of the 22 reports are real, 4 are the shared-memory `atomicAdd` false-report class: FINAL_SWEEP_B §11) |
| **P7-stencil1d** (scalar-clock, N=16) | TIMEOUT at 84,600 s, **435 kernel JSONs, the last (`kernel_434`) cut mid-write: 434 complete**, peak 168.1 GB, c63 | **sync-clock term x N.** Kernel 0: `buckets.bytes` 74,449,421,152, `entries` 2,430,599,161, `locations` 409,993,223; `vs.bytes_est` 86,705,700,864 for 134,217,728 threads in 16 shards (SHARDED_SYNC §6: each shard keeps every thread's clock); RSS at kernel end 169.3-172.1 GB. About 196.5 s per kernel in steady state (mtimes of kernels 0-20) | kernel_434 (the 435th launch) was being written when the cap struck; total launches unknown (SHARDED_SYNC §7 reports 1,000 launches; X1_FOLLOW partial note uses "?"). X1 at N=1: 147 kernels in 86,400 s, 84.1 GB |
| P7-stencil1d (vector-clock) | TIMEOUT at 84,600 s, **117 kernel JSONs** (all readable), peak 98.5 GB | `vc.bytes_est` 14,009,040,896 (134,217,728 threads) + `buckets.bytes` 74,448,929,632; RSS 99.4 -> 100.9 GB over the run; about 680-790 s per kernel | inside the 118th launch |
| **P9-atomicCAS** (vector-clock) | 1,200 s: TIMEOUT x3, 0 kernels, 96.2-100.0 GB (the rows that stand). 84,600 s: ERROR (OOM, "Killed"), 15,229.6 s, 30,000 kernels, 189.6 GB (dropped by the merge rule). X1 5,400 s: TIMEOUT x3 (10,000 / 13,636 / 13,948 kernels); X1 24 h: OOM at 17,625 s, 30,000 kernels | see "atomicCAS hb_stats" below: **neither accounted term grows; the memory is not in `hb_stats`** | OOM at 189.6 GB on a 188 GB node (inferred from SIGKILL and the peak) |
| P9-atomicCAS (scalar-clock) | TIMEOUT at 84,600 s, **60,000 kernels**, peak 1,103.5 MB, c73 (X1: 60,000 kernels at 86,400 s, 908 MB) | time: 1,103 MB is not a memory limit; SHARDED_SYNC II.14 (perf build, same cap) found the 60,000th kernel written 5,352 s into the run and none after: **why is not identified** | -- |
| P7-haversine (vector-clock) | TIMEOUT at 5,400 s x3, 59-61 of 100 kernels, 9.4-9.5 GB, c24 (X1: CLEAN at 4,952.7-5,101.5 s, c52) | not memory (9.5 GB). Walls are cross-host (7302P vs 9115); the cause is not separated | inside a kernel after 59-61 of 100 |

**atomicCAS `hb_stats`** (the brief: read vc against buckets from the 5,400 s store's last completed kernel).
The only 5,400 s atomicCAS store is X1's (`final-2026-10-long/P9-atomicCAS-cuda/vector-clock-partial-rep2`,
d38d057; X1b skipped its 5,400 s pass by deviation (a), FINAL_SWEEP_B §1). It holds 13,948 kernel JSONs and
keeps one rep; all are readable. Kernel 13,947, the last:
`vc.bytes_est` **23,101,568** B (262,144 threads), `buckets.bytes` **6,279,344** B (`bytes_est` 14,680,240;
262,144 entries, 1 location), `vs.bytes_est` 6,324,352, `hwm_kb` 101,907,504 (101.9 GB). So vc is **3.68x**
buckets in bytes (1.57x in `bytes_est`), and both are about 30 MB against 101.9 GB of RSS.
**Which term grew: neither.** Over all 13,948 kernels `vc.bytes_est` has min = max = 23,101,568 and
`buckets.bytes` min = max = 6,279,344 (`hwm_changes.py`, `x3-q4`). `hwm_kb` is 100,123,200 at kernel 0 and steps
twice: +1.78 GB at kernel 10,000 (`buckets.entries` 291,552 there) and +160 KB at kernel 10,239. X1b's
84,600 s store (30,000 kernels, f551ca0): `vc.bytes_est` and `buckets.bytes` constant (same values), `hwm_kb`
101.25 GB at kernel 0, steps +1.7 MB (kernel 13,638), **+6.98 GB at kernel 20,000** (`buckets.entries` 291,104),
108.23 GB at kernel 29,999. The ~100 GB is therefore present before the first kernel completes (X1b's 1,200 s
reps hold 96-100 GB with no kernel written); what it is, and what the step at kernels 10,000 / 20,000 is, are
**not established** from `hb_stats`.

Missing for this section: the nodes' kernel logs (OOM is inferred from SIGKILL and peaks); a kernel-end
`hb_stats` for any launch that did not finish (particlefilter's 4th, expdist's 1st vector-clock launch,
stencil1d's last); the maximum readers per location of nbody (X1_FOLLOW §3: "not recorded").

### Decided 2026-10-25 (Jeffery) — `P5-race_interblock_none-lock_rtraw`: count as recorded (RACE, one detection per mode)

The two other ways are kept below for the record; the as-recorded row is the one in force.

X1b: RACE in both modes (one report, the `dummy` WAW 0x170 / 0x2f0; vector-clock reports carry
`a2_uncertain`). X1 and X2's recorded leg: CLEAN. Triage (`final-b/triage_rtraw.md`): the X1b recordings are
A2-inverted (the lock hand-off is lost), the `dummy` pair is ordered by the fenced lock in every schedule, and
the labelled rtraw pair is a strong conflict in both runs. Re-recordings with the f551ca0 runtime and X1b's
harness: **c79 inverts 29 of 120** (vector-clock 12 of 60, scalar-clock 17 of 60; every inverted recording RACE,
every normal one CLEAN), **c42 inverts 0 of 20** (all CLEAN); c62-type job 320429 queued at the time of the
triage, **missing**. X1b's 6 of 6 on c79 is unexplained. The row, both ways:

| counting | P5 vector-clock RACE / CLEAN | P5 scalar-clock RACE / CLEAN | all labelled suites, TP/positives, vector-clock | scalar-clock |
|---|---|---|---|---|
| **as recorded** (X1b; matches the label, one detection per mode) | 5 / 28 | 3 / 30 | 1939 / 2108 | 1938 / 2108 |
| **read CLEAN** (the schedule-normal outcome: X1, c42; "by pair" it is a CLEAN, and the RACE is a false report) | 4 / 29 | 2 / 31 | 1938 / 2108 | 1937 / 2108 |
| by pair, as recorded | the reported pair is a false positive, the labelled pair is not reported as a data race | same | -- | -- |

Source: `final-b/tables/README.md` (table 1 of `BASELINES_SUMMARY.md`), `triage_rtraw.md`. X2 (certain clock,
d38d057, c74) has the same program moving CLEAN -> RACE at the certain point only in vector-clock mode, on
X4's schedule B (`FINAL_CERTAIN.md` summary 3): a third, differently caused way for the row to move.

## (c) Coverage

**Ids and keys.** 4,725 manifest ids x 2 modes = 9,450 (id, mode) keys; missing keys 0; ids in the CSV not in
the manifest 0; 28,234 CSV rows (`coverage_verdicts.md`, recomputed here from the merged file; equals
`FINAL_SWEEP_B.md` §3):

| suite | ids | vector-clock RACE / CLEAN / TIMEOUT / ERROR | scalar-clock RACE / CLEAN / TIMEOUT / ERROR |
|---|---|---|---|
| P1 | 400 | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 |
| P3 | 60 | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 |
| P4 | 28 | 16 / 12 / 0 / 0 | 16 / 12 / 0 / 0 |
| P5 | 33 | 5 / 28 / 0 / 0 | 3 / 30 / 0 / 0 |
| P6 | 50 | 8 / 26 / 0 / 16 | 8 / 26 / 0 / 16 |
| P7 | 14 | 3 / 8 / 3 / 0 | 4 / 9 / 1 / 0 |
| P9 | 10 | 2 / 6 / 2 / 0 | 3 / 6 / 1 / 0 |
| PI | 4,130 | 2,420 / 1,710 / 0 / 0 | 2,420 / 1,710 / 0 / 0 |
| **all** | **4,725** | **2,670 / 2,034 / 5 / 16** | **2,670 / 2,037 / 2 / 16** |

**Node-hours** (`final-b/sacct.txt`, recomputed by `coverage.py`; `coverage_nodehours.md`):

| job name | node-hours | | job name | node-hours |
|---|---|---|---|---|
| x1b-dryrun | 0.0 (23 s) | | x1b-final-long (5,400 s) | 32.3 |
| x1b-final (first pass) | 51.8 | | x1b-final-24h (84,600 s) | 192.7 |
| x1b-final-pi | 15.2 | | x1b-final-r1 + r2 (node-probe stops) | 0.2 |
| **sacct total** | **292.1** | | + post jobs 320157, 320365 (`FINAL_SWEEP_B.md` §8) | 0.3 -> **292.4** |

Other inputs: X1 434.4 node-hours (`FINAL_SWEEP.md` §8); X2 job 311939 4 h 01 m on one node = 4.0 (its
same-trace check job 312216: **missing**); T22-cont and T23 scans, and the lock_rtraw re-recordings (320428,
320490, hold 320880), are not counted in either total.

**Residual keys** (collapsed verdict TIMEOUT or ERROR; `coverage_residuals.csv`):

| key | verdict | reason class (`classify_residuals.py`) | basis |
|---|---|---|---|
| 16 `P6-bulkcpy-*` / `P6-dsmem-*` x 2 modes (32 keys) | ERROR | needs-sm90 | binary needs sm_90; never run |
| P7-particlefilter, vector-clock | TIMEOUT 5,400 s | hb-state-memory | 124-125 GB on a 125 GB host (§(b)); the 24 h pass is not run (Jeffery, 10-24) |
| P7-haversine, vector-clock | TIMEOUT 5,400 s | hb-clock-hang (class name only: 59-61 of 100 kernels written) | the 24 h pass is not run (Jeffery, 10-24) |
| P7-stencil1d, scalar-clock | TIMEOUT 84,600 s | hb-state-memory | 168.1 GB |
| P7-stencil1d, vector-clock | TIMEOUT 84,600 s | hb-state-memory | 98.5 GB |
| P9-atomicCAS, vector-clock | TIMEOUT 1,200 s (the 84,600 s row is an OOM ERROR and is dropped) | hb-state-memory | 96-100 GB, no kernel written |
| P9-atomicCAS, scalar-clock | TIMEOUT 84,600 s | time-cap | 60,000 kernels, 1.1 GB |
| P9-expdist, vector-clock | TIMEOUT 84,600 s | hb-clock-hang (class name only: 0 kernels) | 21.0 GB |

**Partial rows under the stated rule** (X1_FOLLOW Part 4: a run killed by OOM or the time limit keeps every
verdict it produced; the note reads `partial: <OOM|TIMEOUT> after N of M kernels, wall s, cap=C`; N = the row's
`nkernels`, M = the kernel count of a complete row of the same program, "?" if none). X1b did not apply the rule
to its shard CSVs (`FINAL_SWEEP_B.md` §1 (j)); it is applied here to the 16 non-complete rows of the merged
file (`coverage_partial_rows.csv`, one line per rep):

| program, mode | rows | note under the rule | verdict kept |
|---|---|---|---|
| P7-particlefilter, scalar-clock | 3 | partial: OOM after 3 of ? kernels, 234.0-242.4 s, cap=1200 | RACE (31) |
| P9-atomicCAS, vector-clock | 3 | partial: TIMEOUT after 0 of ? kernels, 1200.0 s, cap=1200 | TIMEOUT |
| P7-haversine, vector-clock | 3 | partial: TIMEOUT after 61 / 59 / 61 of 100 kernels, 5400.0 s, cap=5400 | TIMEOUT |
| P7-particlefilter, vector-clock | 3 | partial: TIMEOUT after 3 of ? kernels, 5400.0-5400.2 s, cap=5400 | TIMEOUT |
| P7-stencil1d, scalar-clock | 1 | partial: TIMEOUT after 435 of ? kernels, 84600.0 s, cap=84600 (434 complete) | TIMEOUT |
| P7-stencil1d, vector-clock | 1 | partial: TIMEOUT after 117 of ? kernels, 84600.0 s, cap=84600 | TIMEOUT |
| P9-atomicCAS, scalar-clock | 1 | partial: TIMEOUT after 60000 of ? kernels, 84600.0 s, cap=84600 | TIMEOUT |
| P9-expdist, vector-clock | 1 | partial: TIMEOUT after 0 of 40 kernels, 84600.0 s, cap=84600 | TIMEOUT |

The one RACE among them (particlefilter, scalar-clock) is a RACE seen in a run killed by OOM, which the
harness rule keeps (`FINAL_SWEEP_B.md` §1 (i)); particlefilter's vector-clock RACE (31) of X1 is not in X1b.

**Re-scores that apply to the verdicts used here.** T23's `same_loc` closure is in the runtime of every X1b
row. `R3_CLOSURE.md` and its follow-up (6140129; `eval/results/t23/scan/final-2026-10-24h-vc/`): X1's 24 h
vector-clock store, scanned once BeeGFS returned, moved **0** verdicts (9 of its 11 programs have a
`vector-clock` kernel directory). `FINAL_SWEEP_B.md` §6 (b)-(d) holds the X1b sanity checks: no
`tv_violation`, no static-leg-only verdict, N = 16 in all 21,636 scalar-clock kernel JSONs and in none of the
51,500 vector-clock ones.

## (d) The September rows above the lane cutoff

The 2026-09-22 recording (`eval/results/superseded_baselines-cuvein-2026-09-22.csv`, runtime b7d463e) was
analysed by replaying `hb_events`; above `CUVEIN_BARRIER_PASS_MAX_LANES` (default 5,000,000 lane-accesses per
kernel; `python/sync_dominance.py:1350`, `eval/README.md` "Re-analyzing existing traces") scalar-clock mode loses
the barrier pass and R3 falls back to region dominance. A program is **above the cutoff** here when any kernel
JSON in X1b's stores (any mode, all passes, partial dirs included) has `hb_lanes_count` above 5,000,000
(`sept_cutoff.py`, job 321193; `sept_over_cutoff.csv`). For programs cut by a cap this is a lower bound.

| suite | ids | above the cutoff | of those with a September row | no kernel JSON read |
|---|---|---|---|---|
| P1 | 400 | 0 | 0 | 0 |
| P3 | 60 | 0 | 0 | 0 |
| P4 | 28 | 8 | 8 | 0 |
| P5 | 33 | 0 | 0 | 0 |
| P6 | 50 | 12 | 12 | 16 (the needs-sm90 programs) |
| P7 | 14 | 12 | 12 | 0 |
| P9 | 10 | 7 | 7 | 0 |
| PI | 4,130 | 0 | 0 | 0 |
| **all** | **4,725** | **39** | **39** | 16 |

**These 39 ids' September rows are SUPERSEDED and are not cited** anywhere in this report or its tables; the
September verdicts are deliberately not written out (the join in `sept_table.py` reads X1b's verdicts only).
The replacement is X1b's row:

| id | max lane-accesses in one kernel | X1b vector-clock | X1b scalar-clock |
|---|---|---|---|
| P4-1dconv-norace-large | 15,728,622 | CLEAN | CLEAN |
| P4-1dconv-racy-large | 15,728,622 | RACE | RACE |
| P4-matrix-multiplication-norace-large | 242,961,032 | CLEAN | CLEAN |
| P4-matrix-multiplication-norace-small | 5,970,424 | CLEAN | CLEAN |
| P4-matrix-multiplication-racy-large | 242,851,848 | RACE | RACE |
| P4-matrix-multiplication-racy-small | 5,964,568 | RACE | RACE |
| P4-uts-norace-large | 13,804,197 | CLEAN | CLEAN |
| P4-uts-racy-large | 12,842,932 | RACE | RACE |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | 13,488,881,664 | RACE | RACE |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | 13,488,881,664 | RACE | RACE |
| P6-asyncmemcpy-memcpy_htod_kernel_race-fixed | 268,435,488 | CLEAN | CLEAN |
| P6-asyncmemcpy-memcpy_htod_kernel_race-racy | 268,435,488 | CLEAN | CLEAN |
| P6-hostdevice-global_writeread_race-fixed | 64,000,000 | CLEAN | CLEAN |
| P6-hostdevice-global_writeread_race-racy | 64,000,000 | CLEAN | CLEAN |
| P6-hostdevice-global_writewrite_race-fixed | 16,000,000 | CLEAN | CLEAN |
| P6-hostdevice-global_writewrite_race-racy | 16,000,000 | CLEAN | CLEAN |
| P6-interkernel-global_readwrite_race-fixed | 32,000,032 | CLEAN | CLEAN |
| P6-interkernel-global_readwrite_race-racy | 32,000,032 | CLEAN | CLEAN |
| P6-interkernel-global_writewrite_race-fixed | 56,250,000 | CLEAN | CLEAN |
| P6-interkernel-global_writewrite_race-racy | 53,125,000 | CLEAN | CLEAN |
| P7-backprop-cuda | 12,648,448 | CLEAN | CLEAN |
| P7-bezier-surface-cuda | 3,422,552,064 | CLEAN | CLEAN |
| P7-bfs-cuda | 11,257,847 | RACE | RACE |
| P7-bitonic-sort-cuda | 50,334,324 | CLEAN | CLEAN |
| P7-haversine-cuda | 188,743,680 | TIMEOUT | CLEAN |
| P7-heartwall-cuda | 1,886,759,613 | RACE | RACE |
| P7-hotspot-cuda | 7,405,840 | CLEAN | CLEAN |
| P7-lavaMD-cuda | 9,868,315,232 | CLEAN | CLEAN |
| P7-mandelbrot-cuda | 8,294,400 | CLEAN | CLEAN |
| P7-nbody-cuda | 1,024,144,000 | CLEAN | CLEAN |
| P7-particlefilter-cuda | 145,598,949 | TIMEOUT | RACE |
| P7-stencil1d-cuda | 2,430,599,161 | TIMEOUT | TIMEOUT |
| P9-crs-cuda | 8,915,480 | CLEAN | CLEAN |
| P9-dxtc2-cuda | 88,928,584 | RACE | RACE |
| P9-expdist-cuda | 1,697,991,488 | TIMEOUT | RACE |
| P9-gpp-cuda | 32,768,000 | CLEAN | CLEAN |
| P9-knn-cuda | 3,011,510,272 | CLEAN | CLEAN |
| P9-overlap-cuda | 16,777,216 | CLEAN | CLEAN |
| P9-tridiagonal-cuda | 430,080,000 | RACE | RACE |

No P1, P3, P5 or PI program is above the cutoff, so their September rows are not marked by this rule (the
whole September file is in any case replaced by X1b as the primary input, §0).

## Open decisions (recorded, not settled)

1. **lock_rtraw counting rule: DECIDED (Jeffery, 2026-10-25): as recorded (RACE, a detection per mode).** The other two ways stay in §(b) for the record.
   Whether the c79 inversion rate (29 of 120) is a node effect is not
   established; the c62-type re-recording (320429) was still queued.
2. **The 24 h pass for P7-particlefilter and P7-haversine vector-clock** was not run (Jeffery, 10-24). Both
   stay TIMEOUT at 5,400 s; particlefilter's 5,400 s task ran on a 125 GB host.
3. **Labels** (`FINAL_SWEEP_B.md` §11): atomicCAS (the upstream fix makes the binary race-free; cuVein gives
   no verdict), knn (race-free upstream, CLEAN in both modes, scored as a miss against a RACE label), expdist
   and dxtc2 (still racy for a different reason). The labels are unchanged.
4. **Merging**: `eval/final-sweep-b`, `eval/final-certain` and `fix/r3-same-loc-closure` are not merged into
   cuVein; this branch contains X1b by a merge commit and X2/T23-follow-up by file checkout only.
5. **The paper's tables are still X1's** (`BASELINES_SUMMARY.md` on cuVein); X1b's are in
   `eval/results/final-b/tables/` (`README.md` lists what changed: 5 verdicts, every overhead cell).

## What remains unverified (carried from `FINAL_SWEEP_B.md` §10, and added by this report)

- P7-particlefilter and P7-haversine vector-clock stay TIMEOUT at 5,400 s; whether particlefilter's TIMEOUT
  reflects the 125 GB host (X1's runs needed 185 GB) is not established; haversine's walls are cross-host.
- The 84,600 s rows are single reps.
- Walls are cross-host: 19 nodes, three CPUs, two RAM sizes, five drivers.
- OOM is inferred from SIGKILL and the peaks; the nodes' kernel logs were not read (atomicCAS vector-clock,
  particlefilter scalar-clock).
- P5 lock_rtraw: c79 inverts the hand-off in about a quarter of its recordings and 6 of 6 in X1b; the
  mechanism is not established; no other program shows the effect on c79.
- Not done for X1b: X1-follow's partial-run notes in the shard CSVs (applied here to the merged file only);
  why cuVein's slowdowns on short-program suites are about 1.3x X1's on the same CPU type.
- Label questions: P6-asyncmemcpy-…-fixed is RACE again at 84,600 s; P9-knn (labelled racy) is CLEAN.
- **Added here:** `FINAL_SWEEP_B.md` §4 says the X1b store keeps no vector-clock kernel JSON for
  particlefilter; the store has `final-2026-11-long/P7-particlefilter-cuda/vector-clock-partial-rep1` with
  3 kernel JSONs (read for §(b)). The collector-only, scalar-clock N=1 and N=16 perf-build columns are
  different runtimes from X1b's and cross-host. The us/record fits are least squares over programs whose
  records span 10^3-10^10; they describe these runs, not a model. The lane count per program in §(d) is a
  lower bound where a cap cut the run. Kernel counts "of M" are unknown ("?") for the four programs no run
  finished.

## Files

`eval/results/final-tables/`: `cost_table.py` (+ `cost_rows.csv`, `cost_fit.csv`, `cost_table.md`),
`coverage.py` (+ `coverage_verdicts.md`, `coverage_residuals.csv`, `coverage_partial_rows.csv`,
`coverage_nodehours.md`), `sept_cutoff.py`, `sept_table.py` (+ `sept_over_cutoff.csv`,
`sept_over_cutoff_summary.md`, `sept_superseded.md`), `hb_stats_dump.py`, `hb_series.py`, `hwm_changes.py`,
`probe_stores.py`, `q1.sh`-`q4.sh`, `run_*.sh`. Logs: `eval/x_logs/x3-*.log`.

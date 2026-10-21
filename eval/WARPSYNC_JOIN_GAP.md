# WARPSYNC join gap: diverged-warp syncwarp records across the kept stores

Branch `eval/warpsync-join-gap`, worktree `/home/fzheng4/wt-warpsync-join-gap`, cut from `cuVein` afccba7. Left
unmerged. Measurement only: nothing in `sanalyzer/`, `nv-compute/` or `python/` changed. No GPU; every job ran in
partition `normal`. Legend as in CLAUDE.md A4: **proved-in-effect** = checked over every item stated; **tested**
= a specific result asserted; **unverified** = said so.

**Status (2026-10-20 23:55).**
- **Done:** the scan of every kept store, and the census of 8,351 of the 8,720 dumps with diverged-warp records.
- **Stopped:** BeeGFS failed again at 23:11 ("Communication error on send" on every node probed), which stopped the
  last retries.
- **Not run:** the vector-clock replay of 1,213 dumps, the census of 96 dumps, and X1 coverage. §8 lists them, with
  the commands that finish them.

## 0. Findings first

1. **Diverged arrivals at a `WARPSYNC` are common in the stores.**
   - Of the 497,823 kernel JSONs of all stores, 105,668 hold hb_events records and 11,083 hold syncwarp records.
     **8,720 hold a partial one**: a group of a diverged warp, with an active mask that does not cover the sync mask.
   - Over the 8,351 dumps censused with a CFG:
     - **(1)** 1,469,661 diverged instances completed, and 5,978 were still open at the end of their launch;
     - **(2)** 20,193,938 memory records of lanes that had not arrived yet (45,112,358 lane accesses; 19,903,071
       global, 290,867 shared).
   - They occur in P1 and P3 (ECL-CC, X5's case: CUDA's out-of-line `$__internal_0_$__cuda_sm70_warpsync`) and in P4
     (graph-coloring, graph-connectivity, reduction, uts, matrix-multiplication: inline `WARPSYNC` instructions).
     No other suite has any (§2).
2. **Merging every partial instance at its true completion moves no reported race pair where it was measured.**
   - At X5's level (L1), no pair appears or disappears in any dump where the replay finished:
     - the vector clock, through `hb_oracle.analyze`, in 7,136 dumps;
     - the barrier-only clock, through the oracle in those 7,136 and through `sync_dominance.barrier_only_pairs`
       in 8,341 dumps.
   - The two implementations of the barrier-only clock agree in every dump where both ran (proved-in-effect).
3. **The merge does change finer facts.**
   - **37 dumps (L2):** a warp-distance conflict aggregate appears in `P4-graph-connectivity-racy-small`'s
     `linkKernel`: `global:0x160-0x400:WAR:DR` gains 435–439 instances at warp distance. The pair was already
     reported at block distance (5,520 instances), so its report and its widest distance are unchanged.
   - **Counts only (L3):** 143 dumps for the oracle and 249 for the barrier-only pass, all in P4-graph-connectivity
     and P1 Pull ECL-CC programs (§3).
4. **Missing (reasons in §4).**
   - The vector-clock replay of 1,213 merged dumps:
     - the oracle ran out of its 10 GB child cap in 811;
     - its strict trace-validity check refused 386 P4 dumps (`TV-barrier-completion-order`);
     - 16 others were not run, ran past 4 h, or were stopped by the outage.
   - None of the 17 P4 matrix-multiplication-large dumps (7.6 M records each) has a finished oracle replay. Their
     barrier-only pass finished for 4.
   - 96 dumps were not censused (the outages).
   - 271 dumps have an empty dot listing: 261 in non-store task directories, 10 censused during the outage.
5. **The method reproduces X5.** All 60 of X5's recordings give the same instance counts. The late-record counts are
   equal in 52; in the other 8, X5 had dropped the global records of the 1296-node programs before its census (§5).

## 1. Scope, definitions, method

**The gap** (X5_BYTE_PAIRS §4, b5e10b4).
- A warp that reaches a `WARPSYNC` diverged executes it in groups. The trace holds one `syncwarp` record per group,
  with the full `sync_mask` and a partial `active_mask`.
- HbClock (`sanalyzer/src/tools/pc_dependency_analysis.cpp:1661-1668`) and the oracle (`python/hb_oracle.py:672-677`)
  join every `sync_mask` lane at each record. The first group's record therefore orders a late lane's pre-arrival
  accesses as if that lane had arrived.
- The proof models a syncwarp record as a complete instance (`design/proof/hb_proof.tex:145`). Its A3 (`:206-208`)
  states the release condition for barriers only.
- These lines are unchanged on this branch: `git diff --stat 4094187 afccba7 -- sanalyzer nv-compute python design/proof`
  is empty.

**Stores.** CLAUDE.md A2 names the kept traces: every directory under `/mnt/beegfs/fzheng4/cuvein_traces/`, and the home
copies `eval/baselines/traces_keep*` (since T-H, behind symlinks into `/mnt/beegfs/fzheng4/home_archive/eval_baselines/`).
- All were listed: 604,357 kernel JSONs, 497,823 unique real files, 9.17 TB.
- The other top-level BeeGFS directories (task working directories, not stores) were listed too and are reported as
  `other:`.
- A **row** is one (store, run directory): `<program>/<mode>`, `<program>/<mode>-partial-repN` for a timed-out
  run's kept dump, else the kernel JSON's directory.
- Several stores list the same files through symlinks (t16-certain's P3 ECL-CC directories point into
  full-2026-09-22, for instance). For the rows with diverged instances, t9-before, t10-after, t12-after and
  t16-certain show exactly t9-after's numbers. Row counts therefore repeat a dump once per store that lists it.
  The **dump** counts of §0 are of unique real files.

**Definitions** (as briefed):
1. **Diverged syncwarp instances** — X5's rule: per (block, warp, pc), consecutive syncwarp records starting with
   one whose active mask does not cover the sync mask, until the union covers it. *Completed* means it covered the
   sync mask; *open* means it never did in the launch.
2. **Memory records of lanes not yet arrived** — read / write / atomic records of the warp, issued while an
   instance is open, by a sync-mask lane outside the union so far, each record counted once.
   - X5's own count, once per open instance, is identical in total (20,193,938).
   - A syncwarp record at another pc while an instance of the same warp waits for some of its lanes (a completion
     across call sites, which a per-pc key would miss): 0.
3. **Race pairs, per-record join vs merged.**
   - The merge is X5's `partial_instances`, copied verbatim from `x5b_partial.py` (b5e10b4) into `wjg_census.py`:
     each completed instance becomes one record at its completion (active mask = the union; earlier records
     dropped).
   - Both traces run through `hb_oracle.analyze`, the specification HbClock matches bit for bit (CLAUDE.md A4),
     and through `sync_dominance.barrier_only_pairs`, the scalar-clock mode's offline pass. No `CUVEIN_*`
     overrides; the oracle's default strict trace-validity checks stay on.
   - Compared per launch:
     - **L1** (X5's keys): `space:a_pc-b_pc:kind:class` for races, `a_pc-b_pc` for the sync-only set;
     - **L2**: adds thread distance and async side;
     - **L3**: adds counts and `a2_uncertain`.
   - A launch without a completed instance replays equal by construction and is not replayed.

**Pipeline** (`eval/baselines/setup/`; jobs in §9):
- `wjg_scan.py list` / `scan`: a byte scan of every real file, in chunks cut at record starts.
  - Jobs share a queue through O_EXCL claim files.
  - `STEP=fix` rescans the files whose first scan saw no spaced `"hb_events": [` key: t14-after stores compact JSON.
- `wjg_census.py run`: per dump with a partial record, in child processes under `RLIMIT_AS` and a timeout:
  - the census, and the SASS at each partial-record pc;
  - the merged dump;
  - the barrier-only pass and the oracle, each on both traces.
  - Dumps of 2 GB and more are read one record at a time (`StreamDump`, `partial_instances_stream`). orjson cannot
    hold them under the cap, and the collector writes records in seq order, which the census checks.
- `wjg_tables.py`: rows, tables, the moves, the X5 cross-check. Its output is `eval/results/wjg/report_tables.md`
  (every row with a diverged instance), `rows.csv`, `moves.json` and `x5_check.json`.

## 2. The table

Per suite. A row is a (store, run directory) holding records. "Fully replayed" means every launch with a completed
instance finished its oracle replay.

| suite | rows | rows with a diverged instance | (1) instances completed / open | (2) late-lane memory records | rows fully replayed (oracle) | rows fully through the barrier-only pass | rows where an L1 pair moves (races / sync-only) |
|---|---|---|---|---|---|---|---|
| P1 | 5,838 | 311 | 919,301 / 0 | 7,829,832 | 40 | 310 | 0 / 0 |
| P2 | 876 | 0 | — | — | — | — | — |
| P3 | 1,282 | 525 | 332,590 / 0 | 734,254 | 404 | 525 | 0 / 0 |
| P4 | 984 | 561 | 1,250,173 / 9,240 | 23,957,841 | 432 | 517 | 0 / 0 |
| P5 | 1,251 | 0 | — | — | — | — | — |
| P6, P6small | 810 | 0 | — | — | — | — | — |
| P7 | 112 | 0 | — | — | — | — | — |
| P8 | 16 | 0 | — | — | — | — | — |
| P9 | 105 | 0 | — | — | — | — | — |
| PI | 546 | 0 | — | — | — | — | — |
| other (task dirs) | 684 | 17 | 9,942 / 8 | 14,733 | 2 | 2 | 0 / 0 |

These row totals count shared dumps once per store. Unique-dump totals are in §0.1. The per-store table, and the
table of every row with its own (1), (2), (3) and status, are in `eval/results/wjg/report_tables.md` §A and §B; the
same rows are in `rows.csv`. Per store, the stores whose rows hold a diverged instance:

| store | rows with records | with a diverged instance | (1) completed / open | (2) late records | rows replayed (≥ 1 launch) |
|---|---|---|---|---|---|
| evcand | 1,152 | 97 | 417,139 / 450 | 6,462,054 | 89 |
| evcand_smoke | 12 | 2 | 150 / 150 | 3,996 | 2 |
| full-2026-09-22 | 156 | 68 | 105,196 / 180 | 1,300,072 | 52 |
| t0-smoke, t0-smoke2 | 10 | 3 | 11,616 / 0 | 238,957 | 2 |
| t9-after (t9-before, t10-after, t12-after, t16-certain: same files) | 1,179 | 108 | 163,379 / 480 | 1,516,001 | 92 |
| t10-e3 | 8 | 4 | 192 / 8 | 637 | 2 |
| t12-eval-main / -t12 / -t12rb | 116 / 118 / 119 | 28 / 30 / 30 | 35,654 / 63,254 / 65,438 | 701,265 / 1,350,238 / 1,295,205 | 24 / 26 / 26 |
| t12-parity | 64 | 8 | 3,773 / 75 | 27,692 | 8 |
| t14-after | 1,116 | 68 | 71,833 / 300 | 240,285 | 66 |
| t16-certain-exits / t16-recorded-exits | 194 / 194 | 34 / 34 | 70,277 / 69,907 | 1,348,377 / 1,288,395 | 32 / 32 |
| t19-parity, -v2, -v3, -v4, t20-parity, t20-parity2, t4-parity | 126–130 each | 16 each | 7,483–7,564 each | 55,123–55,666 each | 16 each |
| t22-parity-b, t22c-parity, t5b-final-parity, t5b-parity, t5b-vs-parity | 62–65 each | 8 each | 3,753–3,792 each | 27,544–27,803 each | 8 each (7 for t5b-before-parity) |
| t22-parity-n8 | 7 | 4 | 1,369 / 75 | 21,769 | 4 |
| t4-ab-dump / t4-ab2-dump | 6 / 5 | 3 / 3 | 10,441 / 11,951 | 238,552 / 272,510 | 2 / 2 |
| t5b-final-timeout | 102 | 51 | 170,569 / 270 | 2,458,826 | 44 |
| t5b-timeout | 19 | 9 | 45,284 / 30 | 624,016 | 4 |
| t8-fresh | 10 | 2 | 600 / 0 | 18,600 | 2 |
| home: traces_keep, .prefix_36a93d08, .prefix_fe694b5, _evcand, _fpfix, _fpfix_tr | 25–352 | 43, 44, 49, 26, 14, 16 | 7,170–77,681 | 13,269–977,469 | 14–41 |
| other: x2-same-trace, t5a_stats, t5b_profile | 54, 25, 2 | 30, 13, 1 | 176,181; 9,750; 405 | 2,985,844; 14,096; 12,555 | 0 (no CFG) |

All other stores, including every X1 store (`final-2026-10*`, aggregates only) and every no-dump store (t4-nodump,
the t22/t22c runs), hold no syncwarp record with a partial mask: (1) = (2) = 0 and the merge is the identity.

## 3. Programs where (3) differs

- **L1 (the reported race pairs, X5's keys): none,** in either clock, in every dump replayed.
- **L2 — `P4-graph-connectivity-racy-small`, kernel `linkKernel`, 37 dumps (48 rows, both modes, 24 stores).**
  - Appears with the merge: `global:0x160-0x400:WAR:DR` at **warp** distance, 435 instances (vector-clock dump) and
    439 (scalar-clock dump) in evcand's `kernel_1`, 11 / 16 of them `a2_uncertain`.
  - The same pc pair, kind and class is reported as recorded at **block** distance (5,520 instances, unchanged by the
    merge).
  - So the per-record join hides warp-distance conflict instances of a pair the detector reports anyway. The
    program's report ids and the pair's widest distance (the `observed_distance` R1 judges) are unchanged.
- **L3 (counts only):**
  - oracle: P4-graph-connectivity 98 dumps, P1 `CC_CUDA_V_Data_Pull_Determ_IntType_Persist*` 33,
    P1 `…Pull_NonDeterm_IntType…` 10, P4-graph-coloring 2;
  - barrier-only pass: P1 `…Pull_Determ_IntType_Persist*` 108, P4-graph-connectivity 98,
    P1 `…Pull_NonDeterm_IntType…` 43.
  - Pairs are the same in all of them; only instance counts change.

## 4. Missing, with the reason

Unique dumps with a partial syncwarp record: 8,720.

| what | dumps | reason |
|---|---|---|
| census not run | 96 | the census jobs of the large (≥ 500 MB) and the last small dumps were stopped by the BeeGFS outages (jobs 315827, 315829 cancelled, 315933 failed its preflight). By store: t5b-final-timeout 34, evcand 16, full-2026-09-22 14, t4-ab-dump 8, t4-ab2-dump 5, t12-eval-t12rb 5, other ≤ 3 each |
| no CFG to replay against | 271 | the dot listing was empty. 261 are in task directories, which keep no `dots/` (other:x2-same-trace 212, other:t5b_profile 27, other:t5a_stats 22). 10 are in stores (t5b-timeout 7, t12-eval-main 1, t4-ab2-dump 1, t5b-final-timeout 1) and were censused around the 23:11 outage; whether their dots exist is unverified |
| census failed otherwise | 2 | — |
| oracle replay: MemoryError | 811 | over the 10 GB child cap: P1 545, P3 241, P4 25. Most fail within a minute, many on dumps under 10 MB (the oracle's O(threads²) clocks, as T9_RESCORE §2 found for P1 1296-node programs). 70 were retried at 40 GB (66 finished) before the outage stopped the retries. The barrier-only pass finished for these dumps |
| oracle replay: strict trace-validity refusal | 386 | P4 (graph-coloring and the like): `AlignmentError: TV-barrier-completion-order … issues a post-barrier write`. The oracle refuses by default; HbClock records the violation and continues. Pre-existing on these dumps (T9_RESCORE §4) |
| oracle replay: not run / timeout / read error | 10 / 3 / 3 | 10 P4 matrix-multiplication-large dumps that had the census and barrier-only pass only (oracle shards cancelled or not reached). The 4 h cap was hit by 2 matrix-multiplication-large dumps and P4-uts-norace-large. 3 P3 replays failed reading BeeGFS in the outage |
| barrier-only pass | 8 | 7 P4 matrix-multiplication-large dumps: the child died of SIGSEGV (orjson out of memory under the cap; since fixed: stdlib json above 2 GB), and their redo failed its preflight on c48. 1 read error in the outage |
| scan | 113 files | deleted between the 10-18 listing and the scan (T22's `work/dependency_*` directories) |

## 5. Validation

- **Scan vs parsed records** (proved-in-effect, 8,622 dumps re-read in full): record count, full and partial syncwarp
  counts equal in all, and records in seq order in the file in all.
- **Streamed vs verbatim census** (proved-in-effect, 8,607 dumps under 2 GB): `streamcheck` runs X5's
  `partial_instances` on the parsed document and the streamed version on the bytes. Counters, extras, the merged
  hb_events and the rest of the document were equal in all 8,607. Only the 15 dumps of 2 GB and more use the stream
  alone.
- **Barrier-only clock, two implementations** (proved-in-effect): the oracle's `races_sync_only` and `barrier_only_pairs`
  have equal pair sets and counts in every dump where both ran, on both traces.
- **X5's 60 recordings** (`x5_check.json`): completed and open instance counts equal in 60 of 60, and late-record
  counts in 52. The 8 that differ are X5's 1296-node rows, where `x5b_partial.py` removed `space == "global"`
  records before its census (its `shared_only` path): e.g. X5 counts 6,074 and this census 24,006, with 9,570
  instances in both.
- **Where the partial records are** (`report_tables.md` §A3): every pc with partial records holds a `WARPSYNC` in
  the dot (11,703 (dump, pc) pairs).
  - 2,343 sit in CUDA's out-of-line `$__internal_0_$__cuda_sm70_warpsync` and 2 in `…shflsync_idx_p`.
  - 9,409 are inline `WARPSYNC` instructions in a kernel body (51 pcs have both).
  - The other opcodes in that table are other clusters' instructions at the same offset.

## 6. The single-store examples behind §0.3

- **evcand `P4-matrix-multiplication-norace-large` (scalar-clock):**
  - 131 completed instances and 10,583 late-lane records, at the inline `WARPSYNC 0xffffffff` (pc 0x4a0) of
    `matMultKernel`;
  - barrier-only pass: 6 sync-only pairs both ways, counts equal;
  - its oracle replay ran past 4 h.
- Across all 17 matrix-multiplication-large dumps: the census finished; the barrier-only pass finished for 4
  (7 SIGSEGV, 6 stopped by the outage); no oracle replay finished.
- **evcand `P4-graph-connectivity-racy-small`:** §3.

## 7. What X3's soundness statement can and cannot claim

Facts only.
- HbClock and the oracle join a diverged `WARPSYNC` at each group's record.
- The proof takes a syncwarp record as a complete instance, and its trusted base (A3) states a release condition for
  barriers only, so the soundness argument does not cover a warp that reaches a `WARPSYNC` diverged.
- Such arrivals are not rare in the kept stores: 8,720 dumps, in P1, P3 and P4, with 1.47 M completed diverged
  instances and 20.2 M memory records of lanes that had not yet arrived. They occur both at CUDA's out-of-line
  helper and at inline `WARPSYNC`s.
- Where the replay finished, merging each instance at its true completion changes no reported race pair:
  - the vector clock in 7,136 dumps;
  - the barrier-only clock in 8,341.
- It does add hidden warp-distance conflict instances of one already-reported pair (P4-graph-connectivity, 37 dumps),
  and it changes instance counts in 143 / 249 dumps.
- X5's counterfactual shows the per-record join can hide a real race (10 WAW pairs once one `__syncwarp()` is removed).

So X3 **can** state:
- that on the kept stores' recordings, for every dump replayed, no reported pair (DR or SC, either clock) depends on
  the per-record join;
- that the scalar-clock mode's clock is unaffected in every dump it was run on.

X3 **cannot** claim:
- that the model or its soundness theorem covers diverged `WARPSYNC`s;
- the absence of a dependency for the 1,213 dumps whose vector-clock replay did not finish (mostly memory: P1 1296-node
  ECL-CC), for the 96 not censused, or for the 271 without a CFG;
- anything about X1's own recording. Its stores hold aggregates only (no syncwarp records), and how many of X1's
  (program, mode) keys have a recorded store with the same binary was not computed (§8). The PI suite (4,130 of
  X1's 4,725 programs) appears in the stores only through 546 record rows, none of which has a partial syncwarp
  record.

## 8. Not run, and how to resume

**Not run** (BeeGFS failed at 23:11 and was still failing at 23:53):
- the oracle replay of 811 dumps at a larger cap;
- the lenient replay of the 386 strict refusals;
- the census of 96 dumps and the barrier-only pass of the 13 matrix-multiplication-large dumps without one;
- the P4 matrix-multiplication-large oracle replays;
- `wjg_coverage.py` (X1 coverage and WARPSYNC counts in X1's dots).

**Commands** (`REDO=1` skips dumps already finished, or that would fail the same way at that budget):
```
cd /home/fzheng4/wt-warpsync-join-gap; S=eval/baselines/setup; X=--exclude=c23,c46
REDO=1 MAXMB=2000 SLOTS=16 MEMGB=10 TIMEOUT=7200 CHECK=1 TAG=rest sbatch $X $S/p_wjg_census.sh              # the 96
REDO=1 LENIENT=1 MAXMB=2000 SLOTS=16 MEMGB=10 TIMEOUT=7200 TAG=lenient sbatch $X $S/p_wjg_census.sh         # TV refusals
for i in 0 1; do REDO=1 MAXMB=2000 SLOTS=4 MEMGB=40 TIMEOUT=7200 SHARD=$i/2 TAG=r40b_$i sbatch $X $S/p_wjg_census.sh; done
REDO=1 MAXMB=2000 SLOTS=1 MEMGB=auto TIMEOUT=14400 TAG=rfull sbatch $X $S/p_wjg_census.sh                   # after r40b
REDO=1 NOORACLE=1 STAGE=1 MINMB=2000 SLOTS=1 MEMGB=auto TIMEOUT=14400 TAG=p4b_redo sbatch $X $S/p_wjg_census.sh
COVERAGE=1 sbatch $X $S/p_wjg_tables.sh
```

## 9. Commands, jobs, revision, hardware

| jobs | what | outcome |
|---|---|---|
| 314782, smoke2, smoke3 | smoke: X5's P3 program; streamed census check | reproduces X5; streamcheck 22/22 |
| 314783 | `wjg_scan.py list` | 604,357 kernel JSONs |
| 314821–314826 | scan, first pass | killed by the 10-18 shutdown at 457 files |
| 315315–315324 | census and scan resubmitted 10-20 13:13 | failed: BeeGFS not mounted |
| 315518–315523 | scan, rest | 497,823 files (113 deleted) |
| 315868–315870 | key-less rescan (`STEP=fix`) | 397,788 files; t14-after's 5,746 compact dumps hold records, none of the others |
| 315514–315517 | P4 census | failed: orjson buffer under RLIMIT_AS (fixed: streamed census) |
| 315615–315618 | P4 census, streamed, staged | 9 dumps through 315615/315616; 315617/315618 cancelled |
| 315913, 315914 | P4 census + barrier-only pass | 9 + 8 dumps; 315914's 8 bpass SIGSEGV |
| 315825–315827 | census < 500 MB, 3 shards | 8,606 dumps (315827 cancelled in the outage) |
| 315828, 315829 | census 500–2,000 MB | 1 dump (oracle timeout), then the outage |
| 315871 | census t14-after (compact) | 373 dumps |
| 315931, 315932 | oracle retry at 40 GB | 70 dumps, stopped by the 23:11 outage |
| 315933 | barrier-only redo | failed preflight: c48 lost /mnt/beegfs |
| 315992 | `wjg_tables.py` | the tables of this report |

- **Revision:** `cuVein` afccba7 plus this branch's scripts. Python `/home/fzheng4/AccelProf/.env/bin/python` 3.14,
  with `CUVEIN_HOME` set to this worktree. CPU nodes of partition `normal`.
- **Excluded nodes:** c23 and c46 (no /home/fzheng4 after the 10-18 restart) from every job of 10-20. c48 lost BeeGFS
  at 23:28 (315933).
- **Data:** `eval/results/wjg/`. `files.jsonl` (235 MB) is gitignored; `STEP=list` rebuilds it.
  `scan_fix_315868.jsonl` (123 MB) is committed gzipped.
- **Logs:** `eval/x_logs/wjg-*.log` (force-added).

**Unverified:**
- the oracle's answer for the 1,213 dumps of §4;
- whether the L2 instances of §3 change any verdict field other than counts (the verdict layer was not run on the
  merged traces; its inputs from the clocks differ only in those counts and the added warp-distance aggregate);
- X1 coverage.

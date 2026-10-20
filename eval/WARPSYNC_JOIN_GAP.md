# WARPSYNC join gap: diverged-warp syncwarp records across the kept stores — interim, measurement blocked

Branch `eval/warpsync-join-gap`, worktree `/home/fzheng4/wt-warpsync-join-gap`, cut from `cuVein` afccba7.
Left unmerged. Measurement only: nothing in `sanalyzer/`, `nv-compute/` or `python/` changed. No GPU; every job
ran in partition `normal`. Legend as in CLAUDE.md A4: **proved-in-effect** = checked over every item stated;
**tested** = a specific result asserted; **unverified** = said so.

**Status: incomplete.** The brief's per-(program, mode, store) numbers do not exist yet for the corpus.
- The 2026-10-18 18:00 cluster shutdown killed the byte scan (jobs 314821–314826) after 457 of 497,823 files.
- Since the restart, BeeGFS is not mounted on the compute nodes, so every store is unreadable: jobs 315315–315324
  (2026-10-20) failed within seconds on c12, c13, c18, c25, c39, c61, c63, c64, c66 (`/mnt/beegfs` is an empty
  local directory; an `srun` on c61 shows no beegfs mount) and on c58 (`OSError: [Errno 121] Remote I/O error`).
- §5 lists what remains, with the commands that resume it.

## 0. Findings so far

1. **The corpus-wide effect is still unmeasured.** No census or replay ran on a corpus dump.
2. **The gap is not limited to ECL-CC's out-of-line warpsync helper.** The scan finished the 457 largest files
   (3.454 TB of 9.17 TB; every one holds hb_events records).
   - Exactly 17 of them contain syncwarp records at all, and all 17 contain partial ones (active mask not covering
     the sync mask).
   - All 17 are `P4-matrix-multiplication-{norace,racy}-large`, in 8 stores and both modes, with 226–326 partial
     and 38,237–38,287 full syncwarp records per dump.
   - Every partial record is at pc 0x4a0: an inline `WARPSYNC 0xffffffff` in `mm_kernel`, just before
     `BAR.SYNC.DEFER_BLOCKING` at 0x4d0 (the kernel's lock is an `ATOMG.E.CAS` loop at 0x540). The opcode is read
     from t4-ab-dump's dot; for the other 7 stores, that their dot is the same is unverified.
   - (1), (2) and (3) for these dumps are **not measured**: their census jobs (315315–315318) failed on BeeGFS.
3. **The method reproduces X5 exactly** on X5's own program (tested).
   - Program: `P3-…Pull_Determ_IntType_NonPersist_Atomic_Warp…-100n`, t16-certain, both modes.
   - Result: 531 completed instances, 812 memory records from lanes not yet arrived (281 shared / 531 global),
     0 race pairs appear or disappear, the same as X5_BYTE_PAIRS Appendix C.
   - The scan's counts equal the parsed counts in 22/22 dumps; the barrier-only pass equals the oracle's
     sync-only set in 11/11 launches; the partial pc 0x10a0 is `WARPSYNC` in
     `$__internal_0_$__cuda_sm70_warpsync`.
4. **A store fact:** t16-certain's P3 ECL-CC program directories are symlinks into `full-2026-09-22`, so X5's
   "t16-certain" records are full-2026-09-22's recordings. The scan deduplicates by real path.

## 1. Scope, definitions, method

**The gap** (X5_BYTE_PAIRS §4, b5e10b4).
- A warp that reaches a `WARPSYNC` diverged executes it in groups. The trace holds one `syncwarp` record per group,
  each with the full `sync_mask` and a partial `active_mask`.
- HbClock (`sanalyzer/src/tools/pc_dependency_analysis.cpp:1661-1668`) and the oracle (`python/hb_oracle.py:672-677`)
  join every `sync_mask` lane at each record. The first group's record therefore orders a late lane's
  pre-arrival accesses as if that lane had arrived.
- The proof models a syncwarp record as a complete instance (`design/proof/hb_proof.tex:145`). Its A3 (`:206-208`)
  states the release condition for barriers only.
- These lines are unchanged on this branch: `git diff --stat 4094187 afccba7 -- sanalyzer nv-compute python design/proof`
  is empty.

**Stores.** CLAUDE.md A2 names the kept traces: every directory under `/mnt/beegfs/fzheng4/cuvein_traces/` and the
home copies `eval/baselines/traces_keep*` (since T-H, symlinks into `/mnt/beegfs/fzheng4/home_archive/eval_baselines/`).
- All were listed. The other top-level directories of `/mnt/beegfs/fzheng4/` (task working directories) were
  listed too, for separate reporting as `other:`.
- A **row** is one (store, run directory): `<program>/<mode>` in the standard layout, `<program>/<mode>-partial-repN`
  for a timed-out run's kept partial dump, else the kernel JSON's directory.
- Files reached through symlinks are read once (deduplicated by real path) and counted in every row that lists them.

**Definitions** (as briefed; X5's rule for instances):
1. **Diverged syncwarp instances**: per (block, warp, pc), consecutive syncwarp records starting with one whose active
   mask does not cover the sync mask, until the union of active masks covers it. *Completed* means it reached the
   sync mask; *open at end* means it never did.
2. **Memory records of lanes not yet arrived**: read / write / atomic records of the warp, issued while an instance
   is open, by a lane inside the sync mask but outside the union so far. Each record is counted once. X5's own
   count, once per open instance, is kept beside it.
3. **Race pairs, per-record join vs merged**:
   - The merge is X5's `partial_instances`, copied verbatim from `x5b_partial.py` (b5e10b4) into `wjg_census.py`:
     each completed instance becomes one record at its completion (active mask = the union; earlier records
     dropped); open instances stay as recorded.
   - `hb_oracle.analyze` (the specification HbClock matches bit for bit) and `sync_dominance.barrier_only_pairs`
     (the scalar-clock mode's offline pass) run on the dump as recorded and on the merged dump, with no
     `CUVEIN_*` overrides.
   - Compared per launch at three levels. **L1** is X5's keys: `space:a_pc-b_pc:kind:class` for races, `a_pc-b_pc`
     for the sync-only set. **L2** adds distance and async side. **L3** adds counts and `a2_uncertain`.
   - A launch without a completed instance has merged records equal to the recorded ones, so its pairs are equal
     by construction.

**Pipeline** (scripts in `eval/baselines/setup/`):
- `wjg_scan.py list`, then `wjg_scan.py scan`: a byte scan per real file, in chunks cut at record starts. Jobs share
  one queue through O_EXCL claim files.
- `wjg_census.py run`: per file with a partial record — census, merged dump, two oracle replays and two
  barrier-only passes. Each child runs under `RLIMIT_AS` and a timeout.
- `wjg_tables.py`: rows, moves and the X5 cross-check.
- `wjg_coverage.py`: X1's (program, mode) keys against rows with records (same dot md5), plus each X1 program's
  WARPSYNC instructions and warpsync-helper CALLs.

## 2. Measured

**Listing** (job 314783, 3 min): 604,357 kernel JSONs, 497,823 unique real files, 9.17 TB. The listing
`eval/results/wjg/files.jsonl` (235 MB) is gitignored; `STEP=list sbatch eval/baselines/setup/p_wjg_scan.sh` rebuilds it.

**Scan** (jobs 314821–314826, largest files first, killed by the shutdown): 457 files and 3.454 TB done
(`eval/results/wjg/scan_3148*.jsonl`); all 457 hold records; 17 hold syncwarp records, all partial-bearing:

| store | program | mode | records | syncwarp full / partial | partial pcs | GB |
|---|---|---|---|---|---|---|
| evcand | matrix-multiplication-norace-large | scalar-clock | 7,632,539 | 38,269 / 262 | 0x4a0 | 10.4 |
| evcand | matrix-multiplication-racy-large | scalar-clock | 7,639,156 | 38,287 / 226 | 0x4a0 | 10.4 |
| full-2026-09-22 | matrix-multiplication-norace-large | scalar-clock | 7,633,669 | 38,253 / 294 | 0x4a0 | 10.4 |
| full-2026-09-22 | matrix-multiplication-racy-large | scalar-clock | 7,635,791 | 38,251 / 298 | 0x4a0 | 10.4 |
| t12-eval-main | matrix-multiplication-norace-large | scalar-clock | 7,668,674 | 38,278 / 244 | 0x4a0 | 10.5 |
| t12-eval-main | matrix-multiplication-racy-large | scalar-clock | 7,675,085 | 38,278 / 244 | 0x4a0 | 10.5 |
| t12-eval-t12 | matrix-multiplication-norace-large | scalar-clock | 7,666,513 | 38,280 / 240 | 0x4a0 | 10.5 |
| t12-eval-t12 | matrix-multiplication-racy-large | scalar-clock | 7,673,442 | 38,279 / 242 | 0x4a0 | 10.5 |
| t12-eval-t12rb | matrix-multiplication-norace-large | scalar-clock | 7,668,865 | 38,280 / 240 | 0x4a0 | 10.5 |
| t12-eval-t12rb | matrix-multiplication-racy-large | scalar-clock | 7,669,212 | 38,276 / 248 | 0x4a0 | 10.5 |
| t4-ab-dump | matrix-multiplication-norace-large | scalar-clock | 7,675,589 | 38,244 / 312 | 0x4a0 | 10.5 |
| t4-ab-dump | matrix-multiplication-norace-large | vector-clock | 7,671,576 | 38,253 / 294 | 0x4a0 | 13.0 |
| t4-ab2-dump | matrix-multiplication-norace-large | scalar-clock | 7,671,843 | 38,237 / 326 | 0x4a0 | 10.5 |
| t5b-final-timeout | matrix-multiplication-norace-large | scalar-clock | 7,677,117 | 38,260 / 280 | 0x4a0 | 10.5 |
| t5b-final-timeout | matrix-multiplication-norace-large | vector-clock | 7,669,825 | 38,264 / 272 | 0x4a0 | 13.0 |
| t5b-final-timeout | matrix-multiplication-racy-large | scalar-clock | 7,673,976 | 38,287 / 226 | 0x4a0 | 10.5 |
| t5b-final-timeout | matrix-multiplication-racy-large | vector-clock | 7,675,145 | 38,253 / 294 | 0x4a0 | 13.0 |

The other 440 scanned files (P7/P9 partial dumps, P6 asyncmemcpy, the parity stores' large kernels, …) have no
syncwarp record, so (1) = (2) = 0 there and their merged records equal the recorded ones.

**Smoke** (314782, then the final scripts as `smoke2`, `eval/results/wjg/smoke*/`): §0 item 3.

## 3. Programs where (3) differs

None known. None of the 17 P4 dumps was replayed (§0 item 2), and no other row reached the census.

## 4. What X3's soundness statement can and cannot claim

Facts only. HbClock and the oracle join a diverged `WARPSYNC` at each group's record. The proof takes a syncwarp
record as a complete instance, and its trusted base (A3) states a release condition for barriers only. So the
soundness argument does not cover a warp that reaches a `WARPSYNC` diverged.

Diverged arrivals are in the stores:
- ECL-CC: 24 of X5's 60 recordings, at the out-of-line helper.
- P4 matrix-multiplication-large: 17 dumps here, in 8 stores and both modes, at an inline `WARPSYNC` before a
  barrier in a lock kernel.

Whether they change a reported pair:
- Measured only by X5: 0 pairs move in its 60 recordings.
- Shown by X5's counterfactual: the join can hide real races (10 WAW pairs once the first `__syncwarp()` is removed).
- Not measured for the P4 dumps.
- Not measured for the remaining 99.9 % of files (by count): 497,366 unscanned, including every ECL-CC row.
- Not measurable from X1's own dumps, which keep aggregates only (no syncwarp counts).

So, on today's numbers, X3 **cannot** claim corpus-wide that no reported verdict depends on the per-record join. It
**can** state:
- the deviation (a diverged syncwarp is joined per record; the model and A3 do not cover it);
- X5's 60-recording result and counterfactual;
- that diverged instances occur in P4 matrix-multiplication-large and in ECL-CC.

Any soundness sentence would have to exclude, or assume away, kernels whose warps reach a `WARPSYNC` diverged.

## 5. Not run, and how to resume

**Not run:**
- the scan of 497,366 files (5.7 TB);
- the census and replays of every file with partial records (at least the 17 above);
- `wjg_tables.py` (the per-row table, the moves list, the X5 cross-check over all 60 recordings);
- `wjg_coverage.py` (X1 coverage).

**When BeeGFS is mounted again:**
```
cd /home/fzheng4/wt-warpsync-join-gap
for i in 0 1 2 3; do MINMB=2000 SLOTS=1 MEMGB=auto TIMEOUT=14400 STAGE=1 SHARD=$i/4 TAG=big$i \
  sbatch eval/baselines/setup/p_wjg_census.sh; done            # the large P4 dumps, staged to local disk
for k in 1 2 3 4 5 6; do STEP=scan CLAIMS=/mnt/beegfs/fzheng4/wjg_claims3 \
  sbatch eval/baselines/setup/p_wjg_scan.sh; done              # skips the 457 files in scan_*.jsonl
MAXMB=2000 SLOTS=16 MEMGB=10 TAG=small sbatch eval/baselines/setup/p_wjg_census.sh   # after the scan
.env/bin/python eval/baselines/setup/wjg_tables.py --dir eval/results/wjg              # in a normal job
.env/bin/python eval/baselines/setup/wjg_coverage.py --dir eval/results/wjg            # in a normal job
```
The scan reads at ~400–570 MB/s in total on this cluster (BeeGFS), so the rest takes about 3 h on 6 nodes. A
census copy beside a running scan got 3 MB/s, so stage the large dumps first, as above.

## 6. Commands, jobs, revision, hardware

| job | what | outcome |
|---|---|---|
| 314777, 314778, 314779 | store sizes, layout probes (`srun`) | — |
| 314782 | smoke: one P3 program, scan + census | reproduces X5 (§0.3) |
| 314783 | `wjg_scan.py list` | 604,357 kernel JSONs |
| 314788–314791 | first scan, static shards | cancelled: replaced by the shared queue |
| 314821–314826 | scan, shared queue, 16 processes per node | killed by the 10-18 shutdown at 457 files |
| 314891, 314920 | census of the large dumps | cancelled: 314891 to add the local copy; 314920 read BeeGFS at 3 MB/s beside the scan |
| 315315–315318 | census of the 17 P4 dumps, staged, 4 shards | failed: BeeGFS not mounted |
| 315319–315324 | scan resume | failed: BeeGFS not mounted (c58: Remote I/O error) |

- Revision: `cuVein` afccba7 plus this branch's scripts. Python `/home/fzheng4/AccelProf/.env/bin/python` 3.14,
  with `CUVEIN_HOME` set to this worktree.
- Nodes: partition `normal` (c8, c9, c12, c13, c40, c47 for the scan).
- Logs: `eval/x_logs/wjg-*.log` (force-added).

**Unverified:**
- that the 7 other stores' P4 dots have the same SASS at 0x4a0;
- the effect of the merge on any P4 dump;
- whether the Python oracle can replay a 7.6 M-record P4 dump within a normal node's memory (unknown;
  `eval/T9_RESCORE.md` lists 4 P1 1296-node programs it could not).

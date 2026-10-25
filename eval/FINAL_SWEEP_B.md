# X1b: the final recording, repeated on the T22 cont. + T23 + T24 runtime

Branch `eval/final-sweep-b` (from `cuVein` f551ca0, the install commit of the runtime built from
e0e6431 = T24 merged on T22 cont. + T23), worktree `/home/fzheng4/wt-x1b`, left unmerged for Jeffery.
`eval/FINAL_SWEEP.md` (X1) stays as the record of the first run; this file repeats its sections for
the second. Recorded 2026-10-22 02:12 – 2026-10-24 21:56:
dry run 10-22 02:12; first pass 10-22 03:23 – 19:02 (PI pass 15:00 – 19:57); 5,400 s pass
10-22 22:01 – 10-23 09:57; 84,600 s pass 10-22 16:53 – 10-24 21:56. The report was first written while
the last task, P9-expdist-cuda vector-clock (319350_1, c64, 10-23 22:26 – 10-24 21:56), was still
running (§1 (d)). Post-processing ran 10-24 15:41–15:50 (job 320157) and the store checks 15:55–16:03.
After 319350_1 ended, post-processing ran again 21:58–22:06 (job 320365, c45) and its row was folded in.

Legend as in CLAUDE.md A4: **proved-in-effect** = an invariant checked over the stated stores;
**tested** = a specific result asserted; **unverified** = said so.

## 0. Runtime and hardware

| component | sha256[:16] | source |
|---|---|---|
| `build/sanalyzer/lib/libsanalyzer.so` (what the collector's RPATH loads) | `5a20fd14ab6c6806` | install commit f551ca0 (built from e0e6431) |
| `lib/libcompute_sanitizer.so` (collector) | `b746b4dd23e90f46` | f551ca0 (relinked against the new library) |
| `nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin` | `a2d7368bc1c61986` | unchanged since X1 (d38d057) |
| `gpu_patch_pc_dependency_late.fatbin` (installed, not loaded) | `e96343121c74ca0a` | unchanged since X1 |
| verdict layer `python/` of the runtime checkout | `cuVein` f551ca0 | the runtime checkout's HEAD in every `meta.json` (`runtime_head` f551ca00947e) |
| harness (`parallel.py`, `blib.py`, `run_cuvein.py`, `setup/p_final*.sh`) | `eval/final-sweep-b` 0d3bc29 (dry run, 317637_0/_1); d151ceb (318511; 25 PI shards); 3be0591 (39 PI shards; 10 tasks of 84,600 s batch 1); 1468f96 (the 5,400 s pass; 319061_6, 319062_1 and 84,600 s batch 2). 1468f96 adds only id files. | `dirty=0` in every shard log. `git diff 0d3bc29 1468f96` over `parallel.py`, `blib.py`, `run_cuvein.py`, `p_final.sh` and `p_final_long.sh` is empty. Over `p_final_24h.sh` it is 3be0591's partition / exclude / time / `CAP` change (§1, deviation (b)), committed before the first 84,600 s task started. |

**Precondition (the brief's stop condition).** f551ca0's message names the hashes: "after:
libsanalyzer 5a20fd14ab6c6806 collector b746b4dd23e90f46 fatbin a2d7368bc1c61986 late
e96343121c74ca0a". The sha256 of the installed files (login node, 10-24 15:35) equals them, and so does
the runtime block of every `meta.json` (§6 (a)). The stop condition does not apply.
`git status --porcelain` in the runtime checkout lists only `?? corpora` (the untracked symlink X1
reported). `cuVein` is still at f551ca0 at writing.

**Harness against X1** (0d3bc29):
- `BASELINE_HB_SHARDS=N` sets `YOSEMITE_HB_SHARDS=N` for scalar-clock runs only. `blib.base_env` drops an inherited `YOSEMITE_HB_SHARDS`, so vector-clock never sees the knob.
- `meta.json` records `hb_shards` per mode and `nproc`.
- A node probe exits 2 before any row is written when `/home` or BeeGFS is unreadable.
- c23 and c46 are excluded (no `/home`).
- The result and store names are X1b's.
- `final_sanity.py` has a `FINAL_B` branch: the f551ca0 hashes, c23/c46, and `hb_shards`.

**Nodes** (partition `rtx4060ti16g` for every pass), from the shard logs' headers. All are RTX 4060 Ti, sm_89.
A main shard holds 12–13 programs, a PI shard 64–65, a 5,400 s or 84,600 s task one (id, mode).
Each count is the node that wrote the shard's rows (a requeued task counts where it re-ran, §5).

| node | CPU (AMD EPYC) | RAM visible | driver | main shards | PI shards | VC 5,400 s | SC 5,400 s | VC 84,600 s | SC 84,600 s | dry run |
|---|---|---|---|---|---|---|---|---|---|---|
| c0 | 9115 | 125 GB | 615.71.10 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| c1 | 9115 | 125 GB | 580.82.07 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| c24 | 7302P | 125 GB | 580.82.07 | 0 | 12 | 1 | 0 | 1 | 3 | 0 |
| c40 | 7302P | 125 GB | 580.82.07 | 3 | 11 | 2 | 2 | 0 | 0 | 0 |
| c41 | 7302P | 125 GB | 580.82.07 | 4 | 1 | 0 | 0 | 0 | 0 | 0 |
| c42 | 7302P | 125 GB | 580.82.07 | 1 | 6 | 1 | 0 | 1 | 0 | 0 |
| c43 | 7302P | 125 GB | 580.82.07 | 5 | 0 | 2 | 0 | 0 | 0 | 0 |
| c44 | 7302P | 125 GB | 580.82.07 | 4 | 1 | 0 | 0 | 1 | 0 | 0 |
| c56 | 9115 | 125 GB | 580.105.08 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| c61 | 8124P | 188 GB | 580.82.07 | 1 | 0 | 0 | 0 | 2 | 0 | 0 |
| c62 | 8124P | 188 GB | 580.82.07 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| c63 | 8124P | 188 GB | 580.82.07 | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| c64 | 8124P | 188 GB | 580.95.05 | 6 | 0 | 0 | 0 | 4 | 0 | 0 |
| c73 | 7302P | 125 GB | 580.82.07 | 4 | 3 | 0 | 0 | 0 | 1 | 0 |
| c74 | 7302P | 125 GB | 580.82.07 | 7 | 5 | 0 | 0 | 0 | 2 | 0 |
| c75 | 7302P | 125 GB | 580.82.07 | 2 | 4 | 0 | 0 | 1 | 0 | 0 |
| c76 | 7302P | 125 GB | 580.82.07 | 2 | 4 | 3 | 0 | 0 | 0 | 0 |
| c78 | 7302P | 125 GB | 580.82.07 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| c79 | 7302P | 125 GB | 615.71.09 | 1 | 5 | 0 | 0 | 0 | 0 | 0 |
| **19 nodes** | | | | 48 | 64 | 9 | 2 | 11 | 8 | 1 |

The partition mixes three host CPUs (EPYC 7302P Zen 2, 9115 Zen 5, 8124P Zen 4), two RAM sizes (125 /
188 GB visible; `mem_total_gb` 134.6–135.0 / 202.3–202.4 in `meta.json`) and five drivers
(580.82.07; 580.95.05 on c64; 580.105.08 on c56; 615.71.09 on c79; 615.71.10 on c0). X1 ran on 14 nodes with
three drivers. c39–c44 (EPYC 7302P, 125 GB) are `rtx4060ti16g` hosts now and were not among X1's
nodes. The 188 GB hosts X1b used are c61–c64.

As in X1, tool and native walls of a row come from one node, so ratios are per node and cross-row wall
comparisons are not. Five nodes failed the node probe at times (c77, c43, c61, c62, c76: BeeGFS not
readable, §5). None of those failures wrote a row.

## 1. Configuration

The same for every row of a pass (`setup/p_final.sh`; `p_final_long.sh` for the 5,400 s pass,
`p_final_24h.sh` for the 84,600 s pass):

| knob | value | note |
|---|---|---|
| `BASELINE_HB_DUMP` | 0 | no `hb_events`; every `meta.json` has `hb_dump: false` (§6 a) |
| `YOSEMITE_HB_STATS` | 1 | `hb_stats` in every kernel JSON |
| `BASELINE_HB_SHARDS` → `YOSEMITE_HB_SHARDS` | **16, scalar-clock runs only** | The brief's one difference. N = 16 is what `SHARDED_SYNC.md` II.10 (step C) chose for these host types: the core count of its hosts (EPYC 8124P and 7302P), and the fastest of 8 and 16 on all four step-C programs. Every `meta.json` states `hb_shards = {"vector-clock": 0, "scalar-clock": 16}`. Every scalar-clock kernel JSON carries the library's own `hb_stats.hb_clock.sharded.shards = 16`; no vector-clock kernel JSON has a `sharded` block (§6 (a)). |
| modes | both, in one job per shard | `collect_one` wipes `<store>/<id>`; vector-clock first, then scalar-clock |
| `--reps` | 3 (84,600 s pass: 1) | as X1 |
| `--confirm` | on | detail JSONs → `eval/baselines/confirm_final-b{,-long,-long-sc,-24h-vc,-24h-sc}/` in the runtime checkout (untracked) |
| store | `/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11` (+ `-long`, `-long-sc`, `-24h-vc`, `-24h-sc`) | `--keep-all` |
| tool timeout | `--timeout-floor = --timeout-cap = 1200` (5,400 s pass: 5400; 84,600 s pass: 84600) | X1's interpretation (a) |
| offline analysis cap | `--analysis-timeout 14400` | no row reached it (§3) |
| detector knobs | none | `p_final.sh` unsets every inherited `CUVEIN_*` / `YOSEMITE_*` variable |
| partition | `rtx4060ti16g` for every pass | X1's 24 h pass ran on `max` |
| results | `eval/results/final-b/` (`--tag final-b`, `final-b-pi`), `final-b-long/`, `final-b-long-sc/`, `final-b-24h-vc/`, `final-b-24h-sc/` | merged into `eval/results/final-b/merged/baselines-cuvein.csv` (§2). X1's `eval/results/baselines-cuvein.csv`, X1's result directories and X1's tables are untouched (§7). |

**X1's interpretations (a)–(j), as they apply here**

- (a), (b): unchanged. The timeout floor equals the cap. `native_wall_s` is the median of the 3 native reps.
- (c) *Long-pass selection*: an id goes to a long pass when at least one of its reps in that mode is TIMEOUT in the first pass.
  - Vector-clock: 20 ids. These are X1's 19 plus P4-matrix-multiplication-norace-large, whose reps were TIMEOUT / CLEAN 1,190.48 s / TIMEOUT.
  - Scalar-clock: 10 ids. X1 had 18; the other 8 finished at 1,200 s with N = 16.
  - `merge --override` replaces all rows of an overridden (id, mode).
- (d) *Own stores per pass*: as X1.
  - Hosts: the 5,400 s ids whose first-pass peak was at most 10 GB ran on any good host; the others ran on `p_final_long.sh`'s default host list.
  - **That default list was written for X1's partition and does not exclude c39–c44, which are now 125 GB `rtx4060ti16g` hosts.** Both "big-memory" 5,400 s keys (lavaMD and particlefilter, vector-clock, 319347) ran on c43 (125 GB). See §4.
- (e) *Batches*: the 84,600 s pass ran in two batches.
  - Batch 1, 10-22 16:50: the X1 24 h keys that were TIMEOUT at 1,200 s by then (319061: 8 vector-clock; 319062: 4 scalar-clock).
  - Batch 2, 10-22 21:49, with the 5,400 s pass (Jeffery's approval): 319346–319352.
- (f) *Scalar-clock long passes*: as X1, the scalar-clock TIMEOUT keys get the same long passes as the vector-clock ones.
- (g) *Merge is cuVein-only*: the other tools' sha256 is checked (§7).
- (h) *PI*: its 64 shards ran on 125 GB hosts only (c0, c1, c24, c40–c42, c44, c73–c76, c79).
- (i) *The 84,600 s pass, one rep, X1's merge rule*: a long-pass row replaces all rows of its (id, mode) when it reached RACE, CLEAN or TIMEOUT. An ERROR leaves the earlier rows standing and is listed in `eval/results/final-b-24h-kept-<m>/dropped.txt`. That is one key again: P9-atomicCAS vector-clock. A RACE seen in a run killed by OOM is a RACE (the harness rule; P7-particlefilter scalar-clock, §4).
- (j) *Partial-run notes* (X1-follow Part 4): **not applied** to X1b's shard CSVs. Rows carry `nkernels` and `partial(rc=…)` as the harness writes them.

**Deliberate deviations from X1's cap policy (Jeffery, 2026-10-22)**

- (a) Keys that time out at 1,200 s and were in X1's 24 h pass skip the 5,400 s pass and go straight to the long pass: 11 vector-clock and 8 scalar-clock keys.
- (b) The long pass runs on the 4060 partition (`rtx4060ti16g`) with `--time 24:00:00` and a tool cap of 84,600 s (23.5 h), not X1's 86,400 s on `max` (`p_final_24h.sh`, 3be0591).
- (c) Small-memory long-pass keys may run on any good 125 GB `rtx4060ti16g` host; X1 did the same.
  - Jeffery's 10-23 choices: the scalar-clock knn and expdist ran on 125 GB hosts (319352, on c74 and c24) with a fallback to the 188 GB hosts, which was not needed. The vector-clock knn and expdist went back to the 188 GB hosts (319350, c64).
- (d) **2026-10-24, Jeffery: the report is written without waiting for the HeCBench vector-clock tail.**
  - P9-expdist's 84,600 s run (319350_1) was running when the report was first written. It ended at 10-24 21:56 as TIMEOUT with no kernel written; its row is folded in (§4).
  - The cap policy's 24 h pass for P7-particlefilter and P7-haversine vector-clock (both TIMEOUT at 5,400 s) is not run: Jeffery's decision of 10-24, after §4's host finding. Both stay TIMEOUT at 5,400 s.

**Comparison rule** (§9): where X1 has a 5,400 s result and X1b does not (deviation (a)), X1's final verdict
is compared with X1b's long-pass verdict. The cap columns of §9 say which rows each side holds.

## 2. Commands

```
# worktree (runtime = the main checkout via ACCEL_PROF_HOME; harness = the worktree), from cuVein at f551ca0
git worktree add /home/fzheng4/wt-x1b -b eval/final-sweep-b cuVein        # + X1's symlinks (lib, build, ScoR, cuHadron, nv-compute/lib)
# dry run: 2 programs, one rep
IDS=P5-norace_interblock_atom,P4-graph-connectivity-racy-small NSHARDS=1 REPS=1 TAG=final-b-dryrun RES=final-b-dryrun \
  STORE_TAG=final-2026-11-dryrun sbatch --array=0 -J x1b-dryrun -o <RT>/eval/baselines/setup/build_logs/finalb-dryrun-%A_%a.log \
  eval/baselines/setup/p_final.sh                                                                   # 317628 (c56)
# first pass (p_final.sh defaults: PSETS=P1,P3,P4,P5,P6,P7,P9 NSHARDS=48 TAG=final-b CAP=1200 STORE_TAG=final-2026-11 HB_SHARDS=16)
sbatch --array=0-47%14 eval/baselines/setup/p_final.sh                                              # 317637 (shards 0, 1 ran)
PSETS=PI NSHARDS=64 TAG=final-b-pi sbatch --array=0-63%14 --dependency=afterany:317637 -J x1b-final-pi \
  -o <RT>/eval/baselines/setup/build_logs/finalb-pi-%A_%a.log eval/baselines/setup/p_final.sh       # 317638
sbatch --array=2-17%4 -x c2,c21,c23,c37,c46,c54,c77 -J x1b-final-r1 eval/baselines/setup/p_final.sh       # 317702 (node probe)
sbatch --array=18-42%4 -x c2,c21,c23,c37,c43,c46,c54,c77 -J x1b-final-r2 eval/baselines/setup/p_final.sh  # 317729 (node probe)
sbatch --array=2-47%14 -x c2,c21,c23,c37,c46,c54 eval/baselines/setup/p_final.sh                          # 318511
# 84,600 s pass, one rep (p_final_24h.sh: CAP=84600 REPS=1, rtx4060ti16g, 1 day; shard k = the k-th id of the file in manifest order)
MODE=vector-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_vc_ids_1.txt NSHARDS=8 TAG=final-b-24h-vc-1 \
  sbatch --array=0-7%1 -x 'c[0-3],c[23-24],c37,c46,c[39-44],c[50-59],c[73-79]' $W/eval/baselines/setup/p_final_24h.sh   # 319061
MODE=scalar-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_sc_ids_1.txt NSHARDS=4 TAG=final-b-24h-sc-1 \
  sbatch --array=0-3%1 -x 'c[0-3],c[23-24],c37,c46,c[39-44],c[50-59],c[73-79]' $W/eval/baselines/setup/p_final_24h.sh   # 319062
#   (small-memory tasks later given ExcNodeList=c2,c21,c23,c37,c43,c46,c54,c77 with scontrol, §5)
# 5,400 s pass (p_final_long.sh: CAP=5400, 3 reps) and 84,600 s batch 2, submitted by the coordinating session (Jeffery, 10-22 21:49)
XS=c2,c21,c23,c37,c43,c46,c54,c77
MODE=vector-clock ID_FILE=$W/eval/baselines/setup/final_b_long_vc_ids_s.txt NSHARDS=7 TAG=final-b-long-s sbatch --array=0-6%1 -x $XS eval/baselines/setup/p_final_long.sh   # 319346
MODE=vector-clock ID_FILE=$W/eval/baselines/setup/final_b_long_vc_ids_b.txt NSHARDS=2 TAG=final-b-long-b sbatch --array=0-1%1 eval/baselines/setup/p_final_long.sh          # 319347
MODE=scalar-clock ID_FILE=$W/eval/baselines/setup/final_b_long_sc_ids_1.txt NSHARDS=2 TAG=final-b-long-sc-1 sbatch --array=0-1%1 eval/baselines/setup/p_final_long.sh       # 319348
MODE=vector-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_vc_ids_2s.txt NSHARDS=1 TAG=final-b-24h-vc-2s sbatch --array=0%1 -x $XS eval/baselines/setup/p_final_24h.sh   # 319349
MODE=vector-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_vc_ids_2b.txt NSHARDS=2 TAG=final-b-24h-vc-2b sbatch --array=0-1%1 eval/baselines/setup/p_final_24h.sh        # 319350
MODE=scalar-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_sc_ids_2s.txt NSHARDS=2 TAG=final-b-24h-sc-2s sbatch --array=0-1%1 -x $XS eval/baselines/setup/p_final_24h.sh # 319351
MODE=scalar-clock ID_FILE=$W/eval/baselines/setup/final_b_24h_sc_ids_2b.txt NSHARDS=2 TAG=final-b-24h-sc-2b sbatch --array=0-1%1 eval/baselines/setup/p_final_24h.sh        # 319352
# post-processing (CPU, partition normal): kept/dropped 84,600 s keys; merge --override final-b-long,final-b-long-sc,
# final-b-24h-kept-vc,final-b-24h-kept-sc -> eval/results/final-b/merged/baselines-cuvein.csv; confirm-detail view
# (symlinks, ~/x1b/confirm_final-b-merged); classify_residuals.py (output redirected to merged/); FINAL_B=1 final_sanity.py;
# final_verdict_diff.py + verdict_diff.py against x0-default; final_b_old_vs_new.py; final_report_tables.py; other tools' sha256
sbatch eval/baselines/setup/p_final_b_post.sh                                                       # 320157 (c25)
# store checks (CPU), scripts and logs in eval/results/final-b/checks/
sbatch shall.sh   # 320160: hb_stats.hb_clock.sharded over every kernel JSON of the five stores
sbatch rtt23.sh   # 320161: P5 rtraw, X1's and X1b's recordings, t23_closure.py scan + diff --all (R3 closure off / on)
sbatch pf.sh      # 320158: particlefilter / haversine vector-clock 5,400 s reps and kernel JSONs, X1 and X1b stores
```

## 3. Results

Coverage: 4,725 manifest ids × 2 modes. Missing (id, mode): 0. Ids in the CSV that are not in the manifest: 0.
CSV rows: 28,234.

The merged file holds the first pass's rows except the keys a later pass overrides:
- 11 keys at 5,400 s (9 vector-clock, 2 scalar-clock).
- 18 keys at 84,600 s (10 vector-clock, 8 scalar-clock).

87 base rows were replaced by 51 override rows. P9-atomicCAS vector-clock (84,600 s run: ERROR) keeps
its 1,200 s rows. Verdicts are collapsed per (id, mode) as `make_tables.py` collapses them:
RACE > CLEAN > TIMEOUT > ERROR over the reps.

| suite | programs | rows | mode | CLEAN | RACE | TIMEOUT | ERROR | cap (s) |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 2400 | vector-clock | 200 | 200 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 200 | 200 | 0 | 0 | 1200 |
| P3 | 60 | 360 | vector-clock | 44 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 44 | 16 | 0 | 0 | 1200 |
| P4 | 28 | 168 | vector-clock | 12 | 16 | 0 | 0 | 1200/5400 |
|  |  |  | scalar-clock | 12 | 16 | 0 | 0 | 1200 |
| P5 | 33 | 198 | vector-clock | 28 | 5 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 30 | 3 | 0 | 0 | 1200 |
| P6 | 50 | 216 | vector-clock | 26 | 8 | 0 | 16 | 1200/84600 |
|  |  |  | scalar-clock | 26 | 8 | 0 | 16 | 1200 |
| P7 | 14 | 66 | vector-clock | 8 | 3 | 3 | 0 | 1200/5400/84600 |
|  |  |  | scalar-clock | 9 | 4 | 1 | 0 | 1200/5400/84600 |
| P9 | 10 | 46 | vector-clock | 6 | 2 | 2 | 0 | 1200/5400/84600 |
|  |  |  | scalar-clock | 6 | 3 | 1 | 0 | 1200/84600 |
| PI | 4130 | 24780 | vector-clock | 1710 | 2420 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 1710 | 2420 | 0 | 0 | 1200 |
| all | 4725 | 28234 | vector-clock | 2034 | 2670 | 5 | 16 | |
|  |  |  | scalar-clock | 2037 | 2670 | 2 | 16 | |

The rows that are neither RACE nor CLEAN, by reason. The classes are `classify_residuals.py --no-dump`'s
(output redirected to `eval/results/final-b/merged/baselines-diagnose.csv`).
- `needs-sm90`: the 16 cuHadron `bulkcpy`/`dsmem` programs whose binaries need sm_90 (`missing-exe`; ERROR, never run), as in X1.
- `hb-state-memory`: TIMEOUT at 32 GB RSS or more.
  - P7-stencil1d at 84,600 s, in both modes (98.5 GB vector-clock, 168.1 GB scalar-clock).
  - P7-particlefilter vector-clock at 5,400 s (124–125 GB on a 125 GB host, §4).
  - P9-atomicCAS vector-clock: the 1,200 s rows, 96–100 GB with no kernel written; its 84,600 s run was OOM-killed (§4).
- `time-cap`: P9-atomicCAS scalar-clock at 84,600 s (60,000 kernel JSONs written).
- `hb-clock-hang`: the script's name for a vector-clock TIMEOUT below 32 GB whose scalar-clock row resolved.
  - P7-haversine vector-clock at 5,400 s. 59–61 of 100 kernels were written, so this is not a stall.
  - P9-expdist vector-clock: TIMEOUT at 84,600 s with no kernel written (21.0 GB peak).

| suite | mode | verdict | reason class | (id, mode) |
|---|---|---|---|---|
| P6 | scalar-clock | ERROR | needs-sm90 | 16 |
| P6 | vector-clock | ERROR | needs-sm90 | 16 |
| P7 | scalar-clock | TIMEOUT | hb-state-memory | 1 |
| P7 | vector-clock | TIMEOUT | hb-clock-hang | 1 |
| P7 | vector-clock | TIMEOUT | hb-state-memory | 2 |
| P9 | scalar-clock | TIMEOUT | time-cap | 1 |
| P9 | vector-clock | TIMEOUT | hb-clock-hang | 1 |
| P9 | vector-clock | TIMEOUT | hb-state-memory | 1 |

No row reached the offline analysis cap (14,400 s): there is no `analysis-timeout` in the merged file.

## 4. The long passes

**5,400 s, three reps** (deviation (a) sends X1's 24 h keys past this pass; `eval/results/final-b-long/`,
`final-b-long-sc/`):
- Peak is the harness's summed-VmRSS peak.
- Node is the host of a finished row; for a TIMEOUT row the host comes from `sacct`, in parentheses.
- X1's column is from `FINAL_SWEEP.md` §4.

| id | mode | first pass (1,200 s): verdict, rep walls (s) | 5,400 s: verdict | rep walls (s) | median wall (s) | peak MB | node | X1 at 5,400 s: verdict, median wall (s), node |
|---|---|---|---|---|---|---|---|---|
| P4-matrix-multiplication-norace-large | vector-clock | CLEAN (reps TIMEOUT, CLEAN, TIMEOUT): 1200.006, 1190.48, 1200.005 | CLEAN | 999.635, 938.776, 945.394 | 945.394 | 5,296 | c76 | — (CLEAN at 1,200 s) |
| P7-bitonic-sort-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | CLEAN | 4718.987, 4463.97, 4473.419 | 4473.419 | 8,910 | c76 | CLEAN, 3689.219, c58 |
| P7-haversine-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.004 | **TIMEOUT** | 5400.006, 5400.006, 5400.006 | 5400.006 | 9,499 | (c24) | CLEAN, 4984.198, c52 |
| P7-lavaMD-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2267.895, 2227.138, 2226.8 | 2227.138 | 23,015 | c43 | CLEAN, 1867.433, c62 |
| P7-mandelbrot-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | CLEAN | 4749.016, 4860.454, 5035.371 | 4860.454 | 1,430 | c40 | CLEAN, 3691.401, c66 |
| P7-particlefilter-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | **TIMEOUT** | 5400.009, 5400.167, 5400.058 | 5400.058 | 125,397 | (c43) | RACE (31), 5320.796, c64 |
| P7-srad-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2332.638, 2352.08, 2297.766 | 2332.638 | 1,072 | c76 | CLEAN, 2160.416, c61 |
| P9-dxtc2-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE (3) | 3499.559, 3384.328, 3361.742 | 3384.328 | 2,893 | c40 | RACE, 3248.307, c79 |
| P9-fpc-cuda | vector-clock | TIMEOUT: 1200.037, 1200.039, 1200.039 | CLEAN | 1776.08, 1740.153, 1785.064 | 1776.08 | 2,852 | c42 | CLEAN, 1294.81, c74 |
| P7-bitonic-sort-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.004, 1200.014 | CLEAN | 2224.487, 2219.591, 2204.554 | 2219.591 | 17,746 | c40 | CLEAN, 3706.864, c51 |
| P7-mandelbrot-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.007, 1200.007 | CLEAN | 2175.979, 2112.824, 2122.107 | 2122.107 | 2,336 | c40 | CLEAN, 2339.662, c52 |

5,400 s pass, vector-clock: 9 ids; RACE 1, CLEAN 6, TIMEOUT 2. Scalar-clock: 2 ids; CLEAN 2.

**The two keys still out at 5,400 s.** Their 24 h pass, as the cap policy gives it, is not run (Jeffery,
10-24; §1 (d)).

- **P7-particlefilter vector-clock: X1's detection is lost at this cap, and on this host.**
  - X1: the three 5,400 s reps ran on c64 (`mem_total_gb` 202.3). Each ended with rc 1 before the cap (not timed out; OOM per X1 §1 (j)), at 5,313–5,331 s and 185.3–185.4 GB after 3 kernels. The races are in `kernel_2.json` (31 `hb_races`), and the harness's rule ("a race already visible in a partial dump is still a race") made the rows RACE (31).
  - X1b: the three reps ran on **c43, a 125 GB host** (`mem_total_gb` 135.0). They reached the 5,400 s cap (rc 124, `timed_out`) at 124.1–125.4 GB with `nkernels` = 3.
  - A timed-out rep is TIMEOUT by rule (`parallel.py`: `if rm.get("timed_out"): verdict = "TIMEOUT"`), and the X1b store keeps no vector-clock kernel JSON for this id (checked, `checks/pf-320158.log`).
  - The task was meant for the 188 GB hosts. `p_final_long.sh`'s default host list does not keep it off c39–c44 (§1 (d)).
  - Its scalar-clock row is RACE (31) at 1,200 s: runs ended with rc 1 (`partial(rc=1)`, OOM inferred) at 234–242 s and 189.5–189.7 GB after 3 kernels on c64. This is X1's 24 h scalar-clock outcome, reached here inside the first pass.
- **P7-haversine vector-clock.**
  - X1: CLEAN at 4,952.7–5,101.5 s (c52, EPYC 9115).
  - X1b: TIMEOUT in all three reps on c24 (EPYC 7302P), with 59–61 of 100 kernels written and a peak of 9.4–9.5 GB, the same as X1's.
  - Cross-host walls; the cause is not separated.

**84,600 s, one rep** (deviations (a)–(c); `eval/results/final-b-24h-vc/`, `final-b-24h-sc/`):
- X1's verdict at 5,400 s was TIMEOUT for every one of these keys.
- X1's 24 h column is from `FINAL_SWEEP.md` §4.
- Reports in parentheses.

| id | mode | X1b 84,600 s verdict | wall (s) | peak MB | rc | node | in X1b's merged CSV | X1 24 h (86,400 s): verdict, wall (s), node |
|---|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | RACE (44) | 13156.552 | 71,955 | 0 | c64 | 84,600 s row | RACE, 14534.817, c61 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | RACE (44) | 13323.263 | 71,956 | 0 | c61 | 84,600 s row | RACE, 14550.27, c60 |
| P7-bfs-cuda | vector-clock | RACE (31) | 11500.605 | 1,813 | 0 | c44 | 84,600 s row | RACE, 6289.863, c51 |
| P7-heartwall-cuda | vector-clock | RACE (2) | 61435.923 | 6,194 | 0 | c75 | 84,600 s row | RACE, 35574.705, c58 |
| P7-nbody-cuda | vector-clock | CLEAN | 11252.449 | 29,009 | 0 | c24 | 84,600 s row | CLEAN, 8197.555, c62 |
| P7-pathfinder-cuda | vector-clock | RACE (1) | 35024.582 | 17,596 | 0 | c42 | 84,600 s row | RACE, 28386.115, c63 |
| P7-stencil1d-cuda | vector-clock | TIMEOUT | 84600.019 | 98,492 | 124 | (c61) | 84,600 s row | TIMEOUT, 86400.019 |
| P9-atomicCAS-cuda | vector-clock | **ERROR (out of memory)** | 15229.649 | 189,581 | 1 | (c64) | dropped: the 1,200 s TIMEOUT rows stand | ERROR (OOM), 17624.601; the 5,400 s TIMEOUT stood |
| P9-expdist-cuda | vector-clock | TIMEOUT | 84600.019 | 21,016 | 124 | (c64) | 84,600 s row | TIMEOUT, 86400.015 (no kernel in the cap) |
| P9-knn-cuda | vector-clock | CLEAN | 58674.223 | 22,187 | 0 | c64 | 84,600 s row | CLEAN, 57215.724, c62 |
| P9-tridiagonal-cuda | vector-clock | RACE (24) | 51436.282 | 10,810 | 0 | c78 | 84,600 s row | RACE, 42483.9, c61 |
| P7-haversine-cuda | scalar-clock | CLEAN | 4131.136 | 13,999 | 0 | c24 | 84,600 s row | CLEAN, 6931.599, c63 |
| P7-heartwall-cuda | scalar-clock | RACE (2) | 5728.658 | 6,367 | 0 | c24 | 84,600 s row | RACE, 32057.217, c52 |
| P7-pathfinder-cuda | scalar-clock | RACE (1) | 20855.057 | 68,874 | 0 | c63 | 84,600 s row | RACE, 19225.434, c77 |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT | 84600.017 | 168,102 | 124 | (c63) | 84,600 s row | TIMEOUT, 86400.005 |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT | 84600.023 | 1,104 | 124 | (c73) | 84,600 s row | TIMEOUT, 86400.03 |
| P9-expdist-cuda | scalar-clock | RACE (22) | 2696.849 | 13,774 | 0 | c24 | 84,600 s row | TIMEOUT, 86400.016 |
| P9-knn-cuda | scalar-clock | CLEAN | 9680.41 | 30,386 | 0 | c74 | 84,600 s row | CLEAN, 44762.407, c66 |
| P9-tridiagonal-cuda | scalar-clock | RACE (24) | 9227.804 | 12,340 | 0 | c74 | 84,600 s row | RACE, 36768.052, c61 |

**Totals.**
- 84,600 s pass, vector-clock: 11 keys; RACE 6, CLEAN 2, TIMEOUT 2, ERROR 1.
- 84,600 s pass, scalar-clock: 8 keys; RACE 4, CLEAN 2, TIMEOUT 2.
- Every task of 319061, 319062 and 319349–319352 is COMPLETED as a SLURM job.

**Notes.**
- **P9-atomicCAS vector-clock is ERROR because the host ran out of memory. It is not a detector verdict.**
  - The row's notes: `incomplete-trace(rc=1;nkernels=30000;peak_mb=189581.2)`, err `Killed`, after 15,229 s on c64 (188 GB).
  - Under X1's merge rule the ERROR is dropped (`final-b-24h-kept-vc/dropped.txt`) and the earlier TIMEOUT stands. In X1b that earlier TIMEOUT is the 1,200 s first pass, because deviation (a) skipped the 5,400 s pass; in X1 it was the 5,400 s TIMEOUT.
  - X1's 24 h run of the same key was OOM-killed too (17,625 s, 186.3 GB, 30,000 kernels).
- **P9-expdist vector-clock** reached the 84,600 s cap with no kernel written (`nkernels=0`, 21.0 GB peak, rc 124), as X1's 86,400 s run did.
- **P9-expdist scalar-clock** is RACE (22) in 2,697 s with N = 16. X1's serial pass was TIMEOUT at 86,400 s.
- **Other scalar-clock keys that finished in a fraction of X1's time**: heartwall (5,729 s against 32,057 s), knn (9,680 against 44,762), tridiagonal (9,228 against 36,768). These are cross-host walls.
- **Scalar-clock peaks are higher at N = 16**: pathfinder 68.9 GB (X1: 6.8 GB), stencil1d 168.1 GB (X1: 84.1 GB), knn 30.4 GB (X1: 20.6 GB), haversine 14.0 GB (X1: 8.3 GB).
- **Scalar-clock keys that went to X1's long passes but finished in X1b's first pass at 1,200 s**, with the same verdicts as X1 (cross-host walls):

  | key (scalar-clock) | verdict | X1b wall at 1,200 s cap (s) | X1 |
  |---|---|---|---|
  | P6-asyncmemcpy racy and fixed | RACE (44) | 798–803 (racy), 675–681 (fixed) | 5,400 s pass, 4,594 s (racy) and 4,599 s (fixed) |
  | P7-bfs | RACE (31) | 12 | 1,507 s at 5,400 s |
  | P7-lavaMD | CLEAN | 214 | 1,507 s |
  | P7-srad | CLEAN | 732 | 2,537 s |
  | P9-dxtc2 | RACE (3) | 681–694 | 1,498 s |
  | P7-nbody | CLEAN | 387–397 | 8,015 s in the 24 h pass |
  | P7-particlefilter | RACE (31), OOM after 3 kernels | 234–242 | 5,791 s in the 24 h pass, also OOM after 3 kernels |

## 5. Scheduling and resubmission log

The sources are the session log (`~/x1b/log.txt`), `sacct` (`eval/results/final-b/sacct.txt`, `-D`:
requeued records included) and the shard logs.

- **10-22 02:07**: install commit f551ca0. Install job 317623 (c26); check job 317624 (c56): the green set, see the commit message.
- **02:12**: dry run 317628 (c56, 23 s).
  - P5-norace_interblock_atom was CLEAN and P4-graph-connectivity-racy-small was RACE (10 vector-clock / 3 scalar-clock reports), both modes, one rep.
  - `dry_inspect.sh` (317629, c45) read the dry-run store: `hb_shards` = {vector-clock 0, scalar-clock 16}, the four hashes, `hb_dump` false, cap 1200, and `hb_stats` in both modes' kernel JSONs.
- **02:14**: first pass 317637 (48 shards, `%14`) and PI pass 317638 (64 shards, `%14`, `afterany:317637`).
- **03:23 – 04:18**: 317637_0 (c41) and _1 (c40) ran and COMPLETED.
  - 317637_2–17 (c77), 18–42 (c43) and 43–47 (c61) stopped at the node probe: "/mnt/beegfs/fzheng4 not readable", 13–28 s each, no row written.
  - The resubmissions 317702 (tasks 2–17, at 03:59) and 317729 (18–42, at 04:09) stopped at the node probe on c62 (16 + 14 tasks) and c76 (11).
  - In total there were 87 node-probe failures, 1,242 s.
- **04:57**: d151ceb committed shard 0's CSV ("the rest blocked by BeeGFS being unmounted").
- **12:31**: 318511 submitted (tasks 2–47, `%14`, `-x c2,c21,c23,c37,c46,c54`). The submission has no line in `~/x1b/log.txt`.
- **14:25:44**: **seven running tasks of 318511 (11, 18, 33–37) were REQUEUED in the same second.**
  - The coordinating session requeued them (`scontrol requeue`, the seven youngest running x1b-final tasks) to bring fzheng4 down to 10 GPU nodes, after Jeffery relayed the ARC admins' 10-node rule that afternoon. `~/x1b/log.txt` has no line for it.
  - The requeued records hold 10,995 s.
  - All seven re-ran from the start (14:48–14:53) and COMPLETED. No (id, mode, rep) appears twice in any shard CSV (checked over all 112).
- **15:00**: PI 317638 started; 64 / 64 COMPLETED by 19:57.
- **16:50**: 84,600 s batch 1: 319061 (vector-clock, 8 ids) and 319062 (scalar-clock, 4 ids), `%1`, on the 188 GB host list.
  - The small-memory tasks were given the any-good-host list (`c2,c21,c23,c37,c43,c46,c54,c77`) by `scontrol`. This was seen for 319061_2, _3, _5, _7 and 319062_2, _3 at 20:30.
  - 319061 ran at throttle 6 from about 20:23.
- **19:02**: first pass complete (318511_18 last): 48 / 48 main and 64 / 64 PI shard CSVs.
- **20:41**: meta scan 319235 (c22): 4,709 of 4,725 `meta.json` files had `hb_shards` 16; the other 16 were the `missing-exe` programs.
- **21:49**: the coordinating session submitted 319346–319352 (Jeffery approved the exact list), all `%1`.
- **10-23 03:45 / 03:50**: Jeffery chose to run the scalar-clock knn and expdist (319352) on 125 GB hosts, with a fallback to the 188 GB hosts; the vector-clock ones (319350) went back to the 188 GB hosts.
- **10-23 08:01**: the fallback watcher submitted 319604 for P9-expdist scalar-clock. It had misread shard 0 of 319352 as expdist; shard 0 is knn, CLEAN in 9,680 s. 319604 was cancelled at 08:02 before it started.
- **10-23**: the coordinating session's GPU-cap watcher holds pending x1b-* jobs while another user waits on the 4060 partitions and fzheng4 is at 10 GPU nodes or more.
  - 19:54: atomicCAS scalar-clock reached the cap.
  - 20:05 / 22:12: stencil1d vector-clock / scalar-clock reached the cap.
  - 22:26: 319350_0 (knn vector-clock, CLEAN) ended and 319350_1 (expdist vector-clock) started on c64.
- **10-24**:
  - Jeffery: write the report without waiting (§1 (d)).
  - 15:41–15:50: post-processing 320157 (c25).
  - 15:55–16:03: store checks 320158–320161.
  - 21:56: 319350_1 (expdist vector-clock) reached the cap: TIMEOUT, no kernel written. The sacct record was retaken and post-processing ran again, 21:58–22:06 (320365, c45).

## 6. Sanity checks

`setup/final_sanity.py` with `FINAL_B=1` (inside `p_final_b_post.sh`) over the stores `final-2026-11:1200`,
`-long:5400`, `-long-sc:5400`, `-24h-vc:84600` and `-24h-sc:84600` → `eval/results/final-b/merged/sanity.json`.

- **(a) proved-in-effect over 4,755 `meta.json` files** (4,725 + 9 + 2 + 11 + 8).
  - Every one except 16 has `hb_dump: false`, the f551ca0 hashes (collector `b746b4dd`, libsanalyzer `5a20fd14`, fatbin `a2d7368b`, late fatbin `e9634312`), status done, arch 8.9, no excluded node, `tool_timeout == tool_timeout_cap ==` its store's cap, and `hb_shards = {"vector-clock": 0, "scalar-clock": 16}`.
  - The 16 are the `needs-sm90` programs (no binary; `error=missing-exe`). At first writing P9-expdist in `-24h-vc` was a 17th (status `collecting`, the running task); after 319350_1 ended it passes.
  - The harness HEAD (with `dirty=0`) and runtime HEAD (f551ca0) of each store's `meta.json` files are listed in the post log.
  - **73,136 kernel JSONs** (vector-clock 51,500, scalar-clock 21,636): none has `hb_events`; all have `hb_aggregates`, `hb_sync_pass`, `hb_rmw_points` and `hb_stats`, and vector-clock ones also `hb_races` and `hb_chain`. 0 bad.
  - **N = 16, from the runtime itself** (job 320160, `checks/shall-320160.log`):
    - All 21,636 scalar-clock kernel JSONs carry `hb_stats.hb_clock.sharded` with `shards = 16` and 16 per-shard `busy_s` entries: 18,455 in `final-2026-11`, 1,326 in `-long-sc` and 1,855 in `-24h-sc`.
    - None of the 51,500 vector-clock kernel JSONs has a `sharded` block. 0 exceptions.
    - Every shard log's header also states `hb_shards(scalar-clock)=16` (143 logs).
- **(b) Verdict diff against T20's parity recording** (X0's re-score, `eval/results/x0-default/`; 130 (id, mode) keys of `setup/t5b_parity_ids.txt`) → `merged/verdict_diff_t20.txt`.
  - **Same verdict 123.** 9 of them are RACE with a different report set:
    - 2 keys of P1-CC_CUDA_E_Topo… and 1 of P1-CC_CUDA_V_Topo_Push…: the same pc pair with RAW ↔ WAR swapped.
    - 2 keys of P4-graph-coloring-racy-small: the parity side also reports `shared:0x500-0x650:WAW`.
    - 4 keys of two PI programs.
  - **Different 7, all by cap**: the parity recording's 120 s timeout against this recording's caps.
    - P6-interkernel writewrite racy and P9-overlap: CLEAN in both modes.
    - P7-bfs: RACE in both modes.
    - P7-particlefilter scalar-clock: RACE.
  - Causes: cap 7, schedule 0, other 0.
  - Against X1's 122 / 8: P7-particlefilter vector-clock is now TIMEOUT on both sides (X1b at 5,400 s, the parity recording at 120 s).
  - The literal rep-1 diff (`verdict_diff.py`, `merged/verdict_diff_t20_rep1_literal.txt`) lists 16 differing rows of 130: exactly the 7 keys of different verdict and the 9 with a different report set.
- **(c) `tv_violation`: none** in any kernel JSON of any store, in every suite and mode.
- **(d) Static-leg-only verdicts: 0.** Every merged RACE/CLEAN row has `hb_races` (vector-clock) or `hb_sync_pass` (scalar-clock) in every saved kernel JSON of its mode.

## 7. The other tools' results

They were not re-run, as the brief says.

`p_final_b_post.sh` records the sha256 of every `eval/results/baselines-*.csv` other than cuVein's and the
three cuVein-derived analysis files, before and after the post-processing:
- **209 files, unchanged.**
- Equal to X1's `eval/results/final/other_tools.sha256.after` and `.pre-sweep`.
- `git diff --stat` against f551ca0 and against `cuVein` over the 209 files is empty.

Copies: `eval/results/final-b/merged/other_tools.sha256.{before,after}`.

The post job also checked X1's tracked results (`eval/results/baselines-cuvein.csv`, `final*/`): 0 changed entries.
`classify_endpoints.py`, `classify_fp_causes.py`, `make_tables.py` and `cuvein_rev.sh` were **not run**: they
write X1's `baselines-{disagreements,fp-causes}.csv`, tables and revision pin.

## 8. Node-hours

From `sacct` (`eval/results/final-b/sacct.txt`, the x1b-* job ids with `-D`, retaken 10-24 21:57 after the
last task ended; the two post-processing jobs added from their own records). Counted: the 87 node-probe failures (1,242 s) and the 7
REQUEUED records (10,995 s). Not counted: the BeeGFS probe jobs (`probe.sh`, 24 jobs, 47 s on
`rtx4060ti16g`) and the CPU inspection jobs.

| job name | node-hours | nodes | first start | last end |
|---|---|---|---|---|
| x1b-dryrun | 0.0 (23 s) | 1 | 2026-10-22T02:12:52 | 2026-10-22T02:13:15 |
| x1b-final | 51.8 | 16 | 2026-10-22T03:23:12 | 2026-10-22T19:02:42 |
| x1b-final-r1 | 0.1 | 1 | 2026-10-22T04:37:19 | 2026-10-22T04:41:06 |
| x1b-final-r2 | 0.1 | 2 | 2026-10-22T04:41:06 | 2026-10-22T04:44:23 |
| x1b-final-pi | 15.2 | 12 | 2026-10-22T15:00:10 | 2026-10-22T19:57:49 |
| x1b-final-long | 32.3 | 5 | 2026-10-22T22:01:19 | 2026-10-23T09:56:44 |
| x1b-final-24h | 192.7 | 11 | 2026-10-22T16:53:35 | 2026-10-24T21:56:13 |
| x1b-post | 0.3 (530 s + 512 s) | 2 | 2026-10-24T15:41:26 | 2026-10-24T22:06:27 |
| all | 292.4 | 22 | 2026-10-22T02:12:52 | 2026-10-24T22:06:27 |

The 22 nodes are 20 GPU hosts (c77 among them, where every task stopped at the node probe) and c25 and
c45 for the post jobs. (`report_tables.md` counts 21 for the GPU jobs because 319604, cancelled before it
started, has `None assigned`.) X1 used 434.4 node-hours.

## 9. Against X1 (the 2026-10-13/16 recording)

Collapsed verdicts per suite, X1's merged file (`eval/results/baselines-cuvein.csv`) against X1b's
(`eval/results/final-b/merged/baselines-cuvein.csv`), by `setup/final_b_old_vs_new.py` →
`eval/results/final-b/merged/old_vs_new.md`:

| suite | mode | X1 RACE / CLEAN / TIMEOUT / ERROR | X1b RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |
|---|---|---|---|---|
| P1 | vector-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P1 | scalar-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P3 | vector-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P3 | scalar-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P4 | vector-clock | 16 / 12 / 0 / 0 | 16 / 12 / 0 / 0 | 0 |
| P4 | scalar-clock | 16 / 12 / 0 / 0 | 16 / 12 / 0 / 0 | 0 |
| P5 | vector-clock | 4 / 29 / 0 / 0 | 5 / 28 / 0 / 0 | 1 |
| P5 | scalar-clock | 2 / 31 / 0 / 0 | 3 / 30 / 0 / 0 | 1 |
| P6 | vector-clock | 8 / 26 / 0 / 16 | 8 / 26 / 0 / 16 | 0 |
| P6 | scalar-clock | 8 / 26 / 0 / 16 | 8 / 26 / 0 / 16 | 0 |
| P7 | vector-clock | 4 / 9 / 1 / 0 | 3 / 8 / 3 / 0 | 2 |
| P7 | scalar-clock | 4 / 9 / 1 / 0 | 4 / 9 / 1 / 0 | 0 |
| P9 | vector-clock | 2 / 6 / 2 / 0 | 2 / 6 / 2 / 0 | 0 |
| P9 | scalar-clock | 2 / 6 / 2 / 0 | 3 / 6 / 1 / 0 | 1 |
| PI | vector-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |
| PI | scalar-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |

**Every (id, mode) whose verdict changed (5 of 9,450).** Reports in parentheses; caps are those of the rows each side holds.

| id | mode | X1 verdict | X1 cap (s) | X1b verdict | X1b cap (s) | direction |
|---|---|---|---|---|---|---|
| P5-race_interblock_none-lock_rtraw | vector-clock | CLEAN | 1200 | RACE (1) | 1200 | CLEAN → RACE |
| P5-race_interblock_none-lock_rtraw | scalar-clock | CLEAN | 1200 | RACE (1) | 1200 | CLEAN → RACE |
| P7-haversine-cuda | vector-clock | CLEAN | 5400 | TIMEOUT | 5400 | CLEAN → TIMEOUT |
| P7-particlefilter-cuda | vector-clock | RACE (31) | 5400 | TIMEOUT | 5400 | RACE → TIMEOUT |
| P9-expdist-cuda | scalar-clock | TIMEOUT | 86400 | RACE (22) | 84600 | TIMEOUT → RACE |

**T24 direction check: 0 keys that are RACE in X1 and CLEAN in X1b.** One RACE in X1 left the RACE
column: P7-particlefilter vector-clock became TIMEOUT, not CLEAN (§4: the detection is lost at the
5,400 s cap on a 125 GB host).

- **P7-haversine and P7-particlefilter vector-clock** (CLEAN → TIMEOUT, RACE → TIMEOUT): both are at 5,400 s on both sides; §4 has the reps, hosts and memory. The cap policy's 24 h pass for both is not run (Jeffery, 10-24; §1 (d)).
- **P9-expdist scalar-clock** (TIMEOUT → RACE): X1's serial scalar-clock run was TIMEOUT at 86,400 s. X1b's run at N = 16 finished in 2,697 s with 22 reports (§4). The coordinator's triage of the 22 reports is in §11.
- **P5-race_interblock_none-lock_rtraw, both modes** (CLEAN → RACE; labelled RACE in the manifest). Verified from the stores (`checks/rtraw*.log`, `checks/rtt23-320161.log`, `eval/results/final-b/rtraw-t23/`):
  - *The two recordings differ.* X1: c62 (EPYC 8124P, driver 580.82.07, runtime 4094187), 15 events, vector-clock `hb_chain` 7 edges / 3 uncertain, `hb_races` empty. X1b: c79 (EPYC 7302P, driver 615.71.09, runtime f551ca0), 14 events, 6 edges / 2 uncertain.
  - X1b's vector-clock `hb_races` holds two entries:
    - a DR, WAW pc 0x170 → 0x2f0. These are the `dummy = data[0]` stores at lines 28 and 37, inside the two critical sections.
    - an SC, WAR pc 0x140 → 0x340: the rtraw pair.
    - Both are `a2_uncertain`.
    - The row's one report is `global:0x170-0x2f0:WAW`, in both modes.
  - The program's RMW release / acquire points are identical in both stores.
  - *Both recordings analysed by X1b's verdict layer* (f551ca0 `python/`), with R3's location closure off (`CUVEIN_R3_LOC_CLOSURE=0`, the pre-T23 rule) and on (`t23_closure.py scan` + `diff --all`, job 320161):
    - **X1's recording is CLEAN both ways**: WAW 0x170/0x2f0 ORDERED; WAR 0x140/0x340 SC (`latent-sc` in vector-clock). The closure fired in 0 kernels.
    - **X1b's recording is RACE both ways**: WAW 0x170/0x2f0 RACE (`structural`). The closure fired in both modes (landing `0xb0`, `0x330`) but only moved the rtraw pair. In vector-clock it stays SC and its `hb_chain` `0x1b0 → 0x330` is withdrawn; in scalar-clock it goes ORDERED (chain `0x1b0 → 0x330`) → SC. An SC pair is not a race report.
  - **So the CLEAN → RACE follows the recording, not T23's `same_loc` closure.** The closure's effect here is the one `R3_CLOSURE.md` §0 found on X4's c58 recordings: the rtraw pair, ORDERED → SC.
  - The RACE rests on the `dummy` WAW pair. `FINAL_RTRAW.md` (§0, finding 3) describes it as "a pair the fenced lock orders in every schedule", reported when the lock hand-off cannot be certified.
  - What leaves that pair unordered in X1b's recording is not separated here: one event fewer, a different host and driver, and the T22 cont. / T24 runtime that recorded it.

**Same verdict, different caps** (27 keys, listed in `old_vs_new.md`):
- Most are the cap-policy changes: 84,600 s instead of 86,400 s, or 1,200 s instead of 5,400 s / 86,400 s where X1b's scalar-clock finished in the first pass.
- P4-matrix-multiplication-norace-large vector-clock: CLEAN at 1,200 s in X1, CLEAN at 5,400 s in X1b (interpretation (c)).
- P9-atomicCAS vector-clock: TIMEOUT at 5,400 s in X1, TIMEOUT at 1,200 s in X1b (§4).
- P9-expdist vector-clock: TIMEOUT at 86,400 s in X1, TIMEOUT at 84,600 s in X1b.

**RACE in both runs, with a different report set** (not a verdict change; not investigated here).

| suite | vector-clock | scalar-clock |
|---|---|---|
| P1 | 31 | 27 |
| P4 | 3 | 1 |
| P6 | 0 | 1 |
| PI | 396 | 382 |

- In 677 of the 841 keys the set of pc pairs is the same and only the type or orientation differs (RAW ↔ WAR), as in §6 (b).
- In the others the pairs differ: X1b's are a subset in 63 and a superset in 83, and different in 18.

Facts only: P1–P4 and PI have the same collapsed verdicts in both runs. P5's RACE count rises by one
(rtraw) in each mode. P6 is unchanged. P7 vector-clock has 3 TIMEOUT keys against X1's 1, and P9
scalar-clock has 1 against X1's 2.

## 10. What remains unverified

- **P7-particlefilter and P7-haversine vector-clock stay TIMEOUT at 5,400 s**: the 24 h pass is not run (Jeffery, 10-24; §1 (d)). particlefilter's 5,400 s task ran on a 125 GB host (c43), where X1's runs needed 185 GB before they were killed. Whether the TIMEOUT reflects that host is not established. haversine's walls are cross-host (c24, EPYC 7302P, against X1's c52, EPYC 9115).
- **The 84,600 s rows are single reps** (Jeffery's choice for the long pass), with walls and native walls from one run.
- **Cross-host walls**: 19 nodes, three CPUs, two RAM sizes, five drivers (§0). §4's X1-vs-X1b walls are not same-host comparisons.
- **OOM** is inferred from SIGKILL and the peaks; the nodes' kernel logs were not read. The cases are P9-atomicCAS vector-clock ("Killed" at 189.6 GB on a 188 GB host) and P7-particlefilter scalar-clock (`partial(rc=1)` at 189.5–189.7 GB).
- **P5 rtraw**: §9 shows the change follows the recording, but which difference of the recording leaves the `dummy` pair unordered is not separated.
- **Not done for X1b**:
  - X1-follow's partial-run notes (§1 (j)).
  - `classify_endpoints.py`, `classify_fp_causes.py`, `make_tables.py` and the revision pin (§7). The paper's tables are still X1's.
- **Label questions**: P6-asyncmemcpy-…-fixed (labelled race-free) is RACE again at 84,600 s, and P9-knn (labelled racy) is CLEAN in both modes again. §11 has the coordinator's P9 triage. The labels are unchanged.

## 11. P9 triage (the coordinating session's findings, 2026-10-23/24)

These are the coordinator's findings, not re-derived here. The labels are unchanged and the decision is
Jeffery's. None of this changes a cuVein verdict.

- **Versions.** SuperCollider's artifact pins HeCBench 6a8c46c (2025-09-09). Our P9 builds are from 2026-09-17: HeCBench 2b73f4da07, CUDA 13.3.
- **All 159 artifact-vs-ours pairs, compared kernel by kernel on the sm_89 SASS** (`~/triage_sc_compare/sc_vs_ours.csv`, script `sc_compare.py`, log `run-319983.log`; 159 rows, checked).
  - Same programs: Indigo (99), cuHadron, and five HeCBench apps (tridiagonal, overlap, fpc, gpp, crs).
  - mr differs, but not in a race-related way.
- **Four HeCBench apps are different programs**, because upstream fixed races after 6a8c46c:
  - **atomicCAS** (upstream a3c11f79d4): our first read is a strong relaxed load, so our binary is race-free and the RACE label should be CLEAN for it. SuperCollider's 9 reports are real races in its own binary. cuVein gives no verdict (TIMEOUT; vector-clock 84,600 s run OOM, §4).
  - **knn** (22574e7827): the shared variables became per-thread, so it is race-free. cuVein's CLEAN (both modes) is correct but is scored as a miss against the RACE label.
  - **expdist** (3583b2c4d9, a partial fix): still racy in ours, for a different reason.
    - 18 of the 22 scalar-clock reports are real same-value WAW at `kernel.h:28`: `sh_A` / `sh_scale_A` are filled by all 8 `ty` rows, and upstream guarded only `sh_B`.
    - The other 4 are false reports (next item).
  - **dxtc2** (rewritten): still racy in ours, for a different reason. Its 3 reports (RACE (3) in both modes here) are a real intra-warp race at `main.cu:448` (`colors[xrefs[idx]] = colors[idx]`, no `__syncwarp`).
- **False-report class (not fixed).** On sm_89, ptxas lowers a shared-memory float/double `atomicAdd` to an `LDS` plus an `ATOMS.CAST.SPIN` retry loop, and cuVein pairs the plain `LDS` with other threads' CAS.
  - expdist's 4 false reports are this class: `distance<float/double>` 0x2c90→0x2cb0 and 0x5750→0x5770; `reduce_cross_term` 0x7a0→0x7c0 and 0x7b0→0x7d0.
  - The same class appears in T21b's raft-1 (64-bit).
- **`run_supercollider.py` parser defect.** Its regex expects "In function" (`eval/baselines/run_supercollider.py` line 42, checked), but SuperCollider prints "Inlined function … at file:line", so SuperCollider's rows show `reports_dedup=0`. The other tools were not re-run and §7's hash check stands; the defect is reported only.
- **Sources and disassemblies**: `~/triage_p9/` and `~/triage_atomiccas/`.

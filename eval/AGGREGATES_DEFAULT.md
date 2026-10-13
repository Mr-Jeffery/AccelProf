# X0 — the freeze: verdicts from the runtime's aggregates by default

Branch `fix/aggregates-default` from `cuVein` d38d057; code commit `fce124c`; this report and the
CLAUDE.md lines in the commit after it. Unmerged (Jeffery merges). From `fce124c` on, the detector
is frozen: no change to `sanalyzer/`, `nv-compute/` or `python/hb_oracle.py` before the
submission except a bug fix with a failing test.

## 0. Runtime (precondition)

The installed runtime is the one built from the T16 + T20 merge: install commit `d38d057`
("Install the runtime built from ba99486 (T16 + T20 merge)"), built on c26 from `8804856`
(`ba99486` + the CLAUDE.md revision; `git merge-base --is-ancestor ba99486 8804856` holds),
`build_logs/merge-install-311877.log`; its merge check `build_logs/merge-check-311878.log`
(c73, 2026-10-13): 312 passed / 2 skipped, 55/55, 27/27, SPOT CHECK: ALL EQUAL.

| component | sha256[:16] |
|---|---|
| `build/sanalyzer/lib/libsanalyzer.so` | `2201fcb7d57ae783` |
| `lib/libcompute_sanitizer.so` (collector) | `ee78cb899e8a0a65` |
| `nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin` | `a2d7368bc1c61986` |
| `…_late.fatbin` (T15, not loaded by default) | `e96343121c74ca0a` |

The same four hashes are printed at the head of both green-set logs below.

## 1. What changed

`git diff --stat cuVein..fce124c` — `python/`, `eval/` only (CLAUDE.md in the next commit);
nothing under `sanalyzer/` or `nv-compute/`, so the default tool path is untouched:

```
 eval/README.md                          | 15 ++++--
 eval/baselines/parallel.py              | 24 ++++++---
 eval/baselines/run_cuvein.py            | 13 +++--
 eval/baselines/setup/t4_parity.py       |  7 ++-
 eval/baselines/setup/x0_confirm_diff.py | 88 +++++
 eval/baselines/setup/x0_over_cutoff.txt | 14 ++++++
 python/sync_dominance.py                | 27 +++++++---
 python/test_cp_async.py                 |  6 ++-
 python/test_no_dump.py                  | 56 ++++++++++++++---
```

1. **`sync_dominance.use_aggregates(trace)`** (step 1). True when the file has no
   `hb_events` (nothing to replay); otherwise False under `CUVEIN_PREFER_RECORDS=1`; otherwise
   True when the file carries `hb_sync_pass` or `hb_rmw_points` (every file recorded since T4)
   or under `CUVEIN_PREFER_AGGREGATES=1` (kept, now redundant); False otherwise (a pre-T4 dump).
   A no-dump file under `CUVEIN_PREFER_RECORDS=1` still reads its aggregates: there is no
   record to replay, and returning False there would silently drop the sync pass and R3's
   points. That is the one reading of the brief's "False only when…" I chose, and the reason.
   The readers keep their per-key fallback (`aggregated_sync_pass` / `aggregated_rmw_points`
   return None for an absent key and the records then serve). `barrier_only_pairs()`,
   `trace_rmw_points()` and the cutoff variable are unchanged. The docstring, the comment
   block above `use_aggregates`, the comment above `offline_pass()` and `eval/README.md`
   ("No-dump mode"; "Re-analyzing existing traces": the replay is the parity reference, the
   cutoff applies to pre-T4 stores and the reference only) say so.
2. **Tests** (step 2).
   - `test_no_dump.py`: the records side of `_analyze` used to get the records by *popping*
     `CUVEIN_PREFER_AGGREGATES` — implicitly the records path, which after step 1 would have
     become the aggregates on both sides. It now sets `CUVEIN_PREFER_RECORDS=1` with the cutoff
     lifted (`path="records"`); `path="default"` clears all three variables. New test
     `test_default_path_equals_records_without_cutoff` (both modes × both recordings = 4 cases):
     with no environment, `use_aggregates()` is True on the dump and `analyze()` equals the
     records path with `CUVEIN_BARRIER_PASS_MAX_LANES=10**12` on every verdict field (the full
     `_vkey`: pair, verdict, hb_class, conflict_class, race_type, matrix_class, distance, weight,
     candidate, rescued, a2_uncertain, model_bug, chain, strength), `skipped_edges`, the candidate
     diagnostics, `summary` and `gate_policy`.
   - No other test sets `CUVEIN_PREFER_AGGREGATES` (grep over `python/test_*.py`).
   - `test_cp_async.py::test_dump_without_marker_keeps_the_pre_t1a_reading` failed on the first
     green-set run (job 311881, 3 cases): it builds a "pre-T1a" dump by deleting `hb_async`, the
     commit/wait records and `hb_races*` from a fresh dump, but left the T4/T16 keys HbClock
     computed *with* the async agents, so the new default read an agent-aware `hb_sync_pass`
     from a file that is otherwise pre-T1a. A pre-T1a dump predates T4 and has none of those
     keys; the test now drops `hb_sync_pass`, `hb_rmw_points`, `hb_events_count`,
     `hb_lanes_count`, `hb_chain`, `hb_gate_policy` too. The detector was not changed for it.
     The other tests that rewrite a dump strip `hb_races*` to read a vector-clock dump as
     scalar-clock mode (they now read `hb_sync_pass`, which T4/T20 parity shows equals the
     offline pass) or test pre-T3b dumps through `hb_oracle` only (not affected).
   - `eval/baselines/setup/t4_parity.py` had the same implicit records side; it now sets
     `CUVEIN_PREFER_RECORDS=1` there. `nodump_spot_cmp.py` sets `CUVEIN_PREFER_AGGREGATES=1` on
     purpose (one reader path for every recording) and is unchanged.
3. **Harness `--timeout-cap`** (step 3). `parallel.py` (`run` and `collect`) and
   `run_cuvein.py` take `--timeout-cap` (default 1200, the old hard-coded value) in
   `min(max(10 × native, floor), cap)`. `parallel.py` records it in `meta.json`
   (`tool_timeout_cap`) and, from the meta, as a **prefix** `cap=<s>;` of every row's notes
   (`a2_window_count.py:797` reads the notes after `classes=` to the end of the field, so a
   suffix would have leaked into its column; `classify_residuals._KV` matches only
   `native_rc|dump_mb|timeout|events`). A store collected before X0 has no `tool_timeout_cap`
   and its re-scored rows carry no `cap=` (it is not inferred). `run_cuvein.py` writes the
   prefix on every row it writes. **Deviation from the brief:** "parallel.py passes it through
   to run_cuvein.py" — `parallel.py` never runs `run_cuvein.py` (it imports it for
   `_analyze_reports`, `classes_note`, `split_raw`); each script takes the flag itself.
   Pre-existing and not changed: `parallel.py collect` ignores `--timeout-floor`.

## 2. Green set (step 4) — tested

```
W=<wt-x0> sbatch -p rtx4060ti16g -x c54,c2 --job-name=x0-green \
  --output=eval/baselines/setup/build_logs/x0-green-%j.log eval/baselines/setup/merge_check.sh
```
`merge_check.sh` wipes `ScoR/microbenchmarks/artifacts/*` and the cuHadron test dirs and
re-records every trace with the installed runtime.

| job | node | A4 files + `test_instance_gate.py` | `test_instance_gate.py` alone | `test_no_dump.py` | no-dump spot check |
|---|---|---|---|---|---|
| 311881 (before the cp.async test fix) | c73 | 309 passed, **3 failed**, 2 skipped | 55/55 | 31/31 | ALL EQUAL |
| **311899** (`fce124c`'s tree) | c73 (RTX 4060 Ti, sm_89, driver 580.82.07) | **312 passed, 2 skipped** | **55/55** | **31/31** | **ALL EQUAL** |

312 + 31 = 343 = the expected 339 plus the 4 new cases. The 2 skips are
`test_instance_gate.py:104,118` (empty parameter set), as in every run since T12.

## 3. Re-score of the T20 parity store (step 5) — proved-in-effect on this store

Store `/mnt/beegfs/fzheng4/cuvein_traces/t20-parity2`: the 65 programs of
`setup/t5b_parity_ids.txt`, both modes, `YOSEMITE_HB_DUMP=1` (records and aggregates in every
kernel JSON), recorded by T20's final build (`STORE_INFO.json`: `git_head` 31845b3,
2026-10-11), 79 GB, 918 kernel JSONs. 64 kernels of 6 programs (× 2 modes) are above the
5 M lane-access cutoff (`setup/x0_over_cutoff.txt`, from T20's `t4_parity` output).

```
CUVEIN_PREFER_RECORDS=1 CV=<wt-x0> TAG=t20-parity2 OUT=x0-records IDFILE=eval/baselines/setup/t5b_parity_ids.txt \
  EXTRA="--analysis-timeout 14400" sbatch --array=0-7 --job-name=x0-rec eval/baselines/setup/p_analyze_cpu.sh   # 311883
env -u CUVEIN_PREFER_RECORDS CV=<wt-x0> TAG=t20-parity2 OUT=x0-default IDFILE=eval/baselines/setup/t5b_parity_ids.txt \
  EXTRA="--analysis-timeout 14400" sbatch --array=0-7 --job-name=x0-def eval/baselines/setup/p_analyze_cpu.sh   # 311884
.env/bin/python eval/baselines/verdict_diff.py 'eval/results/x0-records/*.csv' 'eval/results/x0-default/*.csv'
.env/bin/python eval/baselines/setup/x0_confirm_diff.py eval/baselines/confirm_x0-records eval/baselines/confirm_x0-default \
  --over <(awk '!/^#/{print $1, $2}' eval/baselines/setup/x0_over_cutoff.txt)
sbatch eval/baselines/setup/x0_kdiff.sh                                                                     # 311902
srun -p normal -x c54,c2 --time=00:30:00 .env/bin/python eval/baselines/setup/x0_mm_detail.py
```
Results: `eval/results/x0-records/`, `eval/results/x0-default/` (committed),
`eval/baselines/setup/x0_kernel_diff.json` (committed); the detail files
`eval/baselines/confirm_x0-{records,default}/` are gitignored (`eval/.gitignore`,
`baselines/confirm*/`) and live in the `wt-x0` worktree only. `normal` partition, 8 shards each; every shard COMPLETED, no analysis timeout (the slowest
shard, P1 CC 1296n + crs-cuda, took 71 min on the records path and 64 min on the default,
on different nodes).

**`verdict_diff.py`** (verdict, reports_dedup, report_ids per (id, mode, rep)):

```
A: 130 rows  B: 130 rows  common: 130  only-A: 0  only-B: 0  differing: 0
identical verdict/report rows: 130
```
The `notes` column (where the `classes=` counts, `a2_uncertain=` and `gate_policy=` live) is
identical as well on all 130 rows. Verdicts on both paths: vector-clock 26 RACE / 35 CLEAN /
4 TIMEOUT, scalar-clock 25 / 36 / 4. The 4 TIMEOUT programs (P6-interkernel
`global_writewrite_race-racy`, P9-overlap, P7-bfs, P7-particlefilter) timed out at the 120 s
recording floor and have no verdict on either path.

**`x0_confirm_diff.py`** (every report object of every detail file, `raw` and `raw_sc`, keyed by
(a_pc, b_pc, space, race_type), every other field compared):

```
A: 122 detail files  B: 122  common: 122
differing detail files: 0; lost reports: 0
```

**Inside the 64 kernels above the cutoff** (`x0_kernel_diff.py`: `analyze()` on each kernel JSON
with the old production path — `CUVEIN_PREFER_RECORDS=1`, cutoff at 5 M — and with no
environment; all verdicts, not only reports):

| program | mode | kernels over | identical | what differs (old → new) |
|---|---|---|---|---|
| P4-1dconv-norace-large | both | 1 | 1 | — |
| P4-matrix-multiplication-norace-small | vector-clock | 1 | 1 | — |
| P4-matrix-multiplication-norace-small | scalar-clock | 1 | 0 | 7 → 11 ORDERED verdicts; event candidates `null` → 2 pairs judged; skipped edges 25 → 23; no report lost or gained |
| P6-hostdevice-global_writewrite_race-fixed | both | 1 | 1 | — |
| P6-interkernel-global_readwrite_race-racy | both | 1 | 1 | — |
| P7-backprop-cuda | both | 2 | 2 | — |
| P9-crs-cuda | both | 26 | 26 | — |

`== 64 kernels above the cutoff; 0 with a lost report`. The one kernel whose content changes
(`x0_mm_detail.py`) gains judgments, never reports. Cause: the old path, above the cutoff,
had no offline barrier pass in scalar-clock mode (class (c)), so (i) the two lock-protected
WAR edges `0x590→0x5a0` and `0x960→0x980`, whose last accessor was the writer's own thread,
were skipped as `intra_thread_only` with no event evidence to rescue them, and (ii) the
event-stream candidates were never generated. With `hb_sync_pass` both edges are rescued at
block distance and judged ORDERED (class SC), and the two same-pc WAW candidates `0x5a0`,
`0x980` are judged ORDERED. The program is CLEAN on both paths. Wherever a kernel above the
cutoff has RMWs (matrix-multiplication's block lock, both modes), R3's points now come from
`hb_rmw_points` instead of region dominance (`trace_rmw_points` returned None above the
cutoff on the old path). That moved no verdict in this store: the vector-clock kernel is
identical on both paths.

So, on this store: the new default never loses a report, has more information on exactly the
kernels above the cutoff, and moves no row. The brief's stop condition did not occur.

## 4. CLAUDE.md (step 6)

One A4 bullet (verdicts from the aggregates; the replay is the parity reference;
`CUVEIN_BARRIER_PASS_MAX_LANES` only for pre-T4 stores; a test or script that needs the
records asks for them) and a "Status 2026-10-13 — the code freeze (X0)" paragraph naming
`fce124c` before "Remaining order".

## 5. What remains unverified

- **Only the T20 parity store was re-scored** (65 programs, 6 of them with kernels above the
  cutoff). The evcand store, T4's long-cap stores and the other October stores are not
  re-scored under the new default. A pre-T4 store keeps the replay by construction
  (`use_aggregates` is False without the keys); that is read from the code and not run on a
  pre-T4 store here.
- The 4 × 2 TIMEOUT rows give no evidence either way.
- **`--timeout-cap` was not exercised in a GPU sweep.** I checked `--help` for both scripts,
  `py_compile`, and the formula's default (1200, so behaviour is unchanged), and I read the
  notes readers. A run with `--timeout-cap 5400` is X1's first job. Rows written since X0 by
  `parallel.py run` carry `cap=<s>;` at the head of their notes; no table reads it yet.
- `diagnostics.tv_violation` on the aggregates path is the dump's own `tv_violation` (HbClock
  writes it in both modes since T4). The offline `TV-barrier-pending-at-end` check inside
  `barrier_only_pairs` now runs only on the replay path. The field is informational (no
  verdict depends on it) and it is not in the CSV or the detail files, so the re-score does
  not compare it. `test_barrier_exit.py::test_offline_pass_matches_hb_clock` still checks
  the offline TV result against HbClock directly.
- The GPU tests' recordings are all below the cutoff. The equivalence above the cutoff rests
  on T20's parity (918 kernel JSONs, 64 above the cutoff, aggregates == records with the
  cutoff lifted; `eval/THREAD_INDEX.md` §2) and on §3 of this report. I did not rerun T20's
  parity.

Hardware: GPU work on c73 (`rtx4060ti16g`, RTX 4060 Ti 16 GB, sm_89, driver 580.82.07, CUDA
13.3). Re-scores and the kernel diff on `normal` nodes (c8–c19, c26, c47, c48, c59, c73,
c77–c79) reading BeeGFS.

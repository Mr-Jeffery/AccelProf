# Mode rename: vector-clock / scalar-clock (task T8)

Branch `rename/clock-modes` (worktree `/home/fzheng4/wt-T8`), based on `cuVein` @ `4898513`.
2026-09-23. Claude.md T8 brief, decision D3 (persisted strings migrate too).

**Status: done (2026-09-23).** Code, collector, converter, tests and docs were verified in
the worktree (§3); the three shared-state steps followed on the user's go-ahead (§4): the T8
engine library is installed in `build/sanalyzer/lib`, the branch is merged into `cuVein`
(`c6bad1a`, by the user), and every kept-trace store and confirm directory in home and on
BeeGFS carries the new names.

Legend: **measured** = a command ran and its output is quoted; **read from the code**;
**unverified**.

## 1. What changed

| what | before | after |
|---|---|---|
| collector switch | `YOSEMITE_HB_NO_ENGINE` set | `YOSEMITE_HB_MODE=scalar-clock` \| `vector-clock` (default `vector-clock` under `YOSEMITE_HB_TRACE=1`); the old variable still honoured with a deprecation warning, the new one wins when both are set, an unknown value warns and runs `vector-clock` |
| vocabulary | literals scattered over the harness | `python/hb_modes.py` (`MODES`, labels, `collector_env`, the compatibility readers, the library interlock) |
| setters | `blib.base_env(no_engine=)`, `driver.py --no-engine`, `YOSEMITE_HB_NO_ENGINE=1` in harness.sh / scale_harness.py | `base_env(hb_mode=)`, `driver.py --mode vector-clock\|scalar-clock` (default suffix `-scalar-clock`), `YOSEMITE_HB_MODE` only; an inherited `YOSEMITE_HB_NO_ENGINE` is scrubbed |
| `$BASELINE_MODES`, `run_cuvein.py --mode`, `parallel.py MODES` | `engine,trace-only` | `vector-clock,scalar-clock` (old names accepted with a warning) |
| CSV `mode` | `engine`, `trace-only` | `vector-clock`, `scalar-clock` |
| CSV `oracle_verified` | `no-engine` | `scalar-clock` |
| CSV `notes` | `mode=trace-only(no-engine)`, `no-engine-output(rc=N)` | `mode=scalar-clock`, `no-kernel-json(rc=N)` (§2) |
| disagreement CSVs | `cuvein/engine`, `cuvein/trace-only` | `cuvein/vector-clock`, `cuvein/scalar-clock` |
| result files | `E*-noengine.csv` | `E*-scalar-clock.csv` |
| kept-trace stores | `<id>/engine/`, `<id>/trace-only/`, `<mode>-partial-rep<k>/`, `logs/engine_rep1.txt`, `meta.modes` keys, `STORE_INFO.modes` | new names (converter written and dry-run; applying it is §4) |
| confirm files | `<id>__cuvein__engine.json`, `"mode"` | `<id>__cuvein__vector-clock.json` |
| `scale_harness.py` fields | `engine_races_dedup`, `t_dump_engine_s`, `engine_eq_oracle`, … | `vector_clock_*`, `t_scalar_clock_s`, `t_vector_clock_s` |
| tests | `test_scor_microbenchmark_trace_only`, `test_trace_only_verdict`, `_trace_only_copy` | `*_scalar_clock` |
| rendering | `cuVein (engine)`, `cuVein-eng`, `cuVein-tr` | `cuVein (vector-clock)`, `cuVein-VC`, `cuVein-SC` |
| prose | README, REPORT, FIX_REPORT, FP_DIAGNOSIS, HARDENING_REPORT, roadmap, STORAGE, setup/blockers.md, setup/tools.csv, docstrings | new names; "engine" kept where it names the HbEngine component |

Compatibility, one release (read from the code): every reader goes through
`hb_modes.canon` / `resolve_dir` / `resolve_confirm` / `canon_meta`, which accept the old
names and print one `DEPRECATED (pre-T8 mode names)` line per source; with
`CUVEIN_NO_LEGACY_NAMES=1` they raise instead. Nothing writes an old name.

Interlock (read from the code): every HB-trace setter calls
`hb_modes.require_collector_support`, which refuses to collect when the engine library the
collector loads (first RPATH entry of `lib/libcompute_sanitizer.so`) does not contain the
string `YOSEMITE_HB_MODE`. Without it, T8 code on a pre-T8 library would run the engine in
every scalar-clock run and file a vector-clock trace as scalar-clock. Measured: it raises
against the current live library (`build/sanalyzer/lib/libsanalyzer.so`, sha256[:16]
`26c4ea0cbea63590`).

Unchanged on purpose (not mode names): the `kernel_N.json` keys, `HbEngine` / `hb_engine_*`,
`barrier_only_pairs`, `hb_class` values, the E*.csv column names `t_trace` / `t_engine`, the
oracle state `engine-only` (engine result not cross-checked), the cause name `engine-hang`, and
`setup/engine_timeout_ids.txt` (referenced by the T5a/T5b briefs).

## 2. Deviations from the brief

- **`no-engine-output(rc=N)` became `no-kernel-json(rc=N)`, not `scalar-clock-output(rc=N)`.**
  `driver.py` wrote it whenever the analyzed run left no kernel JSON, in either mode: 16 of its
  24 occurrences are in vector-clock files (`E0.csv` 2, `E2.csv` 10, `E2-fixed.csv` 4;
  `E2-noengine.csv` 8). The brief's name would have labelled those vector-clock rows
  scalar-clock. `no-kernel-json(rc=N)` is `parallel.py`'s existing name for the same condition.
- `driver.py --no-engine` was removed rather than kept as an alias; `--mode` replaces it.
- Four notes quoting OS errors (`No space left on device: '/mnt/local/.../trace-only/...'`) keep
  their original text: they record paths of node-local directories that no longer exist.

## 3. Verification (measured)

Hardware: GPU work on c20 (`rtx4060ti8g`, RTX 4060 Ti, cc 8.9, sm_89 GPU pinned with
`setup/pin8g.sh`); CPU work on `normal`-partition nodes (c0, c4, c16, c36 and others). Detector runtime for the
"after" runs: the T8 worktree, whose `lib/libcompute_sanitizer.so` is a private copy relinked
from the existing nv-compute objects with its RPATH on the T8 `libsanalyzer.so`
(`setup/t8_relink.sh`): same NEEDED list and same exported symbols as the live collector. The
shared `build/sanalyzer/lib` was not modified.

### 3.1 Engine library build
`setup/t8_build.sh` (job 287209, c70): GCC 12.4.0 (`/opt/ohpc/pub/compiler/gcc/12.4.0`, the
compiler of the live library), `-g -O3 -mtune=znver4`, same include/RPATH as `bin/build`.
DW_AT_producer of the live library: `GNU C++17 12.4.0 --param=l1-cache-size=48
--param=l1-cache-line-size=64 --param=l2-cache-size=1024 -mtune=znver4 -march=x86-64 -g -O3`;
of the T8 library: `GNU C++17 12.4.0 -mtune=znver4 -march=x86-64 -g -O3` (the cache `--param`s
come from `-mtune=native` on the original build host). Exported symbol sets identical; size
14 921 064 → 14 936 072 bytes. `FIX_REPORT.md`'s conda compiler path no longer exists.

### 3.2 Collector: before vs after (jobs 287220 before, 287221 after; c20)
`setup/t8_collector_check.sh` ran three programs twice each under five configurations;
`setup/t8_collector_compare.py` → `setup/t8_check/collector-compare.txt`: **ALL CHECKS PASS**.

| check | race_interblock_none-lock_rtraw, norace_interblock_atom | 1dconv_norace |
|---|---|---|
| default tool path (no `YOSEMITE_HB_TRACE`), before vs after | identical | identical after renaming device addresses by rank and dropping per-edge `dist` histograms |
| vector-clock dump, old library vs `YOSEMITE_HB_MODE=vector-clock` | identical | equal modulo schedule order, engine race records compared as (pc pair, kind, space) sets |
| scalar-clock dump, old `NO_ENGINE=1` vs `YOSEMITE_HB_MODE=scalar-clock` | identical | equal modulo schedule order |
| `YOSEMITE_HB_NO_ENGINE=1` vs `scalar-clock` (after) | identical | equal modulo schedule order |
| `YOSEMITE_HB_MODE=bogus` vs `vector-clock` (after) | identical | same as the vector-clock row |
| hb_races present in vector-clock, absent in scalar-clock | yes | yes |
| deprecation / unknown-value warning where expected, no `[cuVein]` line elsewhere | yes | yes |

The 1dconv relaxations are the program's own run-to-run variation, measured with a single
library: its two repetitions differ exactly (device addresses; `dist` histograms; event and race
order), agree modulo schedule order in scalar-clock mode, and agree at the pc-pair level in
vector-clock mode, before and after alike. Device allocation addresses move between runs.
Read from the code: the changed C++ is reached only inside the `_hb_trace` branches.

### 3.3 Green set (job 287228, c20, from the T8 worktree runtime)
```
rm -rf ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py
136 passed, 1 xfailed, 8 warnings in 154.71s
XFAIL python/test_atomic_memory_model.py::test_relaxed_handoff_should_race - KNOWN UNSOUND (Phase 2)
```
39 renamed `*_scalar_clock` tests collected and passed. Engine library in use:
`/home/fzheng4/wt-T8/sanalyzer/t8_install/lib/libsanalyzer.so`.

### 3.4 Converter
- Fixture (228 MB copied from real CSVs, stores, confirm files): the dry run changes nothing
  (file list and md5s identical), a second `--apply` finds nothing, forward then `--reverse`
  restores every file name and every file in the harness's own formats byte for byte.
- `eval/results` (commit `665150a` + `da9e9dc`, logs `setup/migrate_logs/results.*.txt`): 600
  CSVs rewritten + 2 after the T0 follow-up merge, 8 `E*-noengine.csv` renamed, 0 conflicts;
  a further dry run finds nothing. Every rewritten CSV keeps its line count.
- Private BeeGFS copies of home `confirm/` and `traces_keep/` (job 287233,
  `setup/migrate_logs/stores.private-copy.apply.txt.gz`): 248 program dirs, 352 dirs, 1 392
  logs and 9 344 confirm files renamed, 248 `meta.json` rewritten, 0 conflicts; the dry run
  after it finds nothing.
- All real stores, **dry run only** (`setup/t8_stores_dry.sh`,
  `setup/migrate_logs/stores.dry.txt.gz`): 12 stores (6 home `traces_keep*`, 6 BeeGFS
  `cuvein_traces/*`), 1 510 program dirs; would rename 2 137 dirs, 7 652 logs, 15 113 confirm
  files; rewrite 1 489 `meta.json`, 56 `PARTIAL` markers, 5 `STORE_INFO.json`; **0 conflicts**.

### 3.5 Tables identical up to labels
`setup/t8_compare_reports.py` maps the new labels back to the old ones and compares line by
line (runs of blanks collapsed: fixed-width columns widen with the labels).

1. `make_tables.py` under `CUVEIN_NO_LEGACY_NAMES=1` on the migrated committed CSVs, against the
   pre-T8 reports on `cuVein` (`setup/t8_check/compare_reports.committed.txt`):
   `eval/BASELINES.md` (7 525 lines) and `eval/BASELINES_SUMMARY.md` (45 lines) **identical up
   to labels, in order**. Before any change, the unchanged worktree had reproduced both
   committed reports byte for byte.
2. The whole `p_final2` analysis chain, BEFORE = pre-T8 code on pre-T8 data (T0 worktree, tree
   == `cuVein`), AFTER = T8 code on the migrated copies under `CUVEIN_NO_LEGACY_NAMES=1`
   (`setup/t8_check/chain.txt`, `compare_reports.chain.txt`): `baselines-diagnose.csv` (49
   lines), `baselines-disagreements.csv` (36 841), `baselines-fp-causes.csv` (286) and the
   `compare_fpfix.py` output (35) **identical up to labels**; every script rc 0, no legacy name
   met. Found on the way: `classify_endpoints.py` writes its rows in `glob()` order, so even the
   pre-T8 code does not reproduce the committed `baselines-disagreements.csv` byte for byte (same
   36 841 rows, other order). The committed migrated CSV was therefore kept, not replaced.

Three pre-T8 behaviours had to be preserved: `sorted()` over mode names reorders
(`scalar-clock` < `vector-clock` but `engine` < `trace-only`) in `classify_endpoints`
(tool_a/tool_b columns), `classify_fp_causes`, `compare_fpfix` and four `make_tables` tables; all
now order by the harness mode order.

### 3.6 Fresh five-program run (job 287234, c20, T8 runtime)
`setup/t8_fresh.sh`, store `cuvein_traces/t8-fresh`, `eval/results/t8-fresh/`:
rtraw RACE/RACE, canary RACE (vector-clock) / CLEAN (scalar-clock, by design), norace_interblock_atom
and 1dconv CLEAN/CLEAN, graph-coloring-large TIMEOUT (vector-clock, partial dump kept as
`vector-clock-partial-rep1/`) / CLEAN. Only new names were written: CSV `mode`, `<id>/vector-clock/`,
`<id>/scalar-clock/`, `logs/vector-clock_rep1.txt`, `meta.modes`, `partial_dump`,
`STORE_INFO.modes`, `__cuvein__<mode>.json`; a grep for the old names in all outputs finds nothing.

### 3.7 Acceptance grep
```
grep -rn "trace-only\|no-engine\|noengine\|NO_ENGINE\|engine mode" --include=*.py --include=*.sh \
    --include=*.md --include=*.cpp --include=*.h --include=*.cu .
```
Remaining hits: the compatibility shim and its notes (`python/hb_modes.py`, the collector's
parse function, `migrate_mode_names.py`, two comments in `parallel.py`, `eval/README.md`,
`eval/STORAGE.md`'s header note), the T8 check scripts that exercise the old names on purpose
(`setup/t8_collector_check.sh`, `t8_collector_compare.py`, `t8_compare_reports.py`,
`t8_fresh.sh`), and `eval/baselines/store_index/inventory.md`, which is generated from the
stores and is regenerated after they are migrated (§4c).

## 4. Shared-state steps (done 2026-09-23, on the user's go-ahead)

Order: the pre-T8 code reads only the old store names, and the T8 code refuses to collect with
a pre-T8 library, so the library went first, then the merge, then the stores.

a. **Engine library installed** 11:31 (`build/sanalyzer/lib/libsanalyzer.so`, sha256[:16]
   `785d27a28b6456c5`; the previous one kept as `libsanalyzer.so.pre-t8`, `26c4ea0cbea63590`).
   The first attempt (the user's three `!` lines) did nothing: each line ran in its own shell,
   so `L` was empty; the same commands then ran in one shell.
b. **Merged** by the user: `c6bad1a` (`git merge --no-ff rename/clock-modes`, message edited in
   vi; its subject line accidentally carries the store-migration command). Its tree is identical
   to the branch tree (`ab8ebd8…`). While that merge was writing files, a failed merge attempt of
   mine was mistaken for its wreckage and the checkout was partly reset; after the user saved the
   commit, the working tree was resynced to it (`git reset --hard HEAD`, after checking that the
   tracked files were byte-identical to the old `cuVein` and every untracked file byte-identical
   to the merge commit).
c. **Stores migrated** (job 287762, c8, 2 991 s; log `setup/migrate_logs/stores.apply.txt.gz`):
   12 stores (6 home `traces_keep*`, 6 BeeGFS `cuvein_traces/*`), 1 510 program dirs, all home
   `confirm*` dirs: 2 137 dirs, 7 652 logs, 15 113 confirm files renamed; 1 489 `meta.json`, 56
   `PARTIAL`, 5 `STORE_INFO.json` rewritten; 0 conflicts; exactly the dry run's numbers; a second
   pass finds nothing. `store_inventory.py` under `CUVEIN_NO_LEGACY_NAMES=1` then read every
   store without meeting an old name; per-store program and loss counts are unchanged
   (`eval/baselines/store_index/inventory.md`).
d. **Green set from the main checkout** at `c6bad1a` with the installed library (job 287761,
   c20): 136 passed, 1 xfailed.
e. **Revision re-pinned** (`setup/cuvein_rev.sh t8-2026-09-23` → `setup/cuvein_rev.status`): HEAD
   `c6bad1a`, empty working-tree diff, engine library `785d27a28b6456c5`, OK. Its freshness
   check compares modification times only; git's rewrite of `pc_dependency_analysis.cpp` during
   the merge made the file look newer than the library, so the file got back the modification
   time of its build input (`touch -r`, after `cmp` showed the two byte-identical and
   `git diff 94cbf5e HEAD -- sanalyzer/` was empty).

Rollback, if ever needed: the stores with `migrate_mode_names.py --results '' --store … --confirm
… --reverse --apply`; the library by copying `libsanalyzer.so.pre-t8` back; the code with git.

## 5. What remains unverified
- The T8 library under the real harness on the full corpus: verified on 3 programs × 5
  configurations, the green set (33 ScoR micro-benchmarks + canary + coherent/barrier/atomic
  litmus) and 5 harness programs, all on sm_89.
- The T8 library's behaviour on other architectures (sm_86, sm_120, sm_90): not run.
- `driver.py` / `harness.sh` end to end (the E-series harness): changed and compiled, not run
  (`driver.py` carries a stale CUDA_HOME from before this task).
- `scale_harness.py`: changed and compiled, not run.

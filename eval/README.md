# cuVein race-detector evaluation harness

Reproducible evaluation of the `cuVein` scoped happens-before data-race detector across
the ScoR micro/app suites, cuHadron, HeCBench, Indigo3, ECL, and the Compute-Sanitizer
baseline. Results land in `eval/results/*.csv`; the write-up is `eval/REPORT.md`.

## Layout
```
eval/
  driver.py          orchestrate one program: extract CFG + atomic sidecar, time
                     native/trace/engine, poll peak RSS, then aggregate -> CSV row
  aggregate.py       pair each kernel_N.json with its aligning CFG dot, run
                     sync_dominance, dedup RACE reports, cross-check hb_oracle
  summarize.py       confusion counts + precision/recall/specificity from a CSV
  triage.py          per-report breakdown of a detail JSON (space/class/chain)
  mkmanifest.py      manifest from executables in a dir (label by prefix)
  mk_e0_manifest.py  E0 (ScoR apps) manifest: 7 benches x {norace,racy} x sizes
  mk_e2_manifest.py  E2 (cuHadron) manifest from built binaries
  build_scor.py      build the 7 ScoR apps for sm_86, both RACEY variants
  build_cuhadron.py  build cuHadron for sm_86, both FIXED variants
  gen_scor_input.py  deterministic stdin inputs for the ScoR apps
  racecheck.py       E6a: Compute Sanitizer racecheck baseline (shared mem only)
  manifests/*.json   what was run
  results/*.csv      the eval rows (committed)
  detail/*.json      per-program verdict detail (gitignored)
  inputs/*.in        generated app inputs (gitignored)
  bin/E0, bin/E2     built benchmark binaries (gitignored)
```

## Environment (uncommitted fixups)
The detector runtime lives in the main checkout (`ACCEL_PROF_HOME=/home/fzheng4/AccelProf`);
the harness runs against it. Two fixups (kept out of git, in `.env/` and `setup_env.sh`):
- `.env/bin/python` symlinked to the py310 env that carries networkx 3.2.1 + pydot;
- `setup_env.sh` exports `LD_LIBRARY_PATH` with `$CUDA_HOME/compute-sanitizer` and the
  py310 `lib` (for `libpython3.10.so.1.0`, pulled in by `libcompute_sanitizer.so`).

## Run
```
CONDA="conda run -p /home/fzheng4/AccelProf/.env python"

# E5 microbench litmus
$CONDA eval/mkmanifest.py --suite E5-micro --dir /abs/ScoR/microbenchmarks/bin \
    --label-rule race_:racy,norace_:race-free --oracle --out eval/manifests/e5_micro.json \
    --csv eval/results/E5-micro.csv --detail-dir eval/detail
$CONDA eval/driver.py eval/manifests/e5_micro.json
$CONDA eval/summarize.py eval/results/E5-micro.csv

# E0 ScoR apps
$CONDA eval/build_scor.py --bench-dir /abs/ScoR/benchmarks --out eval/bin/E0
$CONDA eval/gen_scor_input.py --out eval/inputs
$CONDA eval/mk_e0_manifest.py --bin eval/bin/E0 --inputs eval/inputs --sizes small \
    --out eval/manifests/e0_small.json --csv eval/results/E0.csv --detail-dir eval/detail
$CONDA eval/driver.py eval/manifests/e0_small.json

# E2 cuHadron
$CONDA eval/build_cuhadron.py --dir /abs/cuHadron --out eval/bin/E2
$CONDA eval/mk_e2_manifest.py --bin eval/bin/E2 --out eval/manifests/e2.json \
    --csv eval/results/E2.csv --detail-dir eval/detail
$CONDA eval/driver.py eval/manifests/e2.json
```

## Trace-only mode (no in-process engine)
`driver.py MANIFEST --no-engine --csv-suffix=-noengine --detail-suffix=-noengine` runs
native + `YOSEMITE_HB_TRACE=1 YOSEMITE_HB_NO_ENGINE=1` only and analyzes that dump: verdicts
come from the static leg (R1/R2/R3 over the trace's pc edges; every RACE is `latent`, there
is no `hb_races`), `t_engine` is blank, `peak_mem` is the tracing run's, `oracle_verified`
= `no-engine`. Results land next to the engine-mode CSVs as `*-noengine.csv`. (Use the
`--opt=value` form: a suffix starting with `-` is otherwise parsed as a flag.)

## Re-analyzing existing traces / running from a worktree
- `eval/reanalyze.py --bindir eval/bin/E0 --python-dir python <stems>` re-runs the static
  leg + aggregation on already-recorded traces (no GPU) — validates `sync_dominance` changes
  in seconds. `--assume-warp-lockstep` forwards the opt-in filter.
- `CUVEIN_HOME=<checkout>` makes `driver.py` use that checkout's `bin/ lib/ .env/ python/`.
  A worktree becomes a full runtime mirror by symlinking the gitignored `lib build .env
  nv-compute/lib ScoR cuHadron` to the main checkout; the rebuilt engine must install into
  the RPATH location `build/sanalyzer/lib` (see `sanalyzer` Makefile `INSTALL_DIR`, and pass
  `CXX=` the conda compiler the existing build used).
- Run the pytest with the env's python directly (`.env/bin/python -m pytest …`), **not**
  under `conda run`: `getall.sh` calls `conda run` for the atomic-scope sidecar and a nested
  `conda run` fails silently — the engine then has no atomic scopes and every atomic looks
  like a plain access. Wipe `ScoR/microbenchmarks/artifacts/*` first so traces regenerate.

## Notes
- `-n 1` single-worker replay is required (cross-thread edge direction is temporal only then).
- The atomic-scope sidecar (`YOSEMITE_ATOMIC_SCOPE_FILE`) is mandatory — without it the
  engine loses atomic-coherence ordering and over-reports.
- `oracle=false` (engine-only) for many-kernel real apps: the exact VC oracle is O(threads)
  per conflict and impractical there; engine==oracle equivalence is established on the 33
  ScoR litmus programs + the canary.
- Run one GPU batch at a time; kill stragglers by PID (a wrapped `conda run` can outlive
  `pkill -f driver.py`).
```

## False-positive diagnosis and the post-fix re-run
- `eval/FP_DIAGNOSIS.md` explains the head-to-head false positives; regenerate the attribution with
  `python3 eval/baselines/classify_fp_causes.py` (→ `eval/results/baselines-fp-causes.csv`, rendered by
  `make_tables.py` as "false positives by report class and root cause").
- Detector knobs introduced by the fixes: `--strong-ldst {generic,all,none}` / `$CUVEIN_STRONG_LDST`
  (which `.STRONG` loads/stores are language-level atomics; read by `sync_dominance.py`,
  `hb_oracle.py`, `atomic_scope_sidecar.py`), `YOSEMITE_HB_NO_SYNC_ONLY=1` (disable the engine's
  barrier-only second clock; `barrier-ordered` then degrades to `latent`).
- `sbatch eval/baselines/setup/p_fpfix.sh` re-runs P1–P6 with the current detector into
  `eval/results/fpfix/`, `eval/baselines/confirm_fpfix/`, `eval/baselines/traces_keep_fpfix/` (the merged
  baseline is untouched); `python3 eval/baselines/compare_fpfix.py` prints before/after FP/TP and
  lists any true positive lost.
- `CUVEIN_EVENT_CANDIDATES=0` / `--no-event-candidates`: judge trace edges only. By default the
  conflicting pc pairs that only the `hb_events` stream shows (engine `hb_races_sync_only` +
  `hb_races`; trace-only: the offline barrier pass) are judged too — a trace edge keeps just the
  LAST accessor of a location, so a pair can have no edge at all. `CUVEIN_R3_PAST_RELEASE=0`
  disables R3's past-release gate (an access after its thread's own unlock of a CAS-acquired lock
  is not ordered by the lock hand-off). Both exist for ablation on identical traces.
- Storage (T0, `eval/STORAGE.md`): every trace store lives on BeeGFS,
  `BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>` (127 TB shared FS, no quota,
  ~450 MB/s per node; mounted on every compute node, NOT on the login node; not backed up).
  `parallel.py run` keeps EVERY program's trace there (`<id>/{meta.json,dots/,logs/,
  <mode>/kernel_*.json}`, `STORE_INFO.json` = collector build), with no size cap
  (`--keep-all-cap-gb 0`), and a timed-out rep's partial dump under
  `<id>/<mode>-partial-rep<k>/` (marked `PARTIAL`, never a verdict). `_store_root()` refuses
  any other location (`/mnt/local`, `/tmp`, home): the pre-T0 fall-through is what filled
  node-local disks and the 40 GB home quota. `--delete-traces` restores the old lean mode.
  Result CSVs and confirm JSONs still go to home; `store_inventory.py` mirrors every
  store's `STORE_INFO.json`/`meta.json` into `eval/baselines/store_index/<tag>/` (home) and
  lists what each store lacks. Re-score a store on CPU nodes with
  `TAG=<tag> sbatch eval/baselines/setup/p_analyze_cpu.sh` (`parallel.py analyze` never
  touches CUDA); `setup/p_evcand.sh` + `setup/p_evcand_base.sh` +
  `compare_fpfix.py --before 'eval/results/evcand_base/*.csv' --after-glob 'eval/results/evcand/*.csv'`
  is the worked example.
- A cuVein rep is a verdict only if the app reached its own exit status under the tool
  (`rc == native rc`). An app killed mid-run (OOM under the engine: accelprof rc 1) leaves the
  kernels dumped so far; such a rep is `ERROR incomplete-trace(rc;nkernels;peak_mb)` — or RACE
  `partial` when the prefix already shows a race — never CLEAN. `events=`/`nkernels=` in the
  notes are that mode's own dump. `make_tables.py`/`compare_fpfix.py` re-score older rows the
  same way (FP_DIAGNOSIS.md, addendum).

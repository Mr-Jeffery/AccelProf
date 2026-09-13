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

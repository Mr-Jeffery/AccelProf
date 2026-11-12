# Four tools on the stream-K reproducer (X9 finding `streamk-wait-eq-reset`)

Read-only test in X9's checkout (`~/wt-x9`, branch `eval/cutlass-races`). Nothing in `python/`, `sanalyzer/`, `nv-compute/`,
`bin/` or `hb_oracle.py` changed; no runtime rebuild; nothing pushed. Jobs: 340757 (GPU, `rtx4060ti16g`, node c3, RTX 4060 Ti
sm 8.9, driver 615.71.09, COMPLETED 00:01:46) and 340758 (`normal`, c3, the S2 verdict layer re-run, see Setup). Cap 1,200 s
per run; no run came near it.

**The race's pair** (dossier `findings/streamk-wait-eq-reset.md`):
- split 2 (cooperative finisher): producer's partial store `block_striped.h:194` (peer, ← `gemm_universal_streamk.h:772`) ×
  consumer's partial load `functional.h:134` ← `block_striped.h:181` ← SK:813, after `wait_eq_reset` at SK:809.
- split 3 (separate reduction): producer's partial store `block_striped.h:194` ← SK:989 × reduction block's load
  `block_striped.h:165` ← `epilogue_base_streamk.h:133/144`, after `wait_eq_reset` at SK:885.
- **The flag:** `barrier.h:175` (`atomicCAS` spin, `ATOMG.E.CAS.STRONG.GPU`) and `barrier.h:124` (`red.relaxed.gpu`,
  `RED.E.ADD.S32.STRONG.GPU`).

## Result

| variant | racecheck | iGUARD | cuRace (S2, no clock) | cuRace + scalar clock |
|---|---|---|---|---|
| stock, split 2 | none (0 hazards; 0.5 s) | **pair** (64 reports at the consumer's load `functional.h:134`; also 2 at the flag, `barrier.h:175`, `:124`; 3/3 reps identical; 0.42–0.57 s/rep) | **pair** (64 DR RAW `block_striped.h:194` × `functional.h:134`) + other: 148 shared-memory DR at `memory_sm75.h:244`, `regular_tile_iterator_pitch_linear.h:193`, `tile_iterator_simt.h:207` (record 1.0 s, verdict 2.1 s) | **pair** (64 DR RAW `block_striped.h:194` × `functional.h:134`; nothing else) (record 8.5 s, verdict 1.7 s) |
| stock, split 3 | none (0 hazards; 0.5 s) | **pair** (6 reports at the reduction load `block_striped.h:165`; also 2 at the flag; 3/3 reps identical; 0.42 s/rep) | **pair** (48 DR RAW `block_striped.h:194` × `block_striped.h:165`) + other: 52 shared-memory DR at `memory_sm75.h:244`, `regular_tile_iterator_pitch_linear.h:193` (record 1.2 s, verdict 1.3 s) | **pair** (48 DR RAW `block_striped.h:194` × `block_striped.h:165`; nothing else) (record 1.0 s, verdict 1.4 s) |
| fixed, split 2 | none (0 hazards; 0.5 s) | **pair** (64 reports at `functional.h:134`, same 64 offsets each rep, labelled "Missing gpufence" or "Missing lock" (40/26, 37/29, 59/7 by rep); also 2 at the flag; 0.42 s/rep) | **pair** (64, as stock) + other: 148 shared-memory DR, the same sites as stock (record 0.9 s, verdict 1.5 s) | **pair** (64, as stock) (record 1.0 s, verdict 1.3 s) |
| fixed, split 3 | none (0 hazards; 0.5 s) | **pair** (6 reports at `block_striped.h:165`, kinds 4/4, 5/3, 3/5 gpufence/lock by rep; also 2 at the flag; 0.42 s/rep) | **pair** (48, as stock) + other: 52 shared-memory DR, as stock (record 0.8 s, verdict 1.4 s) | **pair** (48, as stock) (record 0.9 s, verdict 1.4 s) |

No cell is TIMEOUT. Every cuRace report is a DR (`conflict_class`); none is SC. iGUARD reports single accesses, not pairs: a
"pair" cell for iGUARD means its reports sit at the consumer's partial load. iGUARD reports no access at the producer's
partial store `block_striped.h:194` in any variant. Native runs: 4/4 PASS (`max_err=0`).

**Two lines.**
- **iGUARD on stock:** reports at the race's pair in both splits (split 2: 64 reports at the consumer's load `functional.h:134`; split 3: 6 at `block_striped.h:165`; kind "Missing gpufence"). It also reports the flag (`barrier.h:175` CAS, `barrier.h:124` RED), but not only the flag.
- **Fixed builds:** three of the four tools report on both fixed builds, all at the same pair as on stock: iGUARD, cuRace (S2) and cuRace + scalar clock. racecheck reports on none of the 8 runs. iGUARD's fixed-build reports are at the same offsets as stock; its kind alternates between "Missing gpufence" and "Missing lock" from rep to rep. cuRace's fixed-build reports are identical to stock (the S1a elected-thread limitation, X9 §3). S2's extra shared-memory reports also appear on both stock and fixed.

## Attribution

Source lines come from `nvdisasm -c --print-line-info-inline` on the cubins that `cuobjdump -xelf all` extracts from each
executable (`runs/repro.lineinfo.txt`, `runs/repro_fixed.lineinfo.txt`; one kernel function,
`cutlass::Kernel2<…ThreadblockSwizzleStreamK…>`). An offset takes the frames of the line-info block above its instruction.

- **Check against cuRace.** For every cuRace pair, the innermost frame agrees with the harness's own `pc_lines` on both
  ends (0 mismatches over all 848 records).
- **iGUARD offsets.** iGUARD prints `Sass offset N` (no source line) and is mapped the same way.

Classification (`eval/cutlass/harness/x9_tools_attr.py`, output `eval/cutlass/tools_streamk/attribution.tsv`), by innermost frame:
- **PAIR-STORE:** `block_striped.h:194`, `functional.h:943/963/992`
- **PAIR-LOAD:** `functional.h:134/177/202`, `block_striped.h:165`
- **FLAG:** any frame in `barrier.h`
- **OTHER:** everything else

iGUARD's flag reports, with their full frames:
- `ATOMG.E.CAS` at `device_atomic_functions.hpp:202` ← `barrier.h:175` ← SK:809 (split 2) or SK:885 (split 3)
- `RED.E.ADD` at `barrier.h:124` ← `barrier.h:191/198` ← SK:794 (split 2), or ← `barrier.h:208/215` ← SK:992 (split 3)

cuRace S2's "other" reports are shared-memory pairs of the mainloop: the tile store `regular_tile_iterator_pitch_linear.h:193`, the `memory_sm75.h:244` access, and the warp tile load `tile_iterator_simt.h:207`. They are absent from the scalar-clock run of the same binary. I have not triaged them.

## Setup and exact commands

- **Build.** `findings/streamk-wait-eq-reset/build.sh` (unchanged), into `/mnt/beegfs/fzheng4/cutlass/tools_streamk/build`:
  - flags `nvcc -arch=sm_89 -lineinfo -std=c++17 -O3 -cudart shared` (CUDA 13.3), CUTLASS v4.8.1
  - `repro_fixed` = `fix.patch` overlay of `barrier.h` (`fence.acq_rel.gpu` after the CAS spin)
  - SASS check from the build log: CAS→`MEMBAR.ALL.GPU` within 6 instructions is 0 in `repro`, 2 in `repro_fixed`
- **Variants.** Manifest `eval/cutlass/tools_streamk/manifest.csv`, ids `x9tools-{stock,fixed}-s{2,3}`. Command `<exe> 1 2` or `<exe> 1 3`: 1 rep, one split. Split 2 runs 34 blocks on the cooperative-finisher path; split 3 runs 66 blocks, 32 of them reduction blocks.
- **Job scripts.**
  - `eval/cutlass/harness/x9_tools_streamk.sh` (GPU): build, native, racecheck, iGUARD, both recordings, scalar-clock verdict
  - `eval/cutlass/harness/x9_tools_s2.sh` (`normal`): the S2 verdict layer
- **racecheck.**
  ```
  compute-sanitizer --tool racecheck --racecheck-report all --print-limit 10000 <exe> 1 <split>
  ```
- **iGUARD.** The install is `/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so`: iGUARD 3eb5003 on NVBit 1.8, `ARCH=sm_89` (`setup/iguard.status`). The runner is `eval/baselines/run_iguard.py`, the one behind every iGUARD row in the repo (`p_iguard.sh` P1–P6, `p_pi_iguard.sh` PI, `p_sc_others.sh` P8/P9).
  - Command:
    ```
    BASELINE_TRACE_DIR=$CB/tools_streamk/iguard_logs IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so \
      $PY eval/baselines/run_iguard.py --manifest eval/cutlass/tools_streamk/manifest.csv --id <id> --out <csv>
    ```
  - Inside the runner: `LD_PRELOAD=iguard.so`, `TIMEOUT=0` (iGUARD's own timeout off), 3 reps (the runner default, as in those jobs).
  - Per-rep timeout is `min(max(10×native,120),1200)`, which comes to 120 s here.
  - NVBit defaults as printed: `BYTE_GRAN=4 CHECK_LOCKS=1 CHECK_ITS=1 CONT_OPT=1 MD_SCALE=1 MANAGED=1`.
- **cuRace + scalar clock.** The same recording and verdict path as X9's reproducer runs (harness of this checkout, installed runtime f551ca0, hashes checked by `x9_env.sh`).
  - Record:
    ```
    BASELINE_MODES=scalar-clock YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16 BASELINE_HB_DUMP=0 \
      x9_collect.py collect --manifest <M> --id <id> --reps 1 --timeout-floor 1200 --timeout-cap 1200
    ```
  - Verdict:
    ```
    parallel.py analyze --manifest <M> --id <id> --confirm --analysis-timeout 1200
    ```
- **cuRace S2.** S2 (`--chain-closure --co-async --co-r3 off`) is **not in this checkout**: `parallel.py` here has no such flags, because the branch was cut from `eval/co-offline`. I did not merge or patch it in.
  - **Recording.** Made with this checkout's harness in collector-only mode, C1's way (`BASELINE_MODES=collector-only`, no `YOSEMITE_HB_*`):
    ```
    BASELINE_MODES=collector-only x9_collect.py collect --manifest <M> --id <id> --reps 1 --timeout-floor 1200 --timeout-cap 1200
    ```
  - **Verdict layer.** Run from a read-only export of `origin/eval/co-chain-b` f31a5067:
    ```
    git archive f31a5067 python eval/baselines eval/*.py | tar -x -C /mnt/beegfs/fzheng4/cutlass/tools_streamk/s2export
    ```
    Then, with `ACCEL_PROF_HOME=CUVEIN_HOME=<export>` and `BASELINE_MODES=collector-only` (the form of `c6b_retime.sbatch`'s `co-s2` line):
    ```
    <export>/eval/baselines/parallel.py analyze --manifest <M> --id <id> --confirm \
      --chain-closure --co-async --co-r3 off --analysis-timeout 1200
    ```
    The rows' notes confirm the switches: `chain=1 … co_async=1;co_r3=off`.
  - **Two attempts.** Job 340757's export lacked `eval/aggregate.py` (`ModuleNotFoundError`, all 4 S2 cells rc 1 in 0.2 s). Job 340758 re-exported with `eval/*.py` and re-ran only the verdict layer on 340757's recordings.
- **Wall times.** Per step in `eval/cutlass/tools_streamk/runs/times.tsv`; recording walls in `runs/meta-*.json`.

## Production-set scoring: what was matched, and what was not

- **No "production set" label.** Neither the repo nor the paper (`cuRacePaper`) has one. The paper's real-world study (`evaluation.tex:17`) is C2's / T21b's real-world harness (`eval/COLLECTOR_ONLY_REALWORLD.md`, on `eval/co-chain-b`).
  - That harness's policy: one rep, `--confirm`, tool cap 1,200 s, analysis timeout 3,600 s, atomic-scope sidecar, `accelprof -n 1`; scalar-clock recorded with `BASELINE_HB_DUMP=0`.
  - These runs follow it, except that the analysis timeout is 1,200 s (the brief's cap). No analysis came close: the longest took 2.1 s.
- **S2 was never applied to the real-world rows.** `CO_CHAIN_B.md` §7 says those rows were "not re-analysed at S1 or S2". The S2 command above is the one used for the 4,709-program corpus.
- **No iGUARD run on the real-world set.** I found none in the repo (no iGUARD file in `eval/realworld/`). The iGUARD command above is the runner and install of every iGUARD row that does exist.

## Files

- `eval/cutlass/tools_streamk/`:
  - `manifest.csv`
  - `attribution.tsv`
  - `runs/` (racecheck, iGUARD rep logs, native, collect/analyze logs, meta, line info, `times.tsv`)
  - `confirm/{scalar-clock,s2}/`
- `eval/results/cutlass/tools_streamk/`:
  - `iguard-<id>.csv`
  - `scalar-clock/`
  - `s2/`
- Logs: `eval/x_logs/x9-tools-340757.log`, `x9-tools-s2.log`. Recordings: `/mnt/beegfs/fzheng4/cutlass/tools_streamk/traces/`.

## Not determined

- **What S2's 148/52 shared-memory reports are** (mainloop tile store/load pairs, present on stock and fixed alike): not triaged.
- **Why iGUARD labels the same offsets "Missing lock" on some reps of the fixed builds.** The stock builds always get "Missing gpufence". Not investigated beyond counting.
- **Whether the paper's production rows used a different iGUARD flag set.** The repo shows none; see above.

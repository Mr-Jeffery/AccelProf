# Trace storage: BeeGFS as the only store (task T0)

Branch `infra/beegfs-store`, 2026-09-22. Base revision `cuVein` @ `b7d463e`. Detector code
(`python/`, `sanalyzer/`, `bin/`, `nv-compute/`) is untouched by this task; only the
evaluation harness (`eval/baselines/`), its sbatch scripts and the docs change.

Legend for every claim below: **measured** (a command ran, output quoted), **read from the
code** (file:line), **unverified**.

## 1. Policy

1. Every trace store is a directory under `/mnt/beegfs/$USER/cuvein_traces/<tag>`.
   `parallel.py` refuses any other location (`_store_root()`, `eval/baselines/parallel.py`):
   `$BASELINE_TRACE_DIR` unset → `/mnt/beegfs/$USER/cuvein_traces`; set to something outside
   `/mnt/beegfs/$USER` → exits with a message; `/mnt/beegfs` not mounted (login node) → exits
   with a message. `BASELINE_TRACE_ALLOW_NONBEEGFS=1` is the only way to use another
   directory and prints a warning (throw-away local tests).
2. `parallel.py run` keeps **every** program's trace in the store (the pre-T0 `--keep-all`
   is now the default and still accepted; `--delete-traces` restores the old lean mode). No
   size cap: `--keep-all-cap-gb` defaults to 0 = unlimited; `--keep-cap-mb 0` makes the
   `--keep-mismatch` home copy unlimited too (default there stays 300 MB because home has a
   40 GB quota).
3. A timed-out rep's partial dump is kept under `<id>/<mode>-partial-rep<k>/` with a
   `PARTIAL` marker file (the rep's meta + "never a verdict"); one per mode, the rep with
   the largest raw dump wins. `analyze` never reads those directories.
4. `meta.json` is written when collection starts (`status: collecting`, `started`,
   `slurm_job`) and after every mode; a shard killed by SLURM leaves a readable marker and
   `analyze` writes an `ERROR collection-interrupted(node;job;started)` row for it instead of
   no row.
5. Saving a dump is a rename inside the store (`_save` uses `shutil.move`), so a program
   never needs twice its dump size transiently.
6. Every sbatch script exports `BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>`
   with one tag per script (two scripts sharing a tag would clobber each other's `<id>/`
   directories: `collect_one` wipes `<store>/<id>` first). None references `/mnt/local` or
   `/tmp` any more (`grep -rn "/mnt/local\|/tmp" eval/baselines/setup/p_*.sh` → nothing).
7. The CPU analysis phase reads the store from `normal`/`max` nodes:
   `TAG=<tag> sbatch eval/baselines/setup/p_analyze_cpu.sh`. `parallel.py analyze` never
   calls `blib.resolve_cuda_home()` (only `cmd_collect`/`cmd_run` do: `parallel.py`
   `grep -n resolve_cuda_home` → 2 call sites, both GPU commands).
8. BeeGFS is not backed up: `eval/baselines/store_inventory.py` mirrors every BeeGFS store's
   `STORE_INFO.json` + `meta.json` into `eval/baselines/store_index/<tag>/` (home; the
   mirrors are gitignored, the summary `store_index/inventory.{md,json}` is tracked) and
   lists what each store lacks and why.
9. Result CSVs, confirm JSONs and the (capped) mismatch copies stay in home as before.

## 2. Filesystem facts (measured)

### 2.1 Login node (`login2`)
```
$ df -h /mnt/beegfs            -> df: /mnt/beegfs: No such file or directory
$ mount | grep -i beegfs       -> (nothing)
$ quota -s                     -> 10.1.1.10:/home  34670M used / 39936M quota / 40960M limit, 239k files
```
No BeeGFS on the login node; home is at 34.7 of 40 GB (the kept-trace copies under
`eval/baselines/traces_keep*` are 12 GB of it).

### 2.2 CPU-partition node `c4` (partition `normal`; carries an RTX 5060 Ti, cc 12.0), job 286569
`eval/baselines/setup/t0_fs_probe.sh`, log `setup/build_logs/t0-probe-286569.log`:
```
beegfs_nodev on /mnt/beegfs type beegfs (rw,nosuid,relatime,cfgFile=/etc/beegfs/beegfs-client.conf,_netdev)
beegfs_nodev     127T   73T   54T  58% /mnt/beegfs
/dev/nvme1n1p1   878G   32K  833G   1% /mnt/local
beegfs-ctl --getquota --uid 467231 : used 0 Byte, hard unlimited, chunk files unlimited
beegfs-ctl --getquota --gid 108    : used 0 Byte, hard unlimited
/mnt/beegfs/fzheng4  drwx------ (created 2026-09-20 21:28)
```
| test | result |
|---|---|
| `du -sh cuvein_traces/*` | evcand 140 G, evcand_smoke 13 M, 1.1 s |
| `dd if=/dev/zero bs=1M count=20480 conv=fsync` (20 GiB write) | 48.3 s, 445 MB/s |
| `dd … iflag=direct` (20 GiB read, page cache bypassed) | 43.3 s, 496 MB/s |
| write 100 000 × 4 KB files (100 dirs × 1000) | 60.0 s, 1667 files/s |
| `listdir` of the 100 dirs | 0.24 s |
| read the 100 000 files | 43.4 s, 2304 files/s |
| `rm` 20 GiB file / `rm -rf` the 100 000 files | 0.0 s / 6.9 s |

The quota report says "used 0 Byte" although the user's directory holds 140 GB: quota
accounting is off or not per-user on this pool — read it as "no quota", not as a size
(unverified which).

### 2.3 GPU-partition node (`rtx4060ti16g`), job 286568
PENDING — the partition's 35 nodes were fully allocated by another user when this was
written (SLURM's start estimate 21:22). The log will be
`setup/build_logs/t0-probe-286568.log`; section to be filled from it.

### 2.4 Node types seen while doing this (measured)
- `normal`/`max` nodes carry GPUs of several kinds (c4: RTX 5060 Ti sm_120; c48: RTX 3060 Ti
  sm_86) and the BeeGFS mount, so they serve the CPU analysis phase; they do **not** run the
  evaluation binaries, which are built for sm_89 only: on c48 every program fails natively
  with `no kernel image is available for execution on the device` (job 286576, recorded by
  the harness as `ERROR no-kernel-json(rc=1);native_rc=…` — the native rc/stderr capture
  works as designed). sm_89 hardware is `rtx4060ti16g`, `rtx4060ti8g` (dual-GPU nodes:
  `setup/pin8g.sh`) and, if the `a5000ada` nodes are RTX 5000 Ada, those (unverified).

## 3. What the earlier "keep every trace" run actually lost (measured: `store_inventory.py`, job 286570, node c4)

`eval/baselines/store_index/inventory.md` has the per-program table; summary:

| store | kind | programs | with a loss | on disk |
|---|---|---|---|---|
| `/mnt/beegfs/fzheng4/cuvein_traces/evcand` (created 2026-09-20 21:31, HEAD `fe694b5`, modes engine+trace-only, 3 reps, P1–P6) | BeeGFS | 613 | 55 | 149.4 GB |
| `/mnt/beegfs/fzheng4/cuvein_traces/evcand_smoke` | BeeGFS | 6 | 0 | 13 MB |
| `eval/baselines/traces_keep` (current sweep, 2026-09-21) | home | 248 | 81 | 3.2 GB |
| `eval/baselines/traces_keep_evcand` | home | 86 | 69 | 1.0 GB |
| `eval/baselines/traces_keep_fpfix` / `_fpfix_tr` | home | 87 / 55 | 87 / 55 | 0.6 / 0.7 GB |
| `eval/baselines/traces_keep.prefix_36a93d08` / `.prefix_fe694b5` (superseded revisions) | home | 110 / 208 | 83 / 67 | 3.0 / 3.9 GB |

evcand loss breakdown (programs): engine all-reps-timed-out 39, trace-only all-reps-timed-out
4, missing-exe 16 (the sm_90 cuHadron `bulkcpy`/`dsmem` targets). **`trace_dropped` is set
on 0 programs**: the 20 GB `--keep-all-cap-gb` never fired in that sweep, because no
program of P1–P6 has a complete trace above 20 GB (the P7/P9 apps with 93–360 GB dumps were
never in that store). This corrects the assumption in the T0 brief (Claude.md B1 item 3)
that the cap discarded the largest traces: what discarded them was `_clean_deps()`
deleting a timed-out rep's partial dump (`parallel.py`, pre-T0 lines 207–209 and 259) —
43 programs in evcand alone, among them the P1 `CC_…_1296n` family (engine dump at
timeout 0.1–261 MB, trace-only 1.0–1.7 GB), P4 `matrix-multiplication-*-large` (trace-only
10.4 GB at timeout) and `uts-*-large` (1.6 GB).

Home copies: `trace-too-large` (the `--keep-cap-mb` 100/300 MB cap; meta+dots+logs kept,
kernel JSONs dropped) on 25 programs in `traces_keep`, 37 in `traces_keep_evcand`, 5 in
`traces_keep_fpfix`, 7 in `traces_keep_fpfix_tr`. For the evcand ones the full trace is on
BeeGFS (if the run did not time out); for the `traces_keep` ones (the 2026-09-21 sweep,
node-local store, deleted after analysis) the trace is gone. The P7/P9 partial dumps at the
20-minute cap (up to 359 GB per rep, `eval/BASELINES.md` §1b) were never kept anywhere.

Union of programs with a lost trace over the current stores: 109. Re-collected by step 6:
86 (`setup/t0_full_ids_p79.txt` 21 P7/P9 apps, `setup/t0_full_ids_rest.txt` 65 of P1–P6).
Excluded (`setup/t0_full_ids_excluded.txt`): 16 sm_90 targets (no binary until T1b) and 7
cuHadron `asyncmemcpy`/`interkernel` programs (out of scope by the user's 2026-09-21
decision; their long-cap runs took nodes down — T2/D5 revisit them).

## 4. Harness changes (read from the code)

| file | change |
|---|---|
| `eval/baselines/parallel.py` `_store_root` | BeeGFS-only with loud failure (policy 1) |
| `parallel.py` `collect_one` | `meta.json` first + per-mode checkpoint (`_write_meta`, atomic rename); `_save` moves; `_keep_partial` for timed-out reps; `_arch()` honours a single `CUDA_VISIBLE_DEVICES` (dual-GPU 8g nodes recorded the wrong cc) |
| `parallel.py` `analyze_one` | `ERROR collection-interrupted` row for a `status: collecting` meta |
| `parallel.py` `_keep_trace`, `_cap_kept`, `cmd_run`, argparse | `--keep-cap-mb 0` = unlimited; keep-all default, cap default 0, `--delete-traces` opt-out |
| `eval/baselines/store_inventory.py` | new: inventory + home mirror (policy 8) |
| `eval/baselines/setup/p_analyze_cpu.sh` | new: CPU re-score of a store (policy 7) |
| `eval/baselines/setup/p_full_store.sh` | new: uncapped re-collection into a store (step 6) |
| `eval/baselines/setup/t0_fs_probe.sh`, `t0_smoke.sh` | new: the measurements of §2 and the smoke/green-set run |
| `setup/p_rerun.sh, p_rerun_p9.sh, p_keep.sh, p_diagnose.sh, p_pi_cuvein.sh, p_sc_others.sh, p7_run.sh, p_fpfix.sh, p_fpfix_eng.sh, p_fpfix_tr.sh, p_run.sh, p_full_run.sh, p_p2_run.sh, p_sweep_run.sh` | `BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>`; `p_sc_others.sh` gives `run_iguard.py` its own log tree (`/mnt/beegfs/$USER/tool_logs/iguard-sc`) so its per-id dirs never land inside the cuVein store |
| `setup/p_evcand.sh` | the 20 GB cap removed (comment records what the 2026-09-20 run used) |
| `eval/README.md`, `eval/.gitignore` | Storage paragraph; `store_index/*/` ignored, inventory tracked |

Unchanged on purpose: `kernel_N.json` contents, CSV columns and values, the confirm-file
names, the `<id>/{meta.json,dots/,logs/,<mode>/}` layout (new: `<mode>-partial-rep<k>/`,
`meta.status/started/finished/slurm_job`, `modes.<mode>.partial_dump` — old readers ignore
them), `bin/accelprof`, the collector.

## 5. Commands run
```
git worktree add ../wt-T0 -b infra/beegfs-store cuVein
sbatch -p rtx4060ti16g eval/baselines/setup/t0_fs_probe.sh                       # 286568 (pending)
sbatch -p normal       eval/baselines/setup/t0_fs_probe.sh                       # 286569, c4
sbatch -p normal ... --wrap ".env/bin/python eval/baselines/store_inventory.py \
    --home-stores '/home/fzheng4/AccelProf/eval/baselines/traces_keep*'"          # 286570, c4
sbatch -p rtx3060ti -w c48 eval/baselines/setup/t0_smoke.sh                       # 286576: sm_86, binaries are sm_89 -> no kernel image
PIN8G=1 sbatch -p rtx4060ti8g -w c20 -t 02:30:00 eval/baselines/setup/t0_smoke.sh # 286580: smoke + green set
CV=/home/fzheng4/wt-T0 TAG=full-2026-09-22 IDFILE=eval/baselines/setup/t0_full_ids_p79.txt FLOOR=1200 \
    sbatch --array=0-20 eval/baselines/setup/p_full_store.sh                      # 286578
CV=/home/fzheng4/wt-T0 TAG=full-2026-09-22 IDFILE=eval/baselines/setup/t0_full_ids_rest.txt \
    sbatch --array=0-15 eval/baselines/setup/p_full_store.sh                      # 286579
```

## 6. Smoke test of the changed harness and the green set (measured, node c20, `rtx4060ti8g`, RTX 4060 Ti cc 8.9, job 286580)

`PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t0_smoke.sh`, store
`cuvein_traces/t0-smoke`, 4 programs × 2 modes × 2 reps, log
`setup/build_logs/t0-smoke-286580.log`:

| program | engine | trace-only | store contents |
|---|---|---|---|
| P4-1dconv-norace-small | CLEAN ×2 (520 events) | CLEAN ×2 | `engine/`, `trace-only/` (1.6 MB) |
| P4-uts-norace-small | TIMEOUT ×2 (120 s, dump 0.0 MB, 11.5 GB RSS) | CLEAN ×2 (315 938 events) | `trace-only/` only (57 MB) — nothing to keep from the engine reps: the dump was empty at the kill |
| P5-norace_interblock_atom | CLEAN ×2 | CLEAN ×2 | both modes |
| P5-race_interblock_none-lock_rtraw | RACE ×2 (`global:0x140-0x340:WAR`, lines 31;37) | RACE ×2 (same) | both modes |

Every `meta.json` carries `status: done`, `started`/`finished`, `slurm_job: 286580`,
`arch: 8.9` (the pinned GPU, not the node's 2080 Super), and a peek from a CPU node
during the run (job 286581, c4) saw the in-progress program with `status: collecting`
— the marker a killed shard would leave. `STORE_INFO.json` written (keep-all default).
The verdicts equal the evcand rows of the same programs (rtraw RACE at lines 31/37 in
both modes; uts-small engine TIMEOUT).

Green set (A4) on the same node, same job — the detector is untouched by T0
(`git diff cuVein -- python sanalyzer bin nv-compute getall.sh` is empty), so before ==
after; run once:
```
rm -rf ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py
136 passed, 1 xfailed, 8 warnings in 161.85s
```
(the one xfail is `test_relaxed_handoff_should_race`, as documented.)

First attempt of the smoke (job 286576, c48, `rtx3060ti`, sm_86): every program fails
natively with `no kernel image is available for execution on the device` — the eval
binaries are sm_89 builds; the harness reported it as `ERROR no-kernel-json(rc=1);
native_rc=255/1;native_err=…` rows, i.e. an honest error, not a verdict.

### 6.0 Second smoke: timed-out reps that leave a partial dump (measured, c20, job 286583)
`PIN8G=1 TAG=t0-smoke2 NOGREEN=1 IDS=P4-graph-coloring-norace-large,P4-uts-norace-large sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t0_smoke.sh`

| program | engine | trace-only | store contents |
|---|---|---|---|
| P4-graph-coloring-norace-large | TIMEOUT ×2 (dump 42.9 MB, 10 kernels at the kill, both reps) | CLEAN ×2 (158 106 events, 30 kernels) | `engine-partial-rep1/` (10 kernel JSONs + `PARTIAL` = the rep's meta + "never a verdict"), `trace-only/`; `meta.modes.engine.partial_dump = "engine-partial-rep1"`; rep 2's dump was not larger (42.9 ≤ 42.9 MB) so rep 1 stays — one partial per mode |
| P4-uts-norace-large | TIMEOUT ×2 (dump 0.0 MB — the engine buffers the whole kernel) | CLEAN ×2 (8 586 062 events, 1.6 GB) | `trace-only/` only, `partial_dump: None` |

Observation, not a T0 matter: in the evcand sweep (2026-09-20) the trace-only mode of
`P4-uts-norace-large` timed out in all 3 reps at 120 s with a 1.57 GB dump; on c20 it
completed in 16–17 s with a 1.64 GB dump. Same binary and input; node/contention differ.

### 6.1 CPU-node re-score of the smoke store (measured, node c36, partition `normal`, job 286584)
```
CV=/home/fzheng4/wt-T0 TAG=t0-smoke OUT=t0-smoke-cpu MANIFEST=eval/baselines/setup/manifest.evcand.csv \
    IDFILE=eval/baselines/setup/t0_smoke_ids.txt sbatch --array=0-0 eval/baselines/setup/p_analyze_cpu.sh
python3 eval/baselines/verdict_diff.py 'eval/results/t0-smoke/*.csv' 'eval/results/t0-smoke-cpu/*.csv'
A: 16 rows  B: 16 rows  common: 16  only-A: 0  only-B: 0  differing: 0
identical verdict/report rows: 16
```
35 s wall on a CPU node with no CUDA on its PATH that mattered (`parallel.py analyze`
never resolves CUDA_HOME); the 7 confirm JSONs (`confirm_t0-smoke-cpu/`) match the
GPU phase's set (no confirm file for the uts engine TIMEOUT, as designed).

## 7. Step 6: re-collection into `cuvein_traces/full-2026-09-22` — PENDING (jobs 286578/286579)

## 8. Acceptance — PENDING

## 9. What remains unverified
- (filled in at the end)

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

### 2.3 GPU-partition node `c70` (partition `rtx4060ti16g`, RTX 4060 Ti cc 8.9, 188 GB RAM), job 286568
Same script, log `setup/build_logs/t0-probe-286568.log` (ran 17:51–17:55 once the partition freed):
```
beegfs_nodev on /mnt/beegfs type beegfs (rw,nosuid,relatime,cfgFile=/etc/beegfs/beegfs-client.conf,_netdev)
beegfs_nodev     127T   73T   54T  58% /mnt/beegfs
/dev/sdb1        914G   57G  811G   7% /mnt/local
beegfs-ctl --getquota --uid / --gid : unlimited (and "used 0 Byte" again)
```
| test | c70 (`rtx4060ti16g`) | c4 (`normal`) |
|---|---|---|
| 20 GiB `dd` write, `conv=fsync` | 56.1 s, 383 MB/s | 48.3 s, 445 MB/s |
| 20 GiB `dd` read, `iflag=direct` | 40.6 s, 532 MB/s | 43.3 s, 496 MB/s |
| write 100 000 × 4 KB files | 53.1 s, 1884 files/s | 60.0 s, 1667 files/s |
| `listdir` 100 dirs | 0.25 s | 0.24 s |
| read the 100 000 files | 42.1 s, 2378 files/s | 43.4 s, 2304 files/s |
| `rm` 20 GiB / `rm -rf` 100 000 files | 0.0 s / 6.8 s | 0.0 s / 6.9 s |

Both measurements ran while other users' jobs occupied the cluster (the 16g partition was
fully allocated); they are single samples, not a benchmark. For the harness this means: a
P7/P9 app that dumps 300 GB in its 20-minute budget writes at ~250 MB/s, i.e. within one
node's measured bandwidth, but with 20 such nodes writing at once the aggregate (5 GB/s)
is unverified — the P7/P9 leg's `dump_mb` at timeout versus the node-local numbers in
`eval/BASELINES.md` §1b is the check (§7).

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

## 7. Step 6: re-collection into `cuvein_traces/full-2026-09-22`

### 7.1 P1–P6 leg (65 programs; job 286589, `--array=0-15`, partitions `rtx4060ti16g,rtx4060ti8g`; ran 16:26–17:54 on the 8g nodes c20, c57, c21 with the sm_89 pin; 120 s floor, 1 rep, both modes, `--analysis-timeout 3600`)
`t0_check_full_store.py` on the store from a `normal` node (`setup/build_logs/t0-check-rest.txt`):

| mode | state | programs |
|---|---|---|
| engine | SAVED (complete dump) | 28 |
| engine | PARTIAL-DUMP (`engine-partial-rep1/` kept, TIMEOUT row) | 31 |
| engine | TIMEOUT-EMPTY (timed out with a 0-byte dump: the engine buffers the kernel; nothing to keep, the TIMEOUT row is the marker) | 6 |
| trace-only | SAVED | 65 |

UNEXPLAINED: 0 — every program has, per mode, a saved dump or an explicit partial/timeout
marker. 47 GB on disk at that point (`du`, c70 probe). No saved dump above 20 GB in this
leg (expected: none of P1–P6 has one; the acceptance case is P9-mr in the P7/P9 leg).

CPU-node re-score of this leg (job 286663, `--array=0-3` on `normal`: c57, c4, c5, c6;
3–16 min per shard):
```
CV=/home/fzheng4/wt-T0 TAG=full-2026-09-22 OUT=full-2026-09-22-cpu MANIFEST=eval/baselines/setup/manifest.evcand.csv \
    IDFILE=eval/baselines/setup/t0_full_ids_rest.txt sbatch --array=0-3 eval/baselines/setup/p_analyze_cpu.sh
GPU-phase rows (P1-P6 ids): 130  CPU re-score rows: 130  only-GPU: 0  only-CPU: 0  differing: 0
confirm-file sets identical (93 files each)
```
GPU-phase verdicts of the leg: engine RACE 19 / CLEAN 9 / TIMEOUT 37; trace-only RACE 50 /
CLEAN 15 (one rep each).

### 7.2 P7/P9 leg (21 apps; job 286578, `--array=0-20`, `rtx4060ti16g` only, one app per task, 20-minute floor, 1 rep, both modes, `--analysis-timeout 3600`; ran 17:56–21:28 as the partition freed) + re-run job 286816 (bezier-surface, heartwall, srad)

Three tasks had to be repeated, all for reasons that T0 surfaced and fixed:
- **bezier-surface** (task 0, c70, 188 GB node): its trace-only run *completed* and `_save`
  moved a **138 GB** kernel JSON into the store; then the pre-T0 `_count_events` did
  `json.loads` on it, the harness process reached 183 GB RSS and the kernel OOM killer
  SIGKILLed the shard (`sacct`: FAILED 9:0, MaxRSS 182 839 768 K). The T0 marker worked:
  `meta.json` stayed at `status: collecting` and a CPU re-score (job 286735) wrote
  `ERROR collection-interrupted(node=c70;job=286669;started=17:56:55)` for the mode instead of
  no row. Fix: kernel JSONs above `BASELINE_COUNT_EVENTS_MAX_GB` (12) are no longer parsed
  for the event count (`meta.modes.<mode>.events_uncounted`). The re-run (job 286816_0)
  landed on **c58, a 128 GB node**: both collector runs died at ~122 GB RSS (`ERROR
  no-kernel-json(rc=1)`), so bezier's 138 GB trace exists only on a 188 GB node — the
  `rtx4060ti16g` partition mixes 128 GB (c1, c3, c50–c58, …) and 188 GB (c70, c73, …)
  nodes (`/proc/meminfo` on c3: MemTotal 131 535 632 kB; on c70: 188 GB), which is why
  `meta.json` now records `mem_total_gb` (added after this sweep; None in these metas).
- **heartwall, srad** (tasks 2, 7): failed natively in 9 s — `collect_one` mirrors the
  HeCBench data directory from `eval/baselines/corpora/`, which is gitignored and was
  absent from the T0 worktree; the symlink was added and both re-ran (job 286816_1/2):
  TIMEOUT at 20 min with 146 GB / 270 GB partial dumps kept. The superseded rows are in
  `eval/results/full-2026-09-22/superseded_native_fail/` (and the interrupted bezier
  re-score in `full-2026-09-22-cpu/superseded_interrupted/`), never overwritten.

Also new in the harness after this leg: `_analyze_capped` runs the offline analysis under
an address-space cap (`--analysis-mem-gb`, default 80 % of the node's RAM) and reports
`analysis-oom` / `analysis-died(rc=N)` / `analysis-timeout` as ERROR rows — no analysis
can take a shard down any more (unit-tested on the login node for all six paths; no P7/P9
analysis hit it in this sweep).

The rows (`t0_p79_table.py`; the last column is the node-local diagnose run of
`eval/BASELINES.md` §1b, same 20-minute cap, for the dump-size comparison):

| program | mode | T0 verdict (wall s, peak RSS GB) | T0 dump at cap / saved (MB) | node-local run of §1b: verdict, dump (MB), peak GB, cause |
|---|---|---|---|---|
| bezier-surface-cuda | engine | ERROR (1118 s, 122) | collector died (rc=1) | —, —, —, analysis-oom |
| bezier-surface-cuda | trace-only | ERROR (547 s, 122) | collector died (rc=1) | —, —, —, analysis-oom |
| bitonic-sort-cuda | engine | TIMEOUT (1200 s, 19) | 33061.8 | TIMEOUT, 45446.2, 19, trace-volume |
| bitonic-sort-cuda | trace-only | TIMEOUT (1200 s, 4) | 138296.8 | TIMEOUT, 245924.9, 4, trace-volume |
| haversine-cuda | engine | TIMEOUT (1200 s, 29) | 106085.6 | TIMEOUT, 73443.9, 29, trace-volume |
| haversine-cuda | trace-only | TIMEOUT (1200 s, 10) | 293775.4 | TIMEOUT, 277454.6, 10, trace-volume |
| heartwall-cuda | engine | TIMEOUT (1200 s, 52) | 12.7 | TIMEOUT, 12.7, 81, trace-volume |
| heartwall-cuda | trace-only | TIMEOUT (1200 s, 85) | 146073.2 | TIMEOUT, 252269.0, 85, trace-volume |
| hotspot-cuda | engine | TIMEOUT (1200 s, 7) | 13160.8 | TIMEOUT, 9212.6, 7, trace-volume |
| hotspot-cuda | trace-only | CLEAN (132 s, 1) | saved, events=34830000 | CLEAN, —, 1, resolved |
| lavaMD-cuda | engine | TIMEOUT (1200 s, 36) | 0.0 | TIMEOUT, 0.0, 36, collector-memory |
| lavaMD-cuda | trace-only | ERROR (1098 s, 186) | collector died (rc=1) | TIMEOUT, 0.0, 170, collector-memory |
| mandelbrot-cuda | engine | TIMEOUT (1200 s, 3) | 89848.4 | TIMEOUT, 77319.7, 3, trace-volume |
| mandelbrot-cuda | trace-only | TIMEOUT (1200 s, 1) | 298232.8 | TIMEOUT, 288159.0, 1, trace-volume |
| nbody-cuda | engine | TIMEOUT (1200 s, 117) | 132501.6 | TIMEOUT, 108999.5, 117, trace-volume |
| nbody-cuda | trace-only | TIMEOUT (1200 s, 44) | 303850.8 | TIMEOUT, 301366.6, 44, trace-volume |
| particlefilter-cuda | engine | RACE (1001 s, 119) | saved, events=5617276 (prefix dump: app died under the tool) | RACE, —, 120, resolved |
| particlefilter-cuda | trace-only | RACE (556 s, 119) | saved, events=5617276 (prefix dump: app died under the tool) | RACE, —, 120, resolved |
| pathfinder-cuda | engine | TIMEOUT (1204 s, 122) | 0.0 | TIMEOUT, 0.0, 95, collector-memory |
| pathfinder-cuda | trace-only | TIMEOUT (1200 s, 7) | 254097.2 | TIMEOUT, 155281.6, 7, trace-volume |
| srad-cuda | engine | TIMEOUT (1200 s, 4) | 18692.5 | TIMEOUT, 16262.1, 4, trace-volume |
| srad-cuda | trace-only | TIMEOUT (1200 s, 1) | 269762.0 | TIMEOUT, 261693.1, 1, trace-volume |
| stencil1d-cuda | engine | ERROR (994 s, 121) | collector died (rc=1) | TIMEOUT, 0.0, 122, collector-memory |
| stencil1d-cuda | trace-only | TIMEOUT (1200 s, 83) | 240044.0 | TIMEOUT, 320058.7, 83, trace-volume |
| atomicCAS-cuda | engine | TIMEOUT (1200 s, 29) | 68231.1 | TIMEOUT, 44397.0, 33, trace-volume |
| atomicCAS-cuda | trace-only | TIMEOUT (1200 s, 1) | 216436.7 | TIMEOUT, 115870.0, 1, trace-volume |
| crs-cuda | engine | RACE (260 s, 3) | saved, events=9617332 | — |
| crs-cuda | trace-only | RACE (44 s, 1) | saved, events=9617332 | — |
| dxtc2-cuda | engine | TIMEOUT (1200 s, 13) | 21589.3 | TIMEOUT, 17991.0, 13, trace-volume |
| dxtc2-cuda | trace-only | TIMEOUT (1200 s, 5) | 248928.5 | TIMEOUT, 248236.9, 4, trace-volume |
| expdist-cuda | engine | TIMEOUT (1200 s, 46) | 0.0 | TIMEOUT, 0.0, 45, collector-memory |
| expdist-cuda | trace-only | TIMEOUT (1200 s, 61) | 192253.5 | TIMEOUT, 359051.9, 61, trace-volume |
| fpc-cuda | engine | ERROR (251 s, 122) | collector died (rc=1) | — |
| fpc-cuda | trace-only | CLEAN (247 s, 1) | saved, events=115834880 | — |
| gpp-cuda | engine | ERROR (854 s, 122) | collector died (rc=1) | — |
| gpp-cuda | trace-only | CLEAN (61 s, 2) | saved, events=10240000 | — |
| knn-cuda | engine | TIMEOUT (1200 s, 103) | 0.0 | TIMEOUT, 0.0, 70, collector-memory |
| knn-cuda | trace-only | TIMEOUT (1200 s, 99) | 202568.1 | TIMEOUT, 101284.0, 99, trace-volume |
| mr-cuda | engine | TIMEOUT (1200 s, 2) | 68394.0 | TIMEOUT, 114965.7, 2, trace-volume |
| mr-cuda | trace-only | ERROR (686 s, 1) | 112955.3 | ERROR, 112955.3, 1, analysis-timeout |
| tridiagonal-cuda | engine | TIMEOUT (1200 s, 51) | 13787.5 | TIMEOUT, 13787.5, 51, trace-volume |
| tridiagonal-cuda | trace-only | TIMEOUT (1200 s, 15) | 220846.5 | TIMEOUT, 358474.2, 15, trace-volume |

Dump volume at the 20-minute cap, BeeGFS (T0) vs node-local NVMe (§1b), trace-only mode
where both timed out: bitonic 138 vs 246 GB, haversine 294 vs 277, heartwall 146 vs 252,
mandelbrot 298 vs 288, nbody 304 vs 301, pathfinder 254 vs 155, srad 270 vs 262, stencil1d
240 vs 320, atomicCAS 216 vs 116, dxtc2 249 vs 248, expdist 192 vs 359, knn 203 vs 101,
tridiagonal 221 vs 358. Ratio range 0.5–2.0 with no consistent sign: the shared filesystem
does not systematically throttle the collector at this concurrency (up to 9 apps writing
at once); node-to-node variation dominates. The aggregate-bandwidth concern of §2.3 is
therefore not borne out at this scale (it remains unverified for 30+ concurrent writers).

### 7.3 The store after the leg (`t0_check_full_store.py`, `setup/build_logs/t0-check-full.txt`)

86 programs, **3.6 TB** (`du -sh`), every `meta.json` `status: done`, `arch: 8.9` on all 12
nodes used (the 8g nodes c20/c21/c57 included — the pin works), 0 UNEXPLAINED, 0
INTERRUPTED:

| mode | state | programs |
|---|---|---|
| engine | NO-KERNEL-JSON(rc=1) | 4 |
| engine | PARTIAL-DUMP | 42 |
| engine | SAVED | 29 |
| engine | SAVED-partial-prefix | 1 |
| engine | TIMEOUT-EMPTY | 10 |
| trace-only | NO-KERNEL-JSON(rc=1) | 2 |
| trace-only | PARTIAL-DUMP | 13 |
| trace-only | SAVED | 70 |
| trace-only | SAVED-partial-prefix | 1 |

Saved dumps above 20 GB (acceptance case):
    113.0 GB  trace-only  P9-mr-cuda
     50.0 GB  trace-only  P9-fpc-cuda
     26.3 GB  trace-only  P7-hotspot-cuda


`NO-KERNEL-JSON(rc=1)` = the collector was OOM-killed on a 128 GB node (bezier ×2, fpc,
gpp, stencil1d engine; lavaMD trace-only at 186 GB on a 188 GB node) — an honest ERROR row
with `peak_mb` ≈ 122 000, not a lost trace.

## 8. Acceptance

| criterion | result |
|---|---|
| a keep-all run of ≥5 programs including one whose trace exceeds 20 GB lands complete on BeeGFS | **met**: 86 programs in `cuvein_traces/full-2026-09-22`; complete (non-partial, non-timed-out) saved dumps above 20 GB: P9-mr trace-only **113.0 GB** (1600 kernels), P9-fpc trace-only 50.0 GB (115.8 M events, CLEAN), P7-hotspot trace-only 26.3 GB (34.8 M events, CLEAN) |
| `parallel.py analyze` of that store from a `normal` node reproduces the GPU phase's verdicts | **met** for the 65 P1–P6 programs (130 rows, 0 differing, confirm sets identical; job 286663) and the 19 finished P7/P9 apps (38 rows, 0 differing; job 287083); the last two apps (fpc, mr) — see below |
| no `p_*.sh` references `/mnt/local` or `/tmp` | **met**: `grep -rn "/mnt/local\|/tmp" eval/baselines/setup/p_*.sh eval/baselines/setup/p7_run.sh` → nothing |
| green set unchanged | 136 passed, 1 xfailed (c20, job 286580); detector code untouched |



## 9. What remains unverified / not done
- The P9-fpc and P9-mr CPU re-score (job 287114) — result appended in §8 when it finishes.
- BeeGFS behaviour with 30+ concurrent collector writers (this sweep peaked at 9 GPU
  tasks); a 32-shard P1–P8 re-run (`p_rerun.sh`) is the test.
- The quota report (`beegfs-ctl --getquota`: "used 0 Byte" with 3.7 TB in the directory):
  read as "no quota", the accounting itself is not understood.
- `a5000ada` nodes: assumed sm_89, never used.
- The 16 sm_90 cuHadron targets (no binary until T1b) and the 7 cuHadron
  `asyncmemcpy`/`interkernel` programs (out of scope by the 2026-09-21 decision) were not
  re-collected (`setup/t0_full_ids_excluded.txt`).
- `--keep-mismatch` home copies were not made for this sweep (home is at 35 of 40 GB); the
  BeeGFS store is the only copy of these traces, and BeeGFS is not backed up. The `meta.json`
  mirrors (`store_index/`) live in home.
- The partial-dump policy keeps one prefix per mode with no size cap: the 21 P7/P9 apps
  contribute ~3.4 TB of prefix dumps that no analysis reads today (T4/T5a/T7 measurements
  are the intended consumers). Reconsider `--keep-all-cap-gb` for prefix dumps if the
  55 TB free on BeeGFS becomes a constraint.
- `mem_total_gb` was added to `meta.json` after this sweep: it is None in the 86 metas.
- The stale BASELINES.md §1b root cause of bezier-surface (`analysis-oom`) is now known to
  be the harness's own `_count_events` on a 138 GB dump (not the analysis); the row text in
  BASELINES.md was not changed (T8 regenerates the tables).

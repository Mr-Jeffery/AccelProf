# T26: the PCDepGraph pass sharded by location

Branch `perf/sharded-pcdep` (unmerged), worktree `~/wt/sharded-pcdep` (sparse: no `eval/results`, `eval/x_logs`,
`eval/x1_follow`, `eval/nvbit_spike`, `setup/*_logs`), 2026-11-07. Freeze exception approved by Jeffery on
2026-11-07, limited to the PCDepGraph pass and the harness plumbing of the worker count. Nothing under
`nv-compute/`, `python/hb_oracle.py`, `python/sync_dominance.py`, `bin/`, HbClock or ShardPool's HbClock use changed.

## 0. Base commit

`origin/cuVein` 98371ee1 (merge of X7 Part A). Reconciled before the build:

- installed `build/sanalyzer/lib/libsanalyzer.so` sha256 `5a20fd14ab6c6806…` = the `libsanalyzer` of C1's runtime
  table (`eval/COLLECTOR_ONLY.md` on `origin/eval/co-chain-b`, every collector-only `meta.json`), runtime HEAD f551ca00
  (“Install the runtime built from e0e6431”); installed collector `b746b4dd23e90f46` likewise.
- `git diff --stat e0e64316 98371ee1 -- sanalyzer nv-compute bin python/hb_oracle.py` is empty: the X7 work merged after
  the install commit touched only the harness and the verdict step. So 98371ee1 carries the installed runtime's source
  and, in addition, the collector-only harness mode (40b52226) that the parity runs need.
- The private collector is relinked from `stage-t24-e0e6431/nvc/obj`, the objects of the installed build.

## 1. The change (`sanalyzer/src/tools/pc_dependency_analysis.cpp`, `…/pc_dependency_analysis.h`)

- **Ownership by location.** The `ctaId % N` partition is gone. A lane of a memory record goes to the shard owning its
  128-byte segment, `ShardPool::shard_of` (T22's function; refactored only into `shard_of_n(n, hi, seg)` so that the
  pass can call it with its own N; ShardPool's own calls are unchanged): global memory by the absolute address
  (`hi` = 0), shared memory by (pooled object, word offset). A lane whose words span segments is split by word
  (entry flag `PCD_SPLIT`). Each shard owns its words exclusively: disjoint entries of the region shadows (plain load and
  store instead of `__atomic_exchange_n`), its own map for untracked addresses (`unit_access_unknown`'s locked
  `parallel_flat_hash_map_m` replaced by one `flat_hash_map` per shard, cleared at kernel start as before), the words of
  a shared-memory object. Local memory unchanged (record statistics only). Within a shard, records are processed in
  buffer order (the serial pass's order; T15's late order never applied to this pass and still does not).
- **Shared memory: routed by object, not block.** The serial pass reuses a pooled object for a later block once the
  earlier block has exited; a reused object's words then carry the earlier block's id, which is what makes the later
  block's first access a cold miss. Routing by block would put the two blocks' accesses to the same words on two
  shards. So the pool is the serial pass's: one pool, the `-n 1` capacity (`max(32, SM × blocks/SM × slack)`, no longer
  divided by N), slot = cta; the drain thread acquires and releases objects in drain order (so a pool miss and every
  reuse happen exactly as at `-n 1`), and a shared word is routed by `shard_of((1<<63) | object, offset >> 7)`.
  This deviates from the brief's “route by (space, block)”; it is the form that is identical at every N.
- **Per-shard statistics.** Each shard keeps `pc_statistics`, `pc_flags` and the 97-bin histograms and merges them into
  the global maps once, at kernel end (`pcdep_merge_shards`, called before `kernel_trace_flush`); sums, ORs and maxima
  commute. A record's own statistics (flags, histograms, repeat lanes, pool-miss cold counts) go to exactly one shard
  (`PCD_REC`). Each shard caches the last (pc, ancient pc) key → slot pointer (re-pointed on every insert, so a rehash
  cannot leave it dangling) and the last pc's flag/histogram slots.
- **Routing.** The drain thread is the router: it routes 32,768-record chunks and publishes each one; the N shard threads
  run behind it; the drain is joined before `gpu_data_analysis` returns (the collector reuses the buffer). A drain below
  4,096 records (`YOSEMITE_PCDEP_INLINE_MAX`) is routed and then run shard by shard on the drain thread. N = 1 is the
  serial path: the drain thread applies each record itself, no router or shard thread. `YOSEMITE_WORKER_COUNT` /
  `accelprof -n` is the shard count (capped at 64, with a stderr line). `YOSEMITE_PCDEP_STATS=1` prints one
  `[PCDEP_STATS]` line per kernel (records, entries, split entries, drain/route/wait seconds, per-shard busy/stall).
- **State** is file-static (`pcd_pool`), not new PcDependency members (the header's latent-UB note): no data member was
  added, removed or retyped; the unused `_workers` / `_job_worker_*` members stay, empty. Removed from the header: the
  declarations of `unit_access*`, `worker_loop`, `get_shared_shadow_entry` (their logic is now `pcd_global`,
  `pcd_unknown`, `pcd_shared`, `PcdPool`).
- **Harness plumbing** (`eval/baselines/blib.py`, `parallel.py`, `run_cuvein.py`): `$BASELINE_WORKERS` (default 1)
  becomes `accelprof -n`, recorded as `analyzer_workers` in every `meta.json`. The tests keep `-n 1`.

## 2. Runtime (own prefix; nothing installed)

`eval/baselines/setup/t26_build.sh` (job 329088, c3): `/home/fzheng4/stage-t26/san-install/lib/libsanalyzer.so`
`31e4d53d367e693b`, collector `/home/fzheng4/stage-t26/rt-lib/libcompute_sanitizer.so` `86473afa906669e5`
(RPATH → the private library); `~/wt/sharded-pcdep/lib` → `stage-t26/rt-lib`, so `ACCEL_PROF_HOME=~/wt/sharded-pcdep` is
the runtime. Installed files unchanged before and after (5a20fd14…, b746b4dd…). GCC 12.4.0, `-O3 -g -mtune=znver4`.

## 3. Parity method

Two GPU executions of a program are two record streams (a schedule-dependent kernel's counts move between two
`-n 1` runs of the *installed* runtime; the live controls below show it). Byte identity is therefore checked on one
stream fed to both libraries:

- `setup/t26_parity/capture_shim.cpp`: a `libsanalyzer.so` that forwards every `yosemite_*` call to `CAP_REAL_LIB`
  (dlopen) and writes allocations, frees, tensor and memcpy/memset events, kernel starts/ends and every drain's records
  (every field the analyzer reads; addresses of the lanes in `active_mask | unique_address_mask`) to `CAP_DIR`. A
  collector relinked against it (`stage-t26/cap-rt-lib`, same objects) and a symlink home (`stage-t26/caphome`) make
  the installed library or the new one record through it. The analyzer and the collector are not changed by it.
- `setup/t26_parity/replay.cpp` (`stage-t26/bin/t26_replay`): makes the captured calls again, in order, through
  whichever `libsanalyzer.so` `LD_LIBRARY_PATH` names.
- `setup/co_json_diff.py`: per kernel, byte identity, then edges only in A / only in B, edges whose dist counts or flags
  differ, nodes only in A / B / differing (flags, access size, the three histograms), kernel header, every other
  top-level key (the hb_* aggregates included). Ignores only tool/runtime hash fields (a kernel JSON has none).

Checks per program: **fidelity** — the installed library's replay of a stream equals the live output of the run that
recorded it (validates capture and replay); **same-stream parity** — on each captured stream (one recorded by the
installed runtime at `-n 1`, one by the new runtime at N = 16), the new library at N = 1, 16 and 16 with every drain
threaded (`YOSEMITE_PCDEP_INLINE_MAX=0`) against the installed library at `-n 1`, and the new runtime's live N = 16
output against the installed library on its records; **live** — the brief's comparison of separate recordings on the
same node in the same job, with an installed-vs-installed control.

## 4. Results

All jobs on `rtx4060ti16g` (RTX 4060 Ti, sm_89), whole nodes; logs in `eval/x_logs/t26-*.log`; per-id kernel JSONs
(live and replayed) and the diff reports of every non-equal comparison under `/mnt/beegfs/fzheng4/t26/`.

**4.1 Green set** (job 329104, c3, AMD EPYC 9115; `ACCEL_PROF_HOME` = the worktree runtime; tests call `accelprof -n 1`):
A4's seven files + `test_collector_only.py`: **306 passed, 0 skipped** (C1's count on the installed runtime: 306 / 0);
`test_no_dump.py`: **31 passed**; `test_co_chain.py` (from `origin/eval/co-chain-b` f31a5067, CPU only, reads recorded
fixtures, not the runtime; job 329125): **21 passed**.

**4.2 Same-stream parity (the acceptance check): 0 differences.** "Equal" below = byte-identical files.

| set | streams | comparison | programs equal / compared | kernels byte-identical |
|---|---|---|---|---|
| fixtures (`python/testdata/*.cu`, `scale/*.cu`; job 329117, c72) | 22 × 2 | fidelity (replay vs the run that recorded) | 22/22, 22/22 | 44/44, 44/44 |
| | | installed `-n 1` vs new N=1, 16, 16 threaded | 6 × 22/22 | 6 × 44/44 |
| | | new live N=16 vs installed on its records | 22/22 | 44/44 |
| T20 ids, collector-only (job 329114, c55) | 64 × 2 | installed `-n 1` vs new N=1, 16, 16 threaded | 6 × 64/64 | 503 + 502 per N |
| | | fidelity / new live N=16 vs installed on its records | 63/64, 63/64 | 502/502, 501/501 |
| T20 ids, scalar-clock, X1b settings (job 329115, c56) | 64 × 2 | installed `-n 1` vs new N=16 | 64/64, 64/64 | 505/505, 504/504 |
| | | fidelity / new live N=16 vs installed on its records | 63/64, 63/64 | 504/504, 503/503 |
| T20 ids, vector-clock (job 329116, c71) | 64 × 2 | installed `-n 1` vs new N=16 | 64/64, 64/64 | 490/490, 490/490 |
| | | fidelity / new live N=16 vs installed on its records | 62/64, 62/64 | 476/476, 476/476 |
| P6-interkernel-ww, 1,200 s re-recording (jobs 329158–329160) | 1 × 2 per mode | every check above, all three modes, live included | 3/3 modes | 2/2 kernels each |
| synthetic streams (`synth.py`, 6 seeds × 5 kernels × 150,000 records; job 329103, CPU) | 6 × 2 pools | installed `-n 1` vs new N=1, 2, 3, 7, 16, 64, 16 threaded | 84/84 | 420/420 |

The program short in every "fidelity / live vs its records" row of the 64-id sets is P6-interkernel-global_writewrite_race-racy: every
configuration's live run, installed included, hit the harness's tool timeout of 120 s (`parallel.py collect` does not
pass `--timeout-floor` on; the timeout is min(max(10 × native, 120), cap)), so the live side has no kernel JSON while the
replay of the partial stream writes one. Its same-stream rows (installed vs new on that partial stream) are equal. A
re-run with a true 1,200 s tool timeout (`LIVE=direct`, `t26_parity/live_one.py`; jobs 329158/9/60) completed in every
configuration (151–177 s per run, 2 kernels, 5.2 GB streams) and is byte-identical on every check in all three modes, the
live comparisons and the installed-vs-installed control included. In vector-clock mode P7-bfs-cuda's live runs also
stopped at the 120 s cutoff (13 of 24 kernels), which is the second short program in the vector-clock row; its 13-kernel
streams compare equal. Its 1,200 s vector-clock re-run (job 329231) was cancelled on request before it finished: complete
vector-clock recordings of P7-bfs-cuda are **missing**. P7-particlefilter-cuda is not in any set: C1 recorded it as TIMEOUT at 1,200 s (7.3·10⁹ records; a capture
would be ~2 TB). The synthetic streams cover: global lanes misaligned, crossing 128-byte segments, out of region past a
first in-region lane, untracked and freed-region addresses, access sizes 0–32, repeat lanes; shared offsets past a 4,096-byte
object and wrapping 2³²; a 32-object pool with misses and reuse (and the default pool); block ids above 2²²; an unknown
record type (366–376 "unknown memory type" lines, the same count from both libraries); drains of 1 to 100,000 records.

**4.3 Live recordings, as the brief asks (separate GPU executions, same node, same job).**

| set | new N=1 vs installed `-n 1` | new N=16 vs installed `-n 1` | control: installed `-n 1` vs installed `-n 1` |
|---|---|---|---|
| fixtures, 22 programs | 17 equal, 5 differ | 17 equal, 5 differ | 17 equal, 5 differ (the same 5) |
| T20 ids collector-only, 64 | 26 equal, 37 differ, 1 none | 27 equal, 36 differ, 1 none | 26 equal, 37 differ, 1 none |
| T20 ids scalar-clock, 64 | — | 27 equal, 36 differ, 1 none (installed run through the shim vs new) | — |
| T20 ids vector-clock, 64 | — | 13 equal, 49 differ, 2 none (P6-interkernel, P7-bfs: 120 s cutoff) | — |

Kernels byte-identical in the collector-only rows: 110/497 (N=1), 113/497 (N=16), 109/498 (control). The fixtures that
differ are `broadcast_read`, `flag_writers`, `lock_contention_a2`, `grid_workqueue`, `tiled_gemm`: multi-warp kernels whose
record order is the GPU's schedule. Two recordings by the installed runtime differ in the same programs and by the same
amount, and each live run's output equals the installed library's output on that run's own records (4.2), so these
differences come from the executions, not the pass. Byte identity of separately recorded JSONs is not obtainable for
these programs with either runtime.

**4.4 Timing on identical streams** (not an X12 measurement; job 329144, c3, AMD EPYC 9115 16-core; collector-only
captures; seconds inside the library's drain calls, mean of 3 reps; replay driver `t26_replay2`, unlocked
reads). "installed -n16" is the old `ctaId % 16` pass, which is **not** identical to its own `-n 1` on 4 of these 6
streams (P9-crs, P7-bfs, P1-CC, P7-backprop).

| program (records) | installed -n1 | installed -n16 | new N=1 | new N=16 | new N=16 route / wait |
|---|---|---|---|---|---|
| P6-interkernel-ww (53 M, 120 s prefix) | 2.11 | 2.11 | 1.74 | 1.55 | 0.80 / 0.30 |
| P9-overlap-cuda | 4.56 | 0.64 | 2.04 | 0.69 | 0.63 / 0.06 |
| P9-crs-cuda | 1.13 | 0.29 | 0.61 | 0.56 | 0.38 / 0.18 |
| P7-bfs-cuda | 1.34 | 0.27 | 1.10 | 0.40 | 0.38 / 0.02 |
| P1-CC_V_Topo_Pull_Determ…1296n | 0.064 | 0.030 | 0.050 | 0.057 | 0.05 / 0.003 |
| P7-backprop-cuda | 0.24 | 0.045 | 0.10 | 0.058 | 0.055 / 0.002 |

New N=16 against installed `-n 1` (the configuration of every collector-only row): 1.4×, 6.6×, 2.0×, 3.4×, 1.1×, 4.1×.
At N=16 the drain thread's routing is most of the pass (route ≈ drain), with the shards idle behind it; new N=16 is
slower than the non-identical old `-n 16` on 5 of 6. Not tuned further (no speed target in T26). An earlier timing job
(329126) measured whole-replay wall time and is superseded: glibc's locked `fread` in the first replay driver dominated
any multi-threaded process (perf, job 329142), the installed library's `-n 1` included.

## 5. Commands

```
# build (private prefix)
sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t26-build-%j.log <W>/eval/baselines/setup/t26_build.sh
# green set; test_co_chain from a read-only checkout of origin/eval/co-chain-b
sbatch -o <W>/eval/x_logs/t26-green-%j.log <W>/eval/baselines/setup/t26_green.sh
# parity
sbatch -o <W>/eval/x_logs/t26-fix-%j.log  <W>/eval/baselines/setup/t26_parity/fixtures.sh
sbatch -o <W>/eval/x_logs/t26-synth-%j.log <W>/eval/baselines/setup/t26_parity/synth.sh
for m in collector-only scalar-clock vector-clock; do
  sbatch --export=ALL,MODE=$m -o <W>/eval/x_logs/t26-t20-$m-%j.log <W>/eval/baselines/setup/t26_parity/t20.sh; done
for m in collector-only scalar-clock vector-clock; do      # P7-bfs-cuda vector-clock likewise: job 329231, cancelled
  sbatch --export=ALL,MODE=$m,LIVE=direct,IDS=P6-interkernel-global_writewrite_race-racy,CAP=1200 \
    -o <W>/eval/x_logs/t26-t20-p6ww-$m-%j.log <W>/eval/baselines/setup/t26_parity/t20.sh; done
.env/bin/python eval/baselines/setup/t26_parity/summarize.py eval/x_logs/t26-t20-*.log
# timing on identical streams
sbatch -o <W>/eval/x_logs/t26-time-%j.log <W>/eval/baselines/setup/t26_parity/timing.sh
# X12: BASELINE_WORKERS=16 makes the harness run accelprof -n 16; ACCEL_PROF_HOME=~/wt/sharded-pcdep is the runtime
```

## 6. What remains unverified

- P7-bfs-cuda in vector-clock mode: complete recordings missing (120 s harness cutoff; the 1,200 s re-run was cancelled).
- P7-particlefilter-cuda: not compared (TIMEOUT at 1,200 s in C1; capture size).
- The green set runs the tests' `accelprof -n 1` only; N=16 is covered by the fixture, T20 and synthetic parity, not by
  the pytest assertions.
- The capture shim keeps lane addresses only for `active_mask | unique_address_mask`; the other lanes are zero in a
  replay. Neither pass reads them (fidelity 0 differences confirms it on these programs), but a stream that did would not
  replay faithfully.
- The live parity jobs ran the installed and new runtimes through the capture shim in the "c" configurations (Ic, Bc);
  the plain runtimes were run as I0, A, B (collector-only only).
- Performance: routing on the drain thread is the N=16 bottleneck (4.4); X12's wall times are measured by X12.

## 7. X12 follow-up: SuperCollider's native HeCBench binaries (parity gate)

X12 recorded SuperCollider's native binaries in collector-only mode at N=16 and compared them with X11's three `-n 1` recordings. crs, fpc, mr and dxtc2 differed, so I checked whether the pass is at fault, using the same capture/replay method as in section 4.

**Setup.** `t26_parity/sc.sh` runs inside X12's container (`ubuntu2204.sif`) with the same setup X12 used:
- a shadow ACCEL_PROF_HOME whose `bin/accelprof` also preloads `libcudart.so.13`;
- X12's run tree (`x12_mktree.py`), with arguments taken from `artifact_subset.json`;
- `accelprof -v`.

Each program is recorded once through the capture shim (installed library, `-n 1`). On the host, that stream is replayed through the installed library at `-n 1` and through the new library at N=1, N=16 and N=16 with every drain threaded. `KMAX_<app>=k` limits the capture to the first k kernels; this sets the shim's new `CAP_MAX_KERNELS` option.

**Same-stream results** (jobs 329305 and 329320; shim e1a01cdd4f0cf5de):

| program | kernels | records | new N=1 | new N=16 | new N=16t | fidelity |
|---|---|---|---|---|---|---|
| mr | 16 | 845,192 | EQUAL | EQUAL | EQUAL | EQUAL |
| crs | 50 | 9,864,919 | EQUAL | EQUAL | EQUAL | EQUAL |
| fpc | 202 | 145,620,992 | EQUAL | EQUAL | EQUAL | EQUAL |
| dxtc2, first 10 kernels | 10 | 49,501,310 | EQUAL | EQUAL | EQUAL | EQUAL |

EQUAL means byte-identical on every kernel. Fidelity compares the installed replay with the live run that produced the stream. The full dxtc2 stream (about 150 GB) was not captured; that job was cancelled.

**Live context.** The live installed `-n 1` run made through the shim differs from X11 r1/r2/r3 about as much as those three differ from each other:

| program | edges changed vs X11 | edges changed between X11 runs |
|---|---|---|
| crs | 443–447 | 445–446 |
| fpc | 399–403 | 402–403 |
| mr | 246–248 | 247–248 |

**Runtime checks** (from the metas):
- X12 (crs, fpc, mr, dxtc2): `workers=16`, `analyzer_workers=16`, libsanalyzer 31e4d53d367e693b, collector 86473afa906669e5.
- X12's crs control: libsanalyzer 5a20fd14ab6c6806, `workers=1`.
- X11 r1–r3: libsanalyzer 5a20fd14ab6c6806, collector b746b4dd23e90f46 (the installed runtime).
- Drained-record counts are equal across all of them.

**Why `intra_block` and `intra_grid` move between runs.** Each 4-byte shadow word stores the thread that touched it last, packed as tid = ctaId<<10 | warpId<<5 | lane. `pcd_classify` compares the current access with that stored thread:
- a different `ctaId` counts as `intra_grid`;
- the same `ctaId` but a different `warpId` counts as `intra_block`;
- the same warp but a different lane counts as `intra_warp`;
- otherwise it counts as `intra_thread`.

In pc_dependency, `ctaId` is `get_ctaid_as_uint64()` and `warpId` is flat threadIdx/32, so both are logical ids, fixed per access. Which thread came last depends on record order, which is the order in which warps take buffer slots (`GetBufferIndex`, an atomic). That order differs from run to run. When the interleaved accesses share a PC pair, only the split between `intra_block` and `intra_grid` changes (crs, fpc). When different PCs interleave, the ancient PC changes as well, so per-edge totals move too (mr, dxtc2).

Routing and shard order have no effect. Each word has exactly one owning shard, that shard applies the word's entries in drain order, and per-shard counts are integer sums.

**Gate for X12 (two parts).**
- **G1, the pass.** Every `same-stream` line must be EQUAL; any DIFFER is a pass bug. Run:
  `APPS="<apps>" [KMAX_knn=20 KMAX_tridiagonal=50] sbatch -o eval/x_logs/t26-sc-%j.log eval/baselines/setup/t26_parity/sc.sh`
  - Captures take about 300 B per record on the node's /tmp, which has about 760 GB free.
  - knn (11.8 G records) and tridiagonal (5.6 G records) therefore need a kernel prefix.
  - atomicCAS and expdist (about 390 GB each) fit, one at a time.
  - G1 has not yet been run for gpp, overlap, expdist, knn, tridiagonal or atomicCAS.
- **G2, the live recordings.** Run:
  `t26_parity/live_gate.py --label <app> --base <X11 r1> <r2> <r3> --new <rep1> <rep2> <rep3>`
  - The checks are: exact bytes, node set, edge set, per-edge totals, grand total, and drained records.
  - A check is enforced only if all baseline runs satisfy it on every kernel of the program.
  - A per-kernel rule overfits: X11's dxtc2 runs gain or lose a rare edge on 11 of 100 kernels, and other runs do so on other kernels.
  - Results on X12's 3 reps, all PASS:
    - gpp, overlap: every check enforced.
    - crs, fpc: every check except exact enforced.
    - mr: nodes, edges and grand total enforced.
    - dxtc2: nodes and grand total enforced.
  - A G2 FAIL is decided by G1 for that program, not waived.
  - For Indigo3 against C1, G2 needs at least 2 C1 recordings per id (parity-a, parity-b, main). Ids with a single recording get G1 on a sample instead.

Logs: `eval/x_logs/t26-sc-dbg-329305.log` (mr), `t26-sc-329320.log`, `t26-build-cap-kmax-329319.log`. Store: `/mnt/beegfs/fzheng4/t26/sc-{329305,329320}`.

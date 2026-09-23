# Host-memcpy (`cudaMemcpyAsync`) races: evidence, sizes, results (T2)

Branch `feat/host-memcpy` (worktree `/home/fzheng4/wt-T2`), based on `cuVein` @ `81b4262`,
rebased onto `6d843e3` (T5a merged).
Claude.md T2; the model is `design/host_memcpy_model.md`. Decision D5 (whether the paper's
scope includes host↔kernel and kernel↔kernel races) is the user's.

Legend: **measured** = a command ran and its output is quoted or saved; **read from the
code / header**; **unverified**.

## 1. Evidence: what the collector is told, and when (step 1)

Job 287916 on c20 (RTX 4060 Ti, sm_89, driver 610.43.02, CUDA 13.3 V13.3.73),
`setup/t2_evidence.sh`: the four cuHadron `asyncmemcpy` programs (P6 binaries, racy and
fixed) and the T2 micro test (`python/testdata/host_memcpy_race.cu`, four variants) under the
collector with **no instrumentation** (`accelprof -v -t code_check`: every API callback, no
per-access patch, so the 2.6e8 / 1.3e10 accesses of the shipped tests are not traced). The
callback sequences are saved as `setup/t2_evidence/order_<program>.txt`; the header facts
below are extracted into `setup/t2_evidence/sanitizer_api.txt`.

**1.1 The copy callback carries the streams; the collector drops them** (read from the
header and the code). `Sanitizer_MemcpyData` has `srcContext`/`dstContext`,
`srcStream`/`hSrcStream`, `dstStream`/`hDstStream`, `apiContext`/`apiStream`/`hApiStream`,
`srcAddress`, `dstAddress`, `size`, `width`/`height`/`depth`, `srcPitch`/`dstPitch`, `isAsync`
and `direction`. `Sanitizer_MemsetData` has `context`, `stream`/`hStream`, `address`, `width`,
`height`, `pitch`, `elementSize`, `value`, `isAsync`. The collector
(`nv-compute/src/compute_sanitizer.cpp`, `SANITIZER_CBID_MEMCPY_STARTING`) forwards only
`(dst, src, size, isAsync, direction, device)` through `yosemite_memcpy_callback`, and
`PcDependency::evt_callback` has no case for the resulting event.

**1.2 A latent swap** (read from the code): `yosemite_memcpy_callback(dst, src, …)` builds
`MemCpy_t(dst, src, …)`, but the constructor's parameters are `(src_addr, dst_addr, …)`, so
every tool receives the source as `dst_addr` and the destination as `src_addr`
(`sanalyzer/src/sanalyzer.cpp:177-183`, `sanalyzer/include/utils/event.h:168-186`). Seven
tools consume `MemCpy_t` (`app_analysis*`, `event_trace*`, `hot_analysis`,
`time_hotness_cpu`); fixing the order changes their output, so it is reported here and not
changed by T2 (T2 reads the fields it adds, not these two).

**1.3 When the copy callback fires** (measured). `MEMCPY_STARTING` fires at API-call time,
in host program order with the kernel launch callbacks. `memcpy_htod_kernel_race`, racy:

```
Launching kernel copy_kernel(int*, int*, unsigned long) <<<(1, 1, 1), (32, 1, 1)>>> ...
Kernel copy_kernel(int*, int*, unsigned long) finished on device 0
Memcpy 0x7f28c8000000 -> 0x7f2848000000 with size 1073741824, async: 1, direction: H2D
Synchronize context ... finished on device 0
```

The same program's fixed build shows the host wait between the copy and the launch
(`Memcpy … async: 1, H2D` / `Synchronize stream … finished` / `Launching kernel …`). In both
shipped tests the copy is issued **after** the racing kernel's launch (dtoh: `write_kernel` on
stream 1, then `Memcpy … async: 1, D2H` on stream 2).

**1.4 Stream/event ordering the Sanitizer offers** (header). Callback domains:
`SYNCHRONIZE` (`STREAM_SYNCHRONIZED`, `CONTEXT_SYNCHRONIZED`,
`GREEN_CONTEXT_SYNCHRONIZED`; data: context, stream, `hStream`) — enabled by the collector;
`EVENTS` (`CREATED`, `DESTROYED`, `RECORD`, `STREAM_WAIT`, `SYNCHRONIZE`; data: event,
context, stream, `hStream`) — **not enabled** by the collector; `RESOURCE` stream
created/destroy (context, stream, `hStream`; no flags). `Sanitizer_LaunchData` carries
`stream`/`hStream` and `apiStream`/`hApiStream`.

**1.5 Consequence** (measured). `kernel_memcpy_dtoh_race` racy and fixed produce the same
callback sequence (28 lines each; they differ only in addresses): the fix is
`cudaEventRecord` + `cudaStreamWaitEvent`, and the collector subscribes to neither. Today the
collector cannot tell the two builds apart even in principle; with the `EVENTS` domain and
the stream handles it can.

**1.6 Under the tool, launches are serialized** (read from the code): the collector drains
the kernel's device buffer before `LAUNCH_END` returns, so every run looks ordered. A verdict
must come from the API-level order (the model), not from whether the two operations
overlapped in the run.

**1.7 The micro test** (measured): `python/testdata/host_memcpy_race.cu` builds and runs in its
four variants (`racy`, `fixed`, `kfirst-racy`, `kfirst-fixed`; 256 ints, two non-blocking
streams), natively `no error`; under the collector each gives 25 callback lines in the
expected order (`racy`/`fixed`: H2D copy, then the launch; `kfirst-*`: the launch, then the
D2H copy), and, as for dtoh, each racy variant's sequence equals its fixed variant's up to
addresses: the event record/wait is invisible.

## 2. The model (step 2)

`design/host_memcpy_model.md`: one agent per stream plus the host; vector clocks over
streams; stream order, event record / stream wait, stream / event / context synchronize, the
legacy default stream's implicit synchronization with blocking streams, and the host-blocking
behaviour of each synchronous copy/set call. A copy reads its source range and writes its
destination range; a kernel reads/writes its global-memory footprint. Two operations race iff
their ranges conflict and neither happens before the other. The check runs at both points: a
kernel against earlier copies, and a copy against the retained footprints of earlier kernels —
both shipped cuHadron tests need the second, which the brief's first sketch (an interval set
checked inside the kernel) does not cover.

## 3. The prototype (step 3), behind `YOSEMITE_HB_HOST_MEMCPY=1`

* **Collector** (`nv-compute/src/compute_sanitizer.cpp`): with the flag set, every copy, set,
  launch (its stream, and whether the launch is monitored), stream creation (flags via
  `cuStreamGetFlags`, resolved with `dlsym` from the driver the application loaded), pinned
  host allocation, stream / context / event synchronize, event record and stream wait is sent to
  the tools as a `YosemiteHostOp_t` (`sanalyzer/include/sanalyzer.h`); the `EVENTS` domain is
  enabled only then. Unset, none of this code runs.
* **Tool** (`pc_dependency_analysis.cpp`): `EventType_HOST_OP` appends each operation to a
  file-static, program-level log, written as `<dump>/host_ops.json` at every kernel flush and
  at exit.
* **Analysis** (`python/host_hb.py`, both modes): replays the log with the kernels' footprints
  from their `hb_events`; `eval/baselines/run_cuvein._analyze_reports` adds the races as reports
  `global:host:<A>-<B>:<type>` (records marked `host`, class `host` or `host-spec-only`);
  `parallel.py` keeps `host_ops.json` with the kernel dumps; the two pc-pair classifiers
  (`classify_endpoints.py`, `classify_fp_causes.py`) skip host records. `sync_dominance.py`,
  `HbEngine` and `hb_oracle.py` are unchanged (engine = oracle is untouched; there is no engine
  part to mirror — model §5).

**Gating, measured** (job 287959, c20, `setup/t2_check.sh`; runtime = the T2 worktree's own
collector `64e01aea9b4296e6` + libsanalyzer `f89162e039ccf20b`, built by `setup/t2_build.sh`):
with the flag unset, the default tool path and the vector-clock dump of
`race_interblock_none-lock_rtraw` and `norace_interblock_atom` are identical to the installed
library's (up to device addresses, `setup/dump_compare.py`), and no `host_ops.json` is written;
with the flag set, the kernel dumps are identical to the unset run's and a `host_ops.json`
(8 operations) is added.

Two bugs found on the way (fixed before the measurements): the collector is not linked
against `libcuda`, so a direct `cuStreamGetFlags` call was an undefined symbol at run time
(job 287950: every micro-test run died at the first user stream); and the log, a
function-local static first used after the collector registered its `atexit` cleanup, was
destroyed before that cleanup's final write (a truncated `host_ops.json`) — it is now never
destroyed.

## 4. Results (step 4)

**Micro test** (`python/testdata/host_memcpy_race.cu`, job 287959), both modes, identical:

| variant | host races | report |
|---|---|---|
| racy (H2D copy on stream a, then a kernel on stream b reads) | 1 | RAW: copy vs `touch` read @0x90 |
| fixed (`cudaEventRecord` + `cudaStreamWaitEvent`) | 0 | — |
| kfirst-racy (kernel on a writes, then D2H copy on b) | 1 | RAW: `touch` write @0xa0 vs copy |
| kfirst-fixed | 0 | — |

**Reduced-size cuHadron programs** (`setup/t2_small_build.sh`: each size constant becomes a
compile-time define with the shipped default, built small; `setup/manifest.t2small.csv`), through
`parallel.py` in both modes (job 287961, c20; re-scored with the spec-only tag, job 287965;
`eval/results/t2-host-rescore/`), and without the flag (`eval/results/t2-host-off/`):

| program (racy / fixed) | without flag | with flag: host races (spec-only of them) | in-kernel reports | verdict, spec reading | verdict, practical reading |
|---|---|---|---|---|---|
| asyncmemcpy/memcpy_htod_kernel_race | CLEAN / CLEAN | 1 (0) / 0 | 0 / 0 | RACE / CLEAN | RACE / CLEAN |
| asyncmemcpy/kernel_memcpy_dtoh_race | RACE / RACE | 3 (2) / 2 (2) | 44 / 44 | RACE / RACE | RACE / RACE |
| interkernel/global_readwrite_race | CLEAN / CLEAN | 3 (2) / 2 (2) | 0 / 0 | RACE / RACE | RACE / CLEAN |
| interkernel/global_writewrite_race | CLEAN / CLEAN | 3 (2) / 2 (2) | 0 / 0 | RACE / RACE | RACE / CLEAN |

(The two modes agree on every row.) The intended race of every racy build is found and none
remains on a fixed build under the practical reading: htod `k0@0x100 vs memcpyH2D` WAR (the
kernel reads, then the async copy overwrites), dtoh `k0@0x890 vs memcpyD2H` RAW, the two
inter-kernel pairs (`k0-k1` RAW / WAW). The spec-only reports are the programs' own
initialization: a synchronous pageable `cudaMemcpy` H2D (inter-kernel) or a `cudaMemset`
(dtoh) on the legacy stream, then kernels on **non-blocking** streams, which do not wait for
the legacy stream.

**`kernel_memcpy_dtoh_race` has an in-kernel race in both builds** (44 WAW pc pairs, with and
without the flag, both modes): `write_kernel` writes `dst[(idx + i*stride) % N]` for
`i < 200`, `stride = N/32`, and threads whose `idx` differ by a multiple of `stride` write the
same element; the final `dst[idx]` store overlaps those too. Its fixed build is therefore not
race-free for an in-kernel detector, host ordering aside (read from the source; the reduced
build keeps the shipped `stride = N/32` relation).

## 5. Cost (step 5)

Five P6 programs (`setup/t2_cost_ids.txt`: memcpy/global_readwrite fixed, memcpy/shared_readwrite
racy, intersubwarp shared readwrite/writewrite racy, hostdevice/global_readwrite racy), both
modes, flag on vs off on the same node in one job (287961): identical verdicts and report ids
on all ten (program, mode) pairs; wall 0.88–1.57 s vs 0.88–1.57 s, peak 849–865 MB either way
(single repetition; the differences are run-to-run noise at this size). `hostdevice/*` (a
host thread touching memory a kernel uses) stays out of scope: host-thread accesses are not
instrumented.

**Green set** with the T2 runtime (job 287961, c20): 148 passed, 1 xfailed — the standard
136 + 1 xfail (`test_relaxed_handoff_should_race`) and 12 `python/test_host_hb.py` unit tests
(13 now, with the spec-only case; `.env/bin/python -m pytest python/test_host_hb.py`, no GPU).

**After rebasing onto T5a** (`cuVein` @ `6d843e3`; one conflict in `pc_dependency_analysis.cpp`,
both sides kept), job 287972 on c20 with the combined library (`698e6aec2432a206`, collector
unchanged): the gating comparisons above hold, `YOSEMITE_HB_STATS=1` adds only its `hb_stats`
field, the micro test gives the same four results in both modes, and the green set gives 149
passed, 1 xfailed (136 + 13 `test_host_hb.py`).

## 6. For decision D5

* Host↔kernel and kernel↔kernel races are reachable: the collector sees every operation and
  every ordering call it needs once it forwards the streams and enables the `EVENTS` domain.
* With the prototype on, the four cuHadron host/inter-kernel programs (reduced size) give the
  intended verdict on all eight builds under the practical reading, in both modes; under the
  spec reading the three that initialize memory with synchronous calls on the legacy stream and
  then launch on non-blocking streams are also RACE in their fixed builds.
* Re-labelling the P6 rows needs (a) the choice of reading, (b) a note that
  `kernel_memcpy_dtoh_race` fixed carries a genuine in-kernel race, and (c) the reduced sizes
  stated in the manifest (they are: `input` = the defines).

## 7. What remains unverified

* The shipped sizes: not run (2.6e8 / 1.3e10 accesses; the reduced builds keep each program's
  host-side structure, only the constants shrink).
* Multi-threaded hosts, the per-thread default stream, CUDA graphs, host callbacks, peer copies
  and managed memory (model §6, A1–A3); polling-based synchronization (A2) — no program here.
* `cuStreamGetFlags` inside the stream-creation callback worked on every stream here (user
  streams report `flags: 1`, the context's internal streams `0xffffffff` = unknown, treated as
  blocking); whether it can fail in other drivers is unverified.
* 2D/3D copies and sets (row ranges) and `cudaMemcpyDefault`: implemented from the header,
  no test program exercises them.
* Only sm_89 (RTX 4060 Ti, driver 610.43.02).

## 8. Commands

```
sbatch -p rtx4060ti8g -w c20 --export=ALL,PIN8G=1 eval/baselines/setup/t2_evidence.sh   # §1  (job 287916)
sbatch -p normal eval/baselines/setup/t2_build.sh                                       # private runtime (287958)
sbatch -p rtx4060ti8g -w c20 --export=ALL,PIN8G=1 eval/baselines/setup/t2_check.sh      # §3, micro test (287959)
sbatch -p rtx4060ti8g -w c20 --export=ALL,PIN8G=1 eval/baselines/setup/t2_eval.sh       # §4-5, green set (287961)
TAG=t2-host OUT=t2-host-rescore CV=/home/fzheng4/wt-T2 ACCEL_PROF_HOME=/home/fzheng4/wt-T2 \
  MANIFEST=eval/baselines/setup/manifest.t2small.csv sbatch --array=0 eval/baselines/setup/p_analyze_cpu.sh  # (287965)
.env/bin/python python/host_hb.py <dump dir>         # one program's host races, no GPU
```
Stores: `/mnt/beegfs/fzheng4/cuvein_traces/{t2-host,t2-host-off,t2-cost-on,t2-cost-off}`.

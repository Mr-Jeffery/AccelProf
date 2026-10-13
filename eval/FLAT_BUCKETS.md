# T19: flat per-location buckets

Branch `perf/flat-buckets`, based on `cuVein` d67ed41 (T4 `feat/no-dump` merged) plus the
runtime install commit 59b239a. Design note: `design/flat_buckets.md`. Written 2026-10-05.
Code: 6f6adcf (first layout, "v1") and 67675e4 (the adopted layout, "v4").

Runtimes measured, each a private libsanalyzer built with GCC 12.4.0 (`-g -O3 -mtune=znver4`)
and a collector relinked from the installed collector's objects with RPATH to that library:

| name | libsanalyzer | collector | what |
|---|---|---|---|
| before | `9ae97c27` | `1c896ce0` | the installed runtime, d67ed41 (node-based buckets) |
| v1 | `65dc4425` | `9b386f95` | 6f6adcf: 20-byte slots, 32-slot tail, one open-addressing location table |
| v2 | `bbe56e0e` | `ffc9457e` | v1 with an 8-slot tail and an allocation-free merge |
| v3 | `adcec1a3` | `a71d9087` | v2 with a locality-preserving home slot in the table |
| **v4** | **`31549a8f`** | **`367b4d65`** | **67675e4: v2 with a segment-directory index (adopted)** |

All five use the installed fatbins (default `a2d7368bc1c61986`, late `e96343121c74ca0a`).
Hardware: RTX 4060 Ti 16 GB nodes of `rtx4060ti16g` (sm_89, driver 580.82.07); CPU work ran
on `normal` nodes. Legend: **proved-in-effect** means an invariant checked over the stated
traces; **tested** means a specific result asserted by a test.

## 1. What changed

`HbClock::buckets` keeps the same entries, one per (location, thread, key), in a different
layout (design note §2). The rest of `HbClock`, `hb_oracle.py`, the collector and the device
code are unchanged.

| | before (d67ed41) | after (67675e4) |
|---|---|---|
| location index | `std::map<Loc, std::vector<KeyGroup>>` | 4-byte-aligned locations: 128-byte segments (32 `LocSlots` headers, 512 B) behind an open-addressing directory with a one-entry cache. Other locations: an open-addressing table. |
| key group | `KeyGroup { kind, scope, std::unordered_map<Tid, Entry> }` | a run of the location's array, sorted by (key, tid), or slots of its tail |
| entry | hash node: next ptr + (Tid, {u64, u64, u32}), 48-byte chunk + bucket ptr | `Slot { u32 tid, u32 clock, u32 sclock, u32 pc, u8 key }`, 20 B, in one `realloc`'d array per location |
| own-slot lookup | `by_tid[t]` hash | binary search in the sorted prefix + a scan of the tail (< 8 slots) |
| Check | per group: skip, or iterate the hash map | per sorted run: skip by binary search on the key, or iterate; the tail slot by slot with the same test |

Exactness conditions, all checked rather than assumed:
- A tid that does not fit 31 bits (an async agent, or a grid of 2²¹ blocks or more) goes
  through a side table.
- An epoch at or above 2³² aborts with a message instead of wrapping.

`HB_STATS` `buckets` carries:
- `bytes`: the new layout (directory, segments, the unaligned table, each array's malloc
  chunk, the side table);
- `segments`;
- `bytes_est`: the pre-T19 layout's estimate for the same entries.

`t4_sweep_table.py` and `t5b_stats_table.py` keep reading `bytes_est`.

**Output order.** No output iterates the location index. Within a location, the order in which
Check visits entries decides only which instance becomes an `hb_races` aggregate's
representative (`addr`, `a_tid`, `b_tid` and its list position). Counts, classes,
`a2_uncertain`, `hb_races_sync_only`, `hb_sync_pass` and the coherence profile are unaffected.
The verdict layer reads representative tids only through the distance, which is part of the
aggregate key (design note §2.3). The old order was libstdc++'s hash order and already
differed from the specification's; every parity check compares at the aggregate key.

## 2. Parity (step 3)

| check | v1 | v4 (adopted) |
|---|---|---|
| green set (CLAUDE.md A4 files + `test_instance_gate.py`) + `test_no_dump.py`, every trace re-recorded (`setup/t4_check.sh`) — tested | **332 passed, 2 skipped, 0 failed** (job 301509) = 305 + 2 skipped, plus 27 | **332 passed, 2 skipped, 0 failed** (job 302125) |
| `test_instance_gate.py` alone on those artifacts (`setup/t19_gate.sh`) | **55 passed** (job 301525) | in the 332 above |
| implementation == specification, T5b's 65-program set, vector-clock dumps (`p_t5b_timeout.sh` recording at the 120 s floor + `t5b_parity.py`) — proved-in-effect | **59/59 programs that dumped, 390 kernels, 0 mismatches** (jobs 301510, 301527) | **59/59, 394 kernels, 0 mismatches** (jobs 302126, 302127) |
| no-dump aggregates == records, the same recordings, both modes (`t4_parity.py`; T4's check on 56 programs × 2 modes instead of the brief's 20) — proved-in-effect | **796 kernel JSONs: 790 equal, 0 mismatches**; 6 (CC_V_Topo_Pull 1296n, scalar-clock, kernels 9–14) hit the 3,600 s per-program cap of the Python side (job 301528) | **805 kernel JSONs: 805 equal, 0 mismatches**, 12 above the cutoff; with a 25,000 s per-program cap the CC 1296n kernels complete (job 302128) |
| verdicts against T4's recording of the same 65 programs (T4 runtime; `wt-T4/eval/results/t4-parity{,-fix}`) | 130 rows: **no verdict differs**; 5 RACE rows differ by 1–2 reports | 130 rows: **no verdict differs**; 3 RACE rows differ by 1–2 reports |
| default tool path (no `YOSEMITE_HB_TRACE`), installed vs private runtime, `race_interblock_none-lock_rtraw` and `norace_interblock_atom` | identical up to device addresses and dist histograms **except `kernel.kernel_pc`** | the same |

v2 and v3 passed the same green set (332 + 2 skipped). v2's implementation == specification
check: 60/60 programs, 409 kernels, 0 mismatches.

The 1–2 report differences come from three programs: P4 graph-coloring-racy-small,
graph-connectivity-racy-small, and PI populate_worklist…atomicBug. They appear in
scalar-clock mode too, whose verdicts in these dump recordings come from the records rather
than from `HbClock`. Each runtime equals the specification on its own trace. So they are
run-to-run schedule differences of contended atomics.

`kernel_pc`: `KernelLaunch::kernel_pc` (`sanalyzer/include/utils/event.h:83`) is never
assigned in sanalyzer, so the default dump prints uninitialised heap memory. It reads 1 under
the installed runtime and 0 under every private one; any change to the library's allocation
pattern can flip it. This is pre-existing (T4's check happened to see equal garbage) and is
not a T19 output.

A re-score of kept dumps cannot move a verdict here: it runs the Python oracle and verdict
layer, which T19 does not touch. The re-recorded comparisons above are the tests that can.

## 3. Memory (step 4)

Script `setup/t19_long.sh`: T4's `t4_long.sh` writing to `/mnt/beegfs/$USER/t19-long*`.
Settings: `accelprof` run directly, `YOSEMITE_HB_DUMP=0`, `YOSEMITE_HB_STATS=1`,
`YOSEMITE_HB_STATS_EVERY=2000000`, scalar-clock then vector-clock. Nodes are T4's where
possible: stencil1d c60 (188 GB), lavaMD c3, tridiagonal c79. particlefilter ran on c61
(188 GB); T4's c23 has 125 GB, and the brief asks for a 188 GB node.

### 3.1 Outcomes

| program | mode | T4 (`NO_DUMP.md` §4.3, cap 5,400 s) | v1 (cap 5,400 s) | v4 |
|---|---|---|---|---|
| stencil1d | scalar-clock | dies at 174 GB after 1,050 s, 0 kernels | killed at the cap after **3 kernels**; RSS at kernel end 136 GiB | killed at the 3,600 s cap after **3 kernels**; RSS at kernel end **111 GiB** |
| stencil1d | vector-clock | dies at 174 GB after 1,034 s | dies at 174 GB after 1,594 s, 0 kernels | killed at the 3,600 s cap after **2 kernels**; RSS at kernel end **130 GiB** (`vc` 268 M entries for 134 M threads + 74.4 GB of buckets) |
| particlefilter | scalar-clock | dies at 122.6 GB after 938 s, 3 kernels | dies near 190 GB after 3,307 s, 3 kernels | killed at the 1,800 s cap set for this run (to reach 64 M records), 3 kernels |
| particlefilter | vector-clock | dies at 122.8 GB after 1,068 s | dies near 190 GB after 3,594 s, 3 kernels | not run |
| lavaMD | scalar-clock | finishes, 3,214 s, 64.9 GB | finishes, 3,941 s, RSS 20.9 GiB | finishes, 3,858 s, RSS 25.1 GiB |
| lavaMD | vector-clock | finishes, 3,614 s | killed at the cap (5,400 s) | killed at the cap (5,400 s) |
| tridiagonal | scalar-clock | killed at the cap after 15 kernels | killed at the cap after 17 kernels | 6 kernels in 1,800 s |
| tridiagonal | vector-clock | killed after 13 kernels | killed after 14 kernels | not run |

stencil1d launches 1,000 kernels of about 20 minutes (v4) to 30 minutes (v1) each, so no cap
I can run lets it finish.
The T4 column was recorded with T4's first build (2fc83fe0), so its times are not a same-build
comparison. §4.2 has the same-node, same-script comparison for lavaMD.

### 3.2 Bucket bytes against the pre-T19 layout

At the same entry count. "T4's `bytes_est`" is the measured estimate T4 printed for its own
runs.

| program, point | entries | locations | v1 `bytes` | v4 `bytes` | T4's `bytes_est` | v4 / T4's |
|---|---|---|---|---|---|---|
| stencil1d, 32 M records | 904.6 M | 152.6 M | 33.4 GB | **27.6 GB** | 101 GB | **0.27** |
| stencil1d, kernel end (scalar-clock) | 2,430.6 M | 410.0 M | 101.1 GB | 74.4 GB | (never reached) | — (0.35 of this branch's own old-layout estimate, 214 GB) |
| particlefilter, 64 M records of kernel 4 | 2,047.3 M | 233 K | 49.9 GB | 49.9 GB | 122 GB | 0.41 |
| lavaMD, kernel end | 866.8 M | 33.1 M | 23.5 GB | 22.3 GB | 60.8 GB | 0.37 |
| tridiagonal, kernel end | 232.5 M | 38.4 M | 8.57 GB | 7.12 GB | 25.5 GB | 0.28 |

**The acceptance bar (bucket bytes ≤ 25 % of before on the four step-4 programs) is not met.**
v4 reaches 27–28 % on stencil1d and tridiagonal (6 entries per location) and 37 % on lavaMD
(26 per location); particlefilter is 41 %.

Per entry, v4 costs:
- stencil1d and tridiagonal: about 30 B. The 20-byte slot, plus the array's growth slack and
  malloc header, which weigh a lot when an array holds 6 slots.
- lavaMD: about 26 B.
- particlefilter: about 24 B. A 20-byte slot plus ×1.5 growth slack, on about 12,000 entries
  per location.

The old layout cost 56–112 B per entry, with 112 B only where locations are small. So the
brief's ×5, which assumed ~110 B everywhere, does not hold where locations are large.
Reaching ≤ 25 % everywhere would take 16-byte slots (the key moved to a per-run header) and
arrays carved from per-segment arenas. Not attempted.

**particlefilter cannot fit any per-entry layout on a 188 GB node.** Its entries grow by about
32 per record without levelling off: 2.05 G at 64 M records, 4.09 G at 128 M (v1: 101 GB).
T4's 2.05 G was where its run died, not the kernel's total. The v1 run died near 190 GB at
about 250 M records, so the kernel holds well over 4 G entries (roughly 8 G at the observed
growth) — 160 GB or more at 20 B each. Theorem "Sound" forbids merging those reader entries
across threads (`NO_DUMP.md` §4.3).

**lavaMD RSS on v4 (25.1 GiB) is higher than on v1 (20.9 GiB),** although v4's bucket bytes
are lower (22.3 vs 23.5 GB). The difference is outside what `HB_STATS` counts: the heap after
`calloc`'d segments and `realloc`'d arrays. Not investigated further.

## 4. Time (step 5)

### 4.1 The step-5 programs

All runs were on c50, AMD EPYC 9115 (Zen 4), the node of T4's A/B: the before runtime and
each variant back to back on the same node. Settings: no-dump mode, `HB_STATS` at kernel end
only (`setup/t19_time.sh`; jobs 301524 for before + v1, 301767 for v2, 301912 for v3, 302129
for v4). T5a's three ran through `t5a_stats.py`; hotspot and fpc through `t19_long.sh`.

Wall time, with peak RSS:

| program (mode) | before | v1 | v2 | v3 | **v4** |
|---|---|---|---|---|---|
| tiled_gemm N=256 (vector-clock) | 10.1 s, 1.18 GB | 6.1 s, 0.99 GB | 6.3 s | 6.3 s | **5.4 s, 0.98 GB** |
| reduction-norace large (vector-clock) | 3.4 s, 1.21 GB | 1.5 s, 0.98 GB | 1.3 s | 1.2 s | **1.1 s, 0.92 GB** |
| Indigo3 CC push 1296n (vector-clock) | 6.1 s, 1.23 GB | 5.1 s, 1.13 GB | 4.9 s | 5.5 s | **5.2 s, 1.13 GB** |
| P7-hotspot (vector-clock, 100 kernels) | 499 s, 2.00 GB | 315 s, 1.40 GB | 327 s | 290 s | **212 s, 1.17 GB** |
| P9-fpc (scalar-clock, 202 kernels) | 1,237 s, 3.10 GB | 888 s, 2.30 GB | 915 s | 729 s | **730 s, 2.08 GB** |

Per lane-access (whole wall over the summed `hb_lanes_count`, so the sanitizer and the
collector are included), before → v4:
- hotspot (740.6 M lane-accesses): 0.67 → 0.29 µs.
- fpc (883.7 M lane-accesses): 1.40 → 0.83 µs.

**Every step-5 program is faster on v4**: 15–67 %, with hotspot 2.4× and fpc 1.7×. fpc in
scalar-clock no-dump mode, T4's regression, now finishes well inside the harness's 1,200 s cap
on this node.

### 4.2 lavaMD: slower on every flat variant

lavaMD is not a step-5 program, but its step-4 runs showed it slower. Same node (c3), same
script, scalar-clock, full input (`-boxes1d 30`, one kernel of 398.8 M records):

| runtime | wall |
|---|---|
| before | **3,162 s** (job 301647) |
| v1 | 3,941 s (+25 %) |
| v2 | 3,874 s (+23 %) |
| v3 | 4,551 s (+44 %) |
| v4 | 3,858 s (+22 %) |

Vector-clock mode, same node and script:
- before **finishes in 3,505 s** (job 302245);
- v4 is killed at the 5,400 s cap (job 302091), so **at least +54 %**;
- v1 also did not finish within 5,400 s.

The vector-clock gap is larger than the scalar-clock one. That fits the explanation below:
vector-clock mode adds a per-thread `vc` lookup to every conflict test.

A reduced input (`-boxes1d 12`, `setup/t19_ab_small.sh`, one node, interleaved reps) shows the
same ordering at a smaller gap. On c76 (EPYC 7302P): before 285/289 s, v1 299/304 s, v2
298/308 s, v3 336/332 s. On c65 (EPYC 8124P): before 244/248 s, v1 258/264 s, v4 254/257 s.

Why: the profiles of those runs (perf, by source line, last rep of each runtime) show the cost
did not move into the buckets.
- The old layout spent about 40 % of its samples in `std::map` walks over locations. The flat
  layouts remove almost all of that; v4's directory probe is about 1 %.
- But per-thread work that is identical in every version takes about 2.4× the absolute time
  under the flat layouts: the `unordered_map<Tid, …>` lookups for `vs` and `rmw_thr` (about
  45 s → 109 s), and `rmw_note`'s linear `std::find` over a thread's pending pcs (about 28 s →
  64 s).

That pattern is cache and TLB pressure on per-thread state, and its exact mechanism is not
established. My guess: under the old layout, each thread's own entries were allocated in time
order next to other recently touched data, and lavaMD's read-heavy, medium-sized locations
(about 26 entries each) did not touch other threads' entries on a read. Neither the shorter
tail (v2) nor locality in the index (v3, v4) removes it. It grows with the working set: about
4 % on the reduced input, 22 % on the full one.

### 4.3 Where the remaining time goes (attribution for T7)

perf (`-F 49 --call-graph dwarf`) over one no-dump run each, with the v1 runtime:
- hotspot vector-clock and fpc scalar-clock (`setup/t19_profile.sh`, job 301534, c73,
  EPYC 7302P);
- lavaMD scalar-clock, its first 1,200 s (job 301646, c65).

Re-reported by source line (`setup/t19_perf_lines.sh`) and grouped by the function ranges of
6f6adcf (`setup/t19_perf_attr.py`). Self time, as a percentage of all samples:

| part | hotspot (vc) | fpc (sc) | lavaMD (sc) |
|---|---|---|---|
| clocks: per-thread `vs`/`vc` lookups (`unordered_map<Tid, …>`), base binary searches, joins (T5b) | 17.9 | 5.3 | 26.1 |
| R3 trace points (`rmw_note`, T4): a per-lane `rmw_thr[t0]` hash lookup | 7.2 | 3.5 | 23.2 |
| inlined STL in `process` that the line table cannot place; on lavaMD mostly `rmw_note`'s linear `std::find` (`stl_algobase.h:2072`, 13.6 %) | 8.2 | 0.6 | 29.6 |
| buckets: v1's location-table probe + slot arrays | 14.6 | 9.3 | 5.6 |
| buckets: Check scan + replace | 1.1 | — | 4.8 |
| allocator: `free`/`malloc_consolidate` under `hb_clock_reset` at kernel start (the previous kernel's state torn down; the clears are inlined, so which container is not separable) | 12.0 | 24.8 | <0.2 |
| `HB_STATS` scan (measurement only; the profile run sets `YOSEMITE_HB_STATS=1`) | 7.9 | 15.4 | — |
| the rest of the listed lines (barrier/exit assembly, A2 windows + gate, emit, reset, record decode, collector callback, dependency tool, unplaced) | 5.6 | 12.7 | 0.7 |
| lines below perf's 0.2 % listing threshold | 25.6 | 28.2 | 9.9 |

v4 cut the bucket rows further: hotspot went from 315 s to 212 s between v1 and v4. What
remains is per-thread state looked up per lane in node-based hash maps keyed by `Tid`, plus
T4's R3 bookkeeping:
- `rmw_thr` is an `unordered_map<Tid, RmwThread>` with a `std::vector` of pending pcs searched
  linearly on every non-RMW access. On lavaMD (3.46 M threads) it is the largest single cost.
- `vs[t]` and `V(t)` are hash lookups on every conflict test.

On programs with many short kernels (fpc: 202 kernels × 4.2 M locations) the teardown at each
kernel start is the largest part.

The items for T7:
- a dense per-warp array for `rmw_thr`, `last_pc` and `vs`, indexed by (block, warp, lane);
- a set or bitmap instead of `rmw_note`'s linear `std::find`;
- reusing the index and arrays across kernels instead of freeing them.

Record decoding and the drain handshake are small in all three profiles: record decode +
dispatch < 1 %, collector callback 0.3–1.9 %.

## 5. The GPU side

Untouched: no collector or device source changed (`git diff d67ed41 67675e4 -- nv-compute` is
empty). Every private collector was relinked from the installed collector's objects. The
fatbins used are the installed ones: `gpu_patch_pc_dependency.fatbin` `a2d7368bc1c61986`,
`_late` `e96343121c74ca0a`.

## 6. Commands

```
# private runtimes (GPU-partition node for /usr/local/cuda); v2-v4 with INSTALL=<wt>/sanalyzer/wt_installN RTLIB=<wt>/wt_rt_libN
sbatch -p rtx4060ti8g -x c21,c22,c34,c54,c2 eval/baselines/setup/t19_build.sh   # v1 301366, v2 301758, v3 301903, v4 302087
# runtime mirrors for RT=: <wt>/rtN = {bin, lib -> wt_rt_libN, build, .env, nv-compute/lib}
# step 3 (worktree lib -> the variant under test)
W=<wt> sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t4_check.sh          # v1 301509, v4 302125
sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t19_gate.sh                 # v1 301525
W=<wt> IDS=eval/baselines/setup/t5b_parity_ids.txt TAG=t19-parity[-vN] BASELINE_MODES=vector-clock,scalar-clock \
  FLOOR=120 sbatch --array=0-7 eval/baselines/setup/p_t5b_timeout.sh                       # v1 301510, v4 302126
W=<wt> TAG=... sbatch --dependency=afterany:<recording> eval/baselines/setup/p_t5b_parity_cmp.sh     # v1 301527, v4 302127
W=<wt> TAG=... [CAP=25000] sbatch --dependency=afterany:<recording> eval/baselines/setup/p_t4_parity_cmp.sh   # v1 301528, v4 302128
# step 4 (one program per job, pinned)
[RT=<wt>/rt4 OUTDIR=t19-long-v4] W=<wt> IDS=eval/baselines/setup/t19_ids/<p>.txt CAP=<s> \
  sbatch -w <node> --array=0 eval/baselines/setup/t19_long.sh
# step 5 and the lavaMD A/B
RUNTIMES="before after" | after2 | after3 | after4 sbatch -w c50 eval/baselines/setup/t19_time.sh
RT=/home/fzheng4/AccelProf OUTDIR=t19-long-before MODES=... sbatch -w c3 eval/baselines/setup/t19_long.sh
PERF=1 RTS="before=... v1=<wt>/rt1 v4=<wt>/rt4" sbatch eval/baselines/setup/t19_ab_small.sh  # 302046, 302090
sbatch ... eval/baselines/setup/t19_profile.sh; DIRS=... sbatch ... t19_perf_lines.sh; sbatch ... t19_perf_alloc.sh
python3 eval/baselines/setup/t19_perf_attr.py eval/baselines/setup/t19_perf/*.lines.txt
T19_RUNTIMES="before after4" .env/bin/python eval/baselines/setup/t19_tables.py time   # on a node with BeeGFS
```

Kept on BeeGFS (`/mnt/beegfs/fzheng4/`): `cuvein_traces/t19-parity{,-v2,-v3,-v4}`,
`t19-long{,-before,-v2,-v3,-v4}`, `t19-time-{before,after,after2,after3,after4}`,
`t5a_stats/*`, `t19_profile`, `t19-ab-small`.

## 7. What remains unverified / not done

- **Acceptance:**
  - Step 3 parity is clean for v4.
  - Wall time is better on every step-5 program.
  - No verdict moves against T4's recording.
  - **Bucket bytes are 27–41 % of before, not ≤ 25 %** (§3.2).
  - **lavaMD, a step-4 program, is slower than the old layout on every flat variant: +22 % in
    scalar-clock mode, at least +54 % in vector-clock mode** (v4: 3,858 s vs 3,162 s; more than
    5,400 s vs 3,505 s; §4.2). Its cause is located (per-thread state), not removed.
  - Neither stencil1d nor particlefilter produces a verdict in either mode. stencil1d's
    kernels now complete and fit in memory in both modes (111 GiB scalar-clock, 130 GiB
    vector-clock; before, both modes died at 174 GB with 0 kernels), but it launches 1,000 of
    them at about 20–30 minutes each. particlefilter needs more than 160 GB of entries under
    any per-entry layout.
- The default-path comparison is identical except the uninitialised `kernel_pc`. Fixing that
  field would change the default tool's output, which A3 reserves. It is reported, not fixed.
- My first `t4_check.sh` run reused its fixed output directory
  `/mnt/beegfs/fzheng4/t4-check` and wiped it first. That deleted T4's kept default-path
  comparison recordings (two ScoR programs, regenerable); T4's report cites the job's log.
- My first v3 parity comparisons were submitted with a dependency on the wrong job and read
  a partly written store. They were discarded and re-run; v3 is not adopted.
- Each time comparison is one run per configuration (two reps for the reduced lavaMD) on one
  node. Run-to-run variance on one node is about 1–3 % where measured (the reduced-lavaMD
  reps).
- The perf attribution is self time at 49 Hz with v1, over the first 1,200 s for lavaMD. It
  places code inlined into `HbClock::process` by source line; 9.9–28.2 % of samples are in
  lines below perf's listing threshold.
- The epoch-overflow abort and the wide-tid side table for grids of 2²¹ blocks or more are not
  exercised by any test; cp.async agents exercise the side table.

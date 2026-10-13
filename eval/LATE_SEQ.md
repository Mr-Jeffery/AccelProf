# T15 — Late ordering key for the HB records (A2 mitigation, measured)

Branch `perf/late-seq`, base `cuVein` f61c389 (T10 + T14 merged). Hardware: RTX 4060 Ti 16 GB
(sm_89), nodes c23 (driver 580.82.07), c77 (580.95.05), c78 (580.82.07); CUDA 13.3, GCC 12.4.0.
Private runtime: collector `fc964ef246c4f4ff`, libsanalyzer `ffd3736d23c8b3f4`, pc_dependency
fatbin `e96343121c74ca0a` (job 293643). Logs: `eval/results/t15-late-seq/`.

## Result, and the sentence for D15

**Not adopted; the default stays off (`YOSEMITE_HB_LATE_SEQ` unset = 0).** On the lock idiom,
a key drawn as the callback's last action (an `atomicAdd` on a separate counter, after the
record's commit) lowers the Sanitizer collector's hand-off inversions from 45/315 to 40/315 at
4 warps and from 212/1,274 to 187/1,274 at 16 warps. These are the same traces scored in both
orders, so the comparison is paired: a 12 % relative drop, not the order of magnitude step 4
asks for. `%globaltimer` cannot order these records at all: 87 % of the keys tie at 16 warps.
W0 held on every late-keyed dump and no TV check fired.

For D15: *"Drawing the collector's ordering key as the last action of the callback — after
the record is written and committed, immediately before the instruction — reduces the measured
inversion rate by only about a tenth (14.3 → 12.7 % at 4 contending warps, 16.6 → 14.7 % at 16,
same traces); A2's exposure is a property of issue-point recording, not of where in the callback
the key is taken."*

A correction to the premise (CLAUDE.md B2, 09-29 status, and D15's "T15 measures the late
ordering key"). The explanation of the 7–25× gap to NVBit was that "NVBit's tool drew its key
last". T13's `atom_after` does not. Its `emit` (`eval/nvbit_spike/atom_after/inject_funcs.cu:17-28`)
draws `seq` with `atomicAdd` first and then calls `ChannelDev::push` (NVBit 1.8
`core/utils/channel.hpp:60-95`). `push` does a second global `atomicAdd` on the buffer head and
waits for its value, then a `memcpy` of the record and a third `atomicAdd` on the tail. So
NVBit's window between key and instruction holds at least as much as the Sanitizer's did. The
gap between the two rates is therefore not explained by where the key is drawn, and T15's
measurement agrees. It remains unexplained. The measured difference between the tools is the
schedule each perturbation produces (§4).

## 1. What was built (step 1)

HB-trace path of the pc_dependency tool only. Every other tool and the default path get
nullptr in the new tracker fields and run the old code.

- **Device** (`nv-compute/gpu_src/gpu_patch_pc_dependency.cu`): `CommitRecord` replaces
  `IncrementNumEntries` at the three commit sites (memory records, sync records, exits). With
  `tracker->late_keys` set, the committing lane does `__threadfence`, then `atomicAdd(numEntries)`,
  then stores `late_keys[slot] = DrawLateKey()`. That store is its last action, apart from the
  full-buffer check. The key is `atomicAdd(late_counter, 1) + 1` (`late_mode` 1) or
  `%globaltimer | 1` (`late_mode` 2). A `__syncwarp(active_mask)` after the commit keeps a
  non-committing lane from reaching its next record, and that record's key, before this record's
  key is drawn. Without it, W0 could fail under the late key (see §2). The lane whose commit fills the
  buffer draws its key before ringing the doorbell and waiting for the drain. It has to: the
  drain needs the key. So for 1 record in 2,097,152 the key precedes a drain wait.
- **Where the key lives:** a side array `late_keys[MEMORY_ACCESS_BUFFER_SIZE]` in device memory,
  parallel to the record buffer. `MemoryAccess` is unchanged, so no reader of the record sees a
  new field. `MemoryAccessTracker` gains three trailing fields (`late_keys`, `late_counter`,
  `late_mode`). Because they come after all existing fields, the other patches' field offsets
  are unchanged.
- **Collector host** (`nv-compute/src/compute_sanitizer.cpp`): `YOSEMITE_HB_LATE_SEQ=1|atomic|timer`
  is read only when `YOSEMITE_HB_TRACE` is set; any other value is an error. The buffers are
  allocated and zeroed per launch. Before each drain, `late_keys_drain` re-copies the keys until
  none is 0; the kernel is still running and each key store follows its commit, so a key can land
  late. A key still missing after 30 s is a hard error. The collector then zeroes the array
  before releasing the doorbell and hands the keys to the tools through the new
  `yosemite_gpu_data_late_keys`. A buffer's keys all precede the next buffer's, because its slots
  are reissued only after the drain.
- **Tool** (`sanalyzer/src/tools/pc_dependency_analysis.cpp`): each drain is sorted by
  (key, slot), and both the `hb_events` serializer and `HbEngine::process` consume it in that
  order (the engine gains only an iteration-order argument). `seq` follows the late order. Every
  event carries `"bpos"` (its position in the kernel's buffer stream, the order of every earlier
  dump) and `"lkey"`, and the dump is marked `"hb_late_seq": 1, "hb_late_seq_key": "atomic"|"timer"`.
  Oracle and `barrier_only_pairs` are unchanged. The state is in file statics, not `PcDependency`
  members (the header's UB note).

## 2. Trace validity (step 2)

`tv_check` does not exist yet (T11). The W0 check is `eval/baselines/late_seq.py prep` (function `check`): per
thread, `lkey` must rise along `bpos`. `bpos` order is program order, because a thread's slot is
drawn before its record's first `__syncwarp`. The same script also checks that the dumped `seq`
is the (lkey, bpos) order. In addition, the engine's in-process TV monitor ran with strict on
(the default).

| dumps | events | thread histories | W0 violations | seq ≠ (lkey, bpos) | TV violations |
|---|---|---|---|---|---|
| lock idiom, 30 late-keyed runs (job 293645) | 110,270 | 8,960 | 0 | 0 | 0 |
| ScoR programs, atomic + timer (job 293745) | 162 kernels | — | 0 | 0 | 0 |
| green set with `YOSEMITE_HB_LATE_SEQ=atomic` (job 293646) | 45 dumps, all late-keyed | — | tests pass | — | tests pass |

Without the `__syncwarp` after the commit, W0 would not hold for multi-lane records: a lane
other than the committing one leaves the callback before the key of its record is drawn. The
brief's "a thread's own callbacks are sequential, so it does" holds only for the committing lane.

## 3. Measurement (step 3)

### Lock idiom, `python/testdata/lock_contention_a2.cu` kernel `kcontend`

Setup: 16 acquisitions per warp, 5 runs per level and variant, one job
(`setup/t15_handoffs.sh`, job 293645, c23). Each count is hand-offs recorded inverted over
cross-thread adjacent critical sections, scored by `a2_window_count.py handoffs` (T14's
definition). The late-keyed runs are scored twice: as dumped (late order), and after
`late_seq.py prep` renumbers `seq` by `bpos` (buffer order, the pre-T15 key).

| contending warps | off (this runtime) | atomic key: buffer order | atomic key: late order | timer key: buffer order | timer key: late order | T14, old runtime (3 jobs) |
|---|---|---|---|---|---|---|
| 2 (1 × 2) | 0 / 155 | 0 / 155 | 0 / 155 | 75 / 155 | 75 / 155 | 53 / 465 (11.4 %) |
| 4 (1 × 4) | 60 / 311 (19.3 %) | 45 / 315 (14.3 %) | 40 / 315 (12.7 %) | 145 / 305 | 145 / 305 | 306 / 945 (32.4 %) |
| 16 (4 × 4) | 321 / 1,266 (25.4 %) | 212 / 1,274 (16.6 %) | **187 / 1,274 (14.7 %)** | 427 / 1,271 | 427 / 1,271 | 1,054 / 3,825 (27.6 %) |

Paired per run, atomic key, late vs buffer order of the same trace (job 293686):

- 1 × 2: 0 vs 0, all five runs.
- 1 × 4: 8 vs 9, all five runs.
- 4 × 4: 46 vs 47, 34 vs 41, 33 vs 38, 35 vs 41, 39 vs 45.

The late order never has more inversions than the buffer order, and never fewer by more than 7
per run.

- **The one-block levels are deterministic.** All five runs of 1 × 2 and of 1 × 4 give identical
  counts, so each such cell is one observation, not five.
- **The timer key orders nothing here.** Keys tie for 557 of 1,185 events at 2 warps, 2,163 of
  3,280 at 4 and 43,456 of 50,095 at 16. Ties fall back to the slot, so the late order equals
  the buffer order in every run. What differs between the timer column and the others is the
  schedule the instrumentation produced, not the key.
- **The variant changes the schedule, so compare columns only within a run.** The three
  variants run different device code, so their executions differ: the off column (0 / 19 / 25 %)
  and T14's (11 / 32 / 28 %) are different executions of the same program, and the timer runs
  inverted far more often. Only the paired comparison (atomic: buffer vs late on one trace)
  isolates the key.
- engine == oracle on all 45 dumps (`engine_eq_oracle` 5/5 per cell), and every inverted
  hand-off's instances carry `a2_uncertain`.

### The three ScoR programs of T14 (vector-clock mode, one recording each, job 293647, c78)

Since T10's token rule merged, all three are CLEAN. Their pairs are `sc` (informational), so no
Race-alone verdict rests on flagged DR reports any more. Every hb_races instance is SC, and every
one carries `a2_uncertain` in every variant (job 293745).

| program | variant | verdict | classes | SC instances / flagged | events | wall s |
|---|---|---|---|---|---|---|
| matrix-multiplication-norace-small | off | CLEAN | sc:4 | 199,200 / 199,200 | 190,455 | 108.9 |
| | atomic | CLEAN | sc:4 | 269,376 / 269,376 | 191,855 | 96.2 |
| | timer | CLEAN | sc:4 | 203,136 / 203,136 | 190,915 | 105.8 |
| rule-110-norace-small | off | CLEAN | latent-sc:2 | 1 / 1 | 35,923 | 6.03 |
| | atomic | CLEAN | latent-sc:2 | 0 / 0 | 35,926 | 6.03 |
| | timer | CLEAN | latent-sc:2 | 1 / 1 | 35,923 | 5.88 |
| rule-110-norace-large | off | CLEAN | latent-sc:14, sc:4 | 846 / 846 | 1,177,043 | 35.3 |
| | atomic | CLEAN | latent-sc:14, sc:4 | 1,399 / 1,399 | 1,178,018 | 35.7 |
| | timer | CLEAN | latent-sc:14, sc:4 | 1,142 / 1,142 | 1,177,554 | 35.5 |

What the table shows:

- **The late key removes no flagged pair.** The instance counts follow how long the spinning
  locks ran in each execution. They are one run each and do not rank the variants.
- **rule-110-small's classes come from the static leg.** Its `latent-sc:2` stays even in the
  atomic run, whose hb_races is empty.

### Cost per record

The late key adds, per record: one extra global atomic (atomic variant) or a `%globaltimer`
read, one 8-byte store and one `__syncwarp`. Per drain it adds a 16 MB device-to-host copy of the
keys and a 16 MB memset. The wall-clock measurements:

- **rule-110-norace-large** (1.18 M events): 35.3 / 35.7 / 35.5 s (off / atomic / timer), i.e.
  +1 % for the atomic key, which is about 0.3 µs per record, in one run each.
- **The lock runs** (≤ 11 k events): 0.9–1.4 s in every variant, dominated by process startup.

Both differences are inside single-run noise. No more precise cost was measured.

## 4. Why the late key does not help (interpretation, not measured)

A key drawn by `atomicAdd` must return its value before it can be stored. So between the key's
arrival at L2 and the instruction's arrival there is at least one L2 round trip plus the
return and issue. A spinning `atomicCAS` spends a fixed share of its loop inside that window,
and the unlock's `atomicExch` has a window of its own. An inversion needs only the unlock to
reach L2 inside a spinner's window. Shortening the Sanitizer window from about four round trips
(slot atomic, fence, commit atomic) to one also shortens the spinner's loop by the same work, so
the in-window fraction changes little. This fits the ~12 % paired reduction, but it is not
proved.

A timer key avoids the round trip, but `%globaltimer`'s update granularity is too coarse on this
GPU (87 % ties). `clock64` is not comparable across SMs.

Recording the instruction's effect, not its issue, remains the fix (D15: an after-instruction
hook; NVBit post-submission).

## 5. Checks (A4)

| check | result |
|---|---|
| default tool path (no `YOSEMITE_HB_TRACE`), main runtime vs T15 runtime, `norace_interblock_atom` and `race_interblock_none-lock_rtraw` (job 293646) | identical up to device addresses and dist histograms |
| green set, `YOSEMITE_HB_LATE_SEQ` unset (job 293646) | 287 passed, 1 xfailed (`test_relaxed_handoff_should_race`) |
| green set, `YOSEMITE_HB_LATE_SEQ=atomic`, all 45 dumps late-keyed | 287 passed, 1 xfailed |
| engine == oracle, lock idiom, late order | 45 / 45 dumps |

**No verdict can move with the default.** With the key off, the collector's behaviour differs
only by a tracker-field load and branch per record, and the engine, oracle and verdict layer are
untouched.

## Commands

```
W=/home/fzheng4/AccelProf/.claude/worktrees/late-seq
sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t15-build-%j.log    --export=ALL,W=$W eval/baselines/setup/t15_build.sh      # 293643
sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t15-handoffs-%j.log --export=ALL,W=$W eval/baselines/setup/t15_handoffs.sh   # 293645
sbatch -p normal -n 1 -c 2 --time=30 -o $W/build_logs/t15-paired-%j.log --export=ALL,W=$W eval/baselines/setup/t15_paired.sh # 293686
sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t15-check-%j.log    --export=ALL,W=$W,LATE=atomic eval/baselines/setup/t15_check.sh  # 293646
sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t15-scor-%j.log     --export=ALL,W=$W eval/baselines/setup/t15_scor.sh       # 293647
sbatch -p normal -n 1 -c 2 --time=60 -o $W/build_logs/t15-scor-a2-%j.log --wrap "$W/.env/bin/python $W/eval/baselines/setup/t15_scor_a2.py"  # 293745
```

Traces: `/mnt/beegfs/fzheng4/t15-late-seq/handoffs/` (lock idiom, both orders) and
`/mnt/beegfs/fzheng4/cuvein_traces/t15-{off,atomic,timer}/` (ScoR).

## What remains unverified

- **The cost.** The per-record cost is inside single-run noise. There is one ScoR run per
  variant and no repeated timing.
- **The size of the effect.** The lock idiom is one kernel shape on one GPU model (sm_89).
  Whether the paired ~12 % reduction holds elsewhere, or on RMW windows other than a CAS/EXCH
  lock, is not measured.
- **The §4 explanation** is an interpretation, not a measurement.
- **Why the off rates differ from T14's** (0 / 19 / 25 % against 11 / 32 / 28 %) is not
  established. Different device code, node and driver all changed at once.
- **The drain protocol at scale.** The full-buffer path (keys awaited mid-kernel, the filling
  lane's early key) was never exercised. No kernel measured here has more than 191 k events
  (matrix-multiplication, one kernel), and a record is at most one event, far below the 2 M-slot
  buffer. A multi-drain kernel under the late key has not been run.
- **Whether `%globaltimer`'s granularity is the same on other GPUs** is not measured.

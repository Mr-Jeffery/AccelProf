# T4 — No-dump mode: both clocks during the run, aggregates only (design note)

Branch `feat/no-dump`, based on `fix/late-seq-gating` 69d9594 (T18) = `cuVein` 8263e04 + T18.
Written 2026-10-01 before any code (CLAUDE.md C, T4 step 1). Decisions are marked **D**;
everything else is read off the code at 69d9594 (`sanalyzer/src/tools/pc_dependency_analysis.cpp`,
`python/sync_dominance.py`, `python/hb_oracle.py`, the harness under `eval/`).

## 1. The problem, and what no-dump mode is

With `YOSEMITE_HB_TRACE=1` the tool appends one JSON string per record to `_hb_events`
for the whole kernel (`hb_collect_events`, per buffer drain) and writes them as the
`hb_events` array in `kernel_N.json` at kernel end (`kernel_trace_flush`). The vector
clock (`HbClock::process`, vector-clock mode only) consumes the same drain in a streaming
way and never keeps a record. So for the nine barrier-only timeout programs and most of
P7/P9 the run dies of host memory or of the 1,200 s cap while holding or writing
100–252 GB of text, in *both* modes (T5b, `eval/MEMORY_FOOTPRINT.md` §7), and the
offline pass would then parse it for hours (P9-mr-cuda: 4 h cap twice).

No-dump mode (`YOSEMITE_HB_DUMP=0`) keeps every record out of host memory: the runtime
computes, during the run, everything the verdict layer reads from `hb_events` today and
writes only those aggregates at kernel end, marked `"hb_aggregates": 1`. The default
(`YOSEMITE_HB_DUMP=1`, or unset) is unchanged and lossless; a lossy `hb_events` is never
written (A4). Parity between the two is established on programs that can do both (§6).

Nothing in the collector (`nv-compute`) changes: the switch lives in the analyzer library.

## 2. What is read from `hb_events` today, and what the runtime can emit

`sync_dominance.analyze()` reads, per kernel JSON: the header (`kernel.*`), `nodes`,
`edges` (the dependency tool's output — untouched by T4), `hb_races`,
`hb_races_sync_only`, `hb_async`, `hb_exits`, `hb_gate`, `tv_violation`, and `hb_events`
through exactly two functions, `trace_rmw_points()` and `barrier_only_pairs()`. The
harness and the census scripts read `len(hb_events)` and a lane count. The table lists
every consumer found by `/usr/bin/grep -rn hb_events python eval` (results/traces/nvbit
dirs excluded).

| # | what is taken from `hb_events` | reader | runtime aggregate | cost | status |
|---|---|---|---|---|---|
| 1 | `hb_races` — aggregated DR/SC records per (pc pair, kind, class, space, dist, async) with `count` and `a2_uncertain` | `analyze()` (raced pc sets, `observed_dyn` from `a_tid`/`b_tid`, `ev_info` for candidates, `_a2_flag`), `run_cuvein`, census | **already an aggregate**, emitted by `HbClock::emit` (vector-clock mode) | none | emitted |
| 2 | `hb_races_sync_only` — `[pc_lo, pc_hi, count]` of the barrier-only clock | `analyze()` (`sync_pcsets`), census, parity | **already an aggregate** (`HbClock::sync_pairs`, vector-clock mode) | none | emitted |
| 3 | the offline barrier-only pass `barrier_only_pairs(trace, …, dist_out, order_out, tv_out)`: the same pairs **plus, per pair, the widest thread distance and the (earlier pc, later pc) of its first conflict** | `analyze()` → `offline_pass()`: in scalar-clock mode it supplies `sync_pcsets` and extends `observed_dyn` (edge rescue) with `dist`; in **both** modes it supplies `ev_info` (orientation, distance, count) for event-stream candidates that `hb_races` does not name (`missing`); its `tv_out` is the diagnostics' `tv_violation` fallback | `HbClock` already computes the pairs; add `dist` (max of `thread_distance` over hits) and the first orientation to `sync_pairs`; in scalar-clock mode run the sync instance of `HbClock` (today it never runs: `hb_scalar_clock_mode()` gates `hb_clock_process`) | 3 ints per pair; in scalar-clock mode the sync instance's state: buckets O(distinct (location, key, thread)), `vs` O(threads), pending barriers — the same state the offline pass builds from the dump, now without the dump | **new key `hb_sync_pass`** (§3), both modes |
| 4 | `trace_rmw_points(trace, rmw, max_lanes)`: per non-RMW pc `u`, the set of pcs of the PO-next RMW of `u`'s thread after each instance of `u` (empty if some instance has none); per pc `v`, the PO-previous RMW pcs (empty if some instance has none) — R3's release and acquire points from the trace (T12) | `analyze()` → `eng.attach_trace(…, rpoints, apoints)`, both modes, only when the kernel has atomics; `None` above `CUVEIN_BARRIER_PASS_MAX_LANES` (5 M lane-accesses) | per lane thread: the set of non-RMW pcs since its last RMW and its last RMW pc; at an RMW, every pending pc gains it as a release point; a non-RMW pc gains the thread's last RMW as an acquire point, or is marked orphan; at kernel end pending pcs are stranded. Exactly the offline loop, in record order (local records skipped, exit/sync records ignored, async copies attributed to the issuing lane as offline) | per thread one small set + one pc; per pc one set of RMW pcs; O(threads × pcs) worst case, in practice a few KB | **new key `hb_rmw_points`** (§3), both modes |
| 5 | the A2 windows and the flag | `a2_uncertain` on `hb_races` (runtime, T14); the offline census `a2_window_count.py` over kept dumps | the flag is already in #1; the window census needs records | — | flag emitted; census not available for no-dump programs (§7) |
| 6 | trace-validity: `tv_violation` (vector-clock), `TV-barrier-pending-at-end` of the offline pass (scalar-clock) | `analyze()` diagnostics, `aggregate.py`, `parallel.py`, `summarize.py` | `HbClock`'s monitor (all five checks + W3) runs in the sync instance too, so scalar-clock mode gets `tv_violation` from the runtime | none | emitted, both modes (a gain for scalar-clock mode, T11) |
| 7 | `len(hb_events)` and `sum(len(e["lanes"]))` | `aggregate.py` (`events`, `oracle_max_events`), `parallel.py _count_events` (P7 largest-trace selection; `meta.modes.<mode>.events`), `scale_harness.py`, `latent_census.py` (`events`, `lanes`), `host_hb.py`, `t5b_parity.py` | two counters: records serialised today (non-local) and lane-accesses | none | **new keys `hb_events_count`, `hb_lanes_count`**; readers take `hb_events_count` when `hb_events` is absent |
| 8 | the markers `hb_async`, `hb_exits`, `hb_gate`, `hb_a2`, `hb_late_seq` | `dump_async_pcs`, the offline pass, oracle, re-score | written as today | none | emitted |
| 9 | `coherence_profile` | tests, `scale_harness.py`, parity | emitted by `HbClock::emit` (vector-clock) | none | emitted |
| 10 | the whole stream, for `hb_oracle.py` (the specification), `t5b_parity.py`, `t9/t10/t12_rescore.py`, `latent_census.py collect`, `late_seq.py`, `a2_window_count.py`, `host_hb.py` (T2's per-kernel footprint) | offline replay | **cannot be emitted**: these replay records | — | not available on no-dump programs (§7) |

Event-stream candidates need no separate mechanism (brief, step 1): `HbClock` checks
every conflicting record pair, so a pair with no dependency edge is in `hb_races`
(vector-clock) or in `hb_sync_pass` (both modes) exactly as it is in the offline pass
today; `analyze()`'s `missing` loop reads them from there.

## 3. The dump under `YOSEMITE_HB_DUMP=0`

`kernel_N.json` keeps the header, `nodes` and `edges` unchanged and carries, instead of
`hb_events` (absent, not empty):

```
"hb_aggregates": 1,
"hb_events_count": <records that hb_collect_events would have serialised>,
"hb_lanes_count": <sum over memory records of popcount(active_mask)>,
"hb_async": 1, "hb_exits": 1, ["hb_late_seq": 1, "hb_late_seq_key": "..."],
"hb_sync_pass": [[pc_lo, pc_hi, count, dist, first_pc, second_pc], ...],
"hb_rmw_points": {"release": {"<pc>": [rmw pcs...] | []}, "acquire": {"<pc>": [...] | []}},
"hb_races": [...], "hb_a2": 1, "hb_gate": "...", "hb_races_sync_only": [...],   (vector-clock mode only, as today)
"coherence_profile": {...},                                                     (vector-clock mode only, as today)
["tv_violation": "..."],                                                        (both modes now)
["hb_stats": {...}]
```

- `hb_sync_pass` is the offline pass's `(pairs, dist, order)`: `dist` ∈ {1 warp, 2 block,
  3 grid} = `max(thread_distance)` over the pair's unordered conflicts (async bit cleared,
  as `barrier_only_pairs` does); `(first_pc, second_pc)` = `(earlier, later)` of the first
  conflict in record order. Sorted by `(pc_lo, pc_hi)` like the offline dict's insertion
  order does not matter to any reader (sets and dicts).
- `hb_rmw_points` keys are decimal pc strings (JSON); an empty list is the offline
  `frozenset()` (an instance with no RMW after / before it); a pc absent from a map is
  absent from the offline map too (never observed as a non-RMW access by any thread).
- **D1** In vector-clock mode `hb_races_sync_only` stays (`[pc_lo, pc_hi, count]`, readers
  unpack triples) and `hb_sync_pass` is added beside it; in scalar-clock mode only
  `hb_sync_pass` is written, so `analyze()` keeps today's control flow exactly:
  `sync_pcsets` from `hb_races_sync_only` when present (vector-clock), else from the
  offline pass — which now returns the dump's `hb_sync_pass` when it is present. The
  lazily computed pass for `missing` candidates in vector-clock mode reads the same key.
- **D2** With the default `YOSEMITE_HB_DUMP=1` the new keys are written **as well** (they
  cost nothing): a full dump therefore carries both the records and the aggregates, which
  is what the parity check compares (§6). The reader prefers the records when both are
  present (today's path, byte-identical results) unless `CUVEIN_PREFER_AGGREGATES=1`.
- Old readers: every new key is additive; a pre-T4 `sync_dominance.py` on a no-dump file
  sees no `hb_events` and behaves as on a dump above the lane cutoff (static-only +
  `hb_races`/`hb_races_sync_only` where present). `hb_oracle.py` raises its existing
  "no hb_events" `AlignmentError`.

## 4. The runtime

`gpu_data_analysis` keeps calling `hb_collect_events` (which now only counts when the
dump is off) and `hb_clock_process` — in **both** modes. `HbClock` gains:

- `vector_pass` (true in vector-clock mode, false in scalar-clock mode). With it false the
  instance is `Detect(T, sync)` (hb_proof.tex Corollary "The sync instance"): barrier /
  syncwarp / exit assembly, the `vs` clock, buckets with `sclock` only, `sync_pairs`,
  the TV monitor, the async agent's `vs` part, the RMW-point bookkeeping and the
  counters. Skipped: `vc`/`own`, `released`, the chain and gate (`wins`, `gate`, `last_pc`
  for the gate), the possible clock `pd`, `races`, `coherence`. `emit` then writes no
  `hb_races`, `hb_races_sync_only`, `hb_a2`, `hb_gate`, `coherence_profile` (so the verdict
  layer's scalar-clock branch — `raced_pcsets is None` — is taken as today), only
  `hb_sync_pass`, `hb_rmw_points`, `tv_violation`.
- `sync_pairs` values become `{count, dist, first_pc, second_pc}`.
- `rmw_points`: per lane thread `(pending pcs, last rmw pc, has_last)`; per pc the release
  set + stranded flag, the acquire set + orphan flag. RMW-ness is the sidecar's `rmw`
  column (`PcInfo::rmw`), which `atomic_scope_sidecar.py` sets iff
  `sd.atomic_scope(op) is not None` — the same predicate `analyze()` uses for `rmw_pcs`
  (`atomic_scope_sidecar.py:97`). A kernel absent from the sidecar uses the merged table,
  as every other sidecar lookup does. **D3** No fallback to the collector's `ATOMIC`
  flag: the sidecar is mandatory for HB runs (A2.3), and an RMW set from a different
  source would break the same-trace parity by construction.
- `events_count`, `lanes_count`.
- `PcDependency` gains no member (the latent-UB rule): the dump switch is a file-static
  read once, like `hb_scalar_clock_mode()`; `_hb_events` stays empty under no-dump.

Memory under no-dump: vector-clock mode is T5b's state (no change); scalar-clock mode is
the sync instance's state, which is the bucket term (T9: ±40 MB on T5a's programs; the
same `(location, key, thread)` triples the offline pass holds) plus `vs` and the pending
barriers. Measured in step 4 with `YOSEMITE_HB_STATS` on the timeout set; the bucket term
is the one that can still grow with the program (distinct locations × threads touching
them), and it is reported, not hidden.

## 5. The reader

`sync_dominance.analyze()`:
- `offline_pass()` → if `trace["hb_sync_pass"]` is present and (`hb_events` absent or
  `CUVEIN_PREFER_AGGREGATES=1`): `(pairs, dist, order)` from the key; else as today.
- `trace_rmw_points()` → the same rule with `hb_rmw_points`; no lane cutoff applies to
  the key (the cutoff exists only because the offline pass costs; a no-dump program has
  no `hb_lanes_count` cutoff — stated in §7 as a deliberate difference).
- `barrier_only_pairs()` itself is unchanged (it is the scalar-clock specification the
  runtime's sync instance must match, §6).
- `make_tables.py` reads no kernel JSON; `run_cuvein.py` / `parallel.py analyze` go
  through `analyze()`; `aggregate.py`, `parallel.py._count_events`, `latent_census.py`,
  `scale_harness.py` take `hb_events_count` when `hb_events` is absent.
- `python/hb_modes.py` documents the key names (not mode names; A4's list grows by
  `hb_aggregates`, `hb_sync_pass`, `hb_rmw_points`, `hb_events_count`, `hb_lanes_count`).

## 6. Parity (brief, step 3) — on one trace, not two runs

Two runs of one program are two schedules, so verdicts can differ between them for
reasons that have nothing to do with the dump. Parity is therefore established on one
recording that carries both the records and the aggregates (D2):

1. **Sync instance == offline pass**, per kernel: `hb_sync_pass` of the dump equals
   `barrier_only_pairs(trace, rmw_all, coh_all, None, dist, order)` as `(pairs, dist,
   order)` — exact, every kernel of every parity program (the two are the same clock;
   `FP_DIAGNOSIS.md` 3b / T9 made them bucket-identical). In vector-clock mode this is also
   `hb_races_sync_only` == the triples of `hb_sync_pass`.
2. **RMW points == `trace_rmw_points`**, per kernel, with the lane cutoff lifted
   (`CUVEIN_BARRIER_PASS_MAX_LANES` large), exact.
3. **Verdicts**: `analyze(dot, kj)` with `hb_events` (today's path) vs
   `CUVEIN_PREFER_AGGREGATES=1` on the same file: the verdict records are compared on
   (pc pair, verdict, hb_class, matrix_class, conflict_class, race_type, observed_distance,
   event_candidate, edge_rescued, a2_uncertain, model_bug) — equal, both modes (the
   scalar-clock view of a vector-clock dump is produced as the tests do it: the
   vector-clock-only keys popped).
4. The programs: 20 that record in both modes with dumps that the oracle/offline pass can
   still replay — the T5b parity set (`setup/t5b_parity_ids.txt`) is the natural choice,
   recorded afresh with the T4 runtime in both modes (a script `setup/t4_parity.py`).
   `make_tables.py`'s verdict columns come from the same `analyze()`, so 3 covers it.

Programs over the 5 M lane cutoff are compared with the cutoff lifted on the dump side;
the production difference (the aggregate path has R3's trace points where the offline
path gave none) is listed by program in the report as the cutoff's effect, not parity's.

## 7. What no-dump loses, and what it gains

Lost on a program recorded without a dump:
- `hb_oracle.py` cannot replay it: `HbClock` == specification is established on the
  programs that dump (A4, revised 2026-09-30). The no-dump program's own verdict rests on
  the runtime alone.
- No offline re-score without a GPU: every change to the detector so far was measured by
  replaying kept dumps; a no-dump program must be re-recorded to re-score. The kept
  stores keep their dumps; only new no-dump recordings lack them.
- `a2_window_count.py` (the A2 window census), `late_seq.py` (T15's dual keys),
  `latent_census.py collect`'s lane counts beyond the counters, T2's `host_hb.py`
  footprint (`YOSEMITE_HB_HOST_MEMCPY`, behind a flag, D5 open): all need records.
  **D4** `YOSEMITE_HB_HOST_MEMCPY=1` with `YOSEMITE_HB_DUMP=0` is refused at start with
  one stderr line rather than silently producing a footprint-less host analysis.
- `design/algorithms_check.py` and the T6 simulator: dumps only.

Gained:
- Scalar-clock mode gets the runtime TV monitor (all checks; today only the offline
  pending-at-end check), and loses the lane cutoff on R3's trace points and on the
  barrier-only pass (the programs the cutoff hit — crs-cuda's 26 kernels in T9-0, class
  (c) — are judged like every other).
- Both modes finish on programs whose dump cannot be held (the point of T4).

Unchanged: the kernel JSON keys of the proof's list (`hb_events` when written, `hb_races`,
`hb_races_sync_only`, `coherence_profile`, `tv_violation`); the collector; the default
tool output (no `YOSEMITE_HB_TRACE`); every verdict rule.

## 8. Steps (brief, steps 2–5) and acceptance

2. Runtime: the switch, the sync instance in scalar-clock mode, `hb_sync_pass`,
   `hb_rmw_points`, the counters, D4; `hb_oracle.py` untouched (no clock value changes —
   the specification's parity gate `test_hb_clock_matches_specification` must stay green
   on dumping runs).
3. Reader: §5; `setup/t4_parity.py` runs §6 (1)–(3) over a store; tests: one litmus kernel
   through both paths in `python/test_no_dump.py` (a vector-clock and a scalar-clock
   recording, verdicts equal between `hb_events` and aggregates; the sync instance equals
   `barrier_only_pairs`; the no-dump recording of the same kernel has no `hb_events` and
   the same verdicts).
4. The timeout set (`setup/hb_clock_timeout_ids.txt`, 58 programs; the nine barrier-only
   ones are the acceptance bar) in both modes under no-dump via `parallel.py run`
   (`BASELINE_HB_DUMP=0` → `YOSEMITE_HB_DUMP=0` in `blib.base_env`), then all of P7 and
   P9; wall, peak RSS, `HB_STATS` against the dump runs; the first vector-clock verdicts
   on those suites. Report `eval/NO_DUMP.md`.
5. Optional (second half): streaming lossless encoding — not started unless 2–4 are done.

Acceptance: §6 holds on the 20 programs; the nine barrier-only programs produce verdicts
in both modes; `hb_events` is never written lossy; green set unchanged on the dump path.

## 9. Assumptions to verify while implementing

- A1 `HbClock::sync_pairs` ≡ offline `barrier_only_pairs` pairs on every corpus kernel
  (claimed by FP_DIAGNOSIS 3b and T9; re-checked by §6 (1) — the first time with `dist`
  and `order`, which were offline-only).
- A2 the sidecar's `rmw` set ≡ `analyze()`'s `rmw_pcs` for every kernel of the parity set
  (both from `sd.atomic_scope`; the sidecar is per kernel, `analyze()` per dot cluster).
- A3 the sync instance in scalar-clock mode costs no more than the offline pass's state
  (measured, step 4); if the bucket term alone exceeds the node on a timeout program, that
  program is reported as not reachable by T4 and left for a later task (no FastTrack
  collapse: Theorem "Sound").

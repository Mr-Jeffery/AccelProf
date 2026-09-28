# T9 — measurements: vector-clock soundness (I1, I2, I5), R2 as class (D12), the `sc` column (D2)

Branch `fix/publish-then-tick`, from `cuVein` 1a3aea5 (the detector of 3331d35 plus PR #4).
Code commits b87adbb (the change) and 2494aa3 (`hb_races` aggregation). The argument is in
`design/soundness_event_candidates.md`; the proof edits in `design/proof/hb_proof.tex`
(status paragraph, Definitions "Asynchronous copies" / "Happens-before", Proposition
"Agents", §5 matrix, §7). Hardware: RTX 4060 Ti (sm_89; nodes c3, c24, c64), driver
580.82.07, CUDA 13.3; CPU re-scores on `normal` nodes. Private T9 runtime: collector
`79dbc7ed9567eddb` → libsanalyzer `0f4a65075cde2217` (`eval/baselines/setup/t9_build.sh`);
the installed runtime (`build/sanalyzer/lib`, collector `7bafac9fbac26efd`) was not touched.

Labels: **proved-in-effect** (checked over N real traces), **tested** (a verdict asserted),
**unverified**.

## 1. Checks (GPU)

| check | job | result |
|---|---|---|
| default tool path (no `YOSEMITE_HB_TRACE`) main vs T9 runtime, 2 ScoR programs, up to device addresses | 292391, 292525 | identical (proved-in-effect, 2 programs) |
| green set (CLAUDE.md A4) + `python/test_hb_substitutions.py`, all traces re-recorded with the T9 runtime | 292391, 292525 | **150 passed, 1 xfailed** (`test_relaxed_handoff_should_race`, the documented I4 case) |
| `test_cp_async.py`, `test_barrier_exit.py`, `test_host_hb.py` (outside the green set) | 292529 | 83 passed, 4 xfailed (T3's strict xfails; T3b's job) — unchanged |
| `design/algorithms_check.py`: `hb_oracle.py` == Detect(T, vec) and Detect(T, sync) with the I1/I2 switches **off** (record pairs with DR/SC, sync pairs with counts), and `barrier_only_pairs` == the second clock | 292525 | 32/32 re-recorded ScoR traces (proved-in-effect) |

The T6 strict xfails now pass: `test_write_after_unlock_other_schedule` (I1), 
`test_strong_stores_barrier_weak_load` (I2: (A, C) DR, (A, B) SC, (A, C) in the barrier-only
set), `test_local_memory_is_thread_private` (I5); new: their scalar-clock variants,
`test_local_records_of_an_older_dump_are_ignored`, and the D12 case
(`testdata/strong_store_strong_load.cu`: an unordered relaxed `cuda::atomic` store/load is
`sc` with verdict `SC` in both modes, never `model_bug`) — all *tested*.

**P5 + E2 sweep** (`setup/t9_eval.sh`, job 292469, c64; the 33 ScoR litmus + canary and the
10 E2 programs `memcpy/*`, `intersubwarp/*` — E2's four `asyncmemcpy/*` are out of scope and
not re-run), both modes, main runtime vs T9 runtime on the same node, 1 rep: **86 (id, mode)
rows, no verdict changed**; the one change in report ids is the I2 pair
`shared:0x150-0x260:WAW` added to `race_interblock_blklock_waw` (label RACE) in both modes. No
SC report on any of the 43 programs. `race_interblock_none-lock_rtraw` stays `latent` (Race
alone: CLEAN) until T12.

## 2. Re-score of the kept stores (no GPU)

`eval/baselines/t9_rescore.py`: the stores `evcand` + `full-2026-09-22` as T9-0 selected them
(598 programs, 558 with a vector-clock dump). The T9 oracle replaces `hb_races` and
`hb_races_sync_only` in every vector-clock dump (what a T9 engine would have written on the
same trace, by the parity invariant) → store `t9-after`; `parallel.py analyze` of the recorded
dumps with the 1a3aea5 code (`t9-before`) and of the re-scored ones with the T9 code.
Oracle not finished on 4 programs — P1 `CC_CUDA_V_Topo_Pull_Determ_*_RaceBug_Block_*-1296n`
(default and slower_atomic, Persist and NonPersist; 2.8 GB dumps; the Python oracle's
O(threads²) clocks were OOM-killed, exit 9) — left out of every comparison below.

### 2.1 Race sets (pc pairs; recorded engine vs T9 oracle; `eval/results/t9-rescore/T9_RESCORE_TABLES.md`)

| pset | programs | pairs before | DR pairs after | SC-only pairs after | DR pairs gained | pairs lost | barrier-only pairs gained / lost |
|---|---|---|---|---|---|---|---|
| P1 | 361 | 1146 | 1158 | 121 | 12 | 0 | 1300 / 0 |
| P2 | 58 | 42 | 42 | 0 | 0 | 0 | 0 / 0 |
| P3 | 56 | 14 | 14 | 79 | 0 | 0 | 662 / 0 |
| P4 | 18 | 91 | 103 | 0 | 12 | 0 | 106 / 0 |
| P5 | 33 | 11 | 13 | 0 | 2 | 0 | 8 / 0 |
| P6 | 27 | 5 | 5 | 0 | 0 | 0 | 0 / 0 |
| P9 | 1 | 155 | 155 | 0 | 0 | 0 | 0 / 0 |
| **all** | **554** | **1464** | **1490** | **200** | **26** | **0** | **2076 / 0** |

No pair any pre-T9 run reported is lost (the code is complete relative to the new one on 554
programs: proved-in-effect). The 26 DR pairs gained are on 15 programs: P5
`race_interblock_fence_rtraw` 0x100/0x1f0 (**I1**, the corpus instance) and
`race_interblock_blklock_waw` 0x150/0x260 (**I2**), nine P1 Thread-level CC/BFS Push RaceBug
programs (1–2 pairs each, 12 in all), P4 `rule-110-racy-large`, `graph-coloring-racy-small` (3), and
`matrix-multiplication-{norace,racy}-small` (4 each; §2.3). The 200 SC pairs are Indigo
`CudaAtomic` strong load/store pairs (66 P1, 34 P3 programs) that R2 used to order; the
barrier-only set gains every unordered SC pair and the pairs the shared I2 state hid.
No kept vector-clock dump contains a `local` record (I5 changes nothing on the corpus).

### 2.2 Verdicts

At the harness's operating point (Race ∪ Latent, the program verdict it records), **no
program's verdict moved in either mode**: TPs gained 0, lost 0, new FPs 0, FPs removed 0
(vector-clock: 302 CLEAN, 252 RACE, 37 TIMEOUT, 2 ERROR on both sides; scalar-clock: 312
CLEAN, 281 RACE on both sides; the one `- → ERROR` row of the tables is a harness placeholder
for P9-crs-cuda written before its AFTER mirror existed — its re-analysed rows are RACE with 155 /
7 report ids, as before). Report sets grew on 19 programs, all already RACE (the list:
`T9_RESCORE_TABLES.md` "Every program whose verdict or report set moved").

At the **Race-alone** operating point (vector-clock; a program is RACE iff one of its RACE
report pairs raced as a DR in `hb_races`), exactly two programs move:

| program | label | before | after | cause |
|---|---|---|---|---|
| `P5-race_interblock_fence_rtraw` | RACE | latent only | **RACE** | I1 fixed — a TP gained |
| `P4-matrix-multiplication-norace-small` | CLEAN | latent only | **RACE** | A2 violated on the trace, exposed by I1's fix — a new FP at this point (§2.3) |

`latent_census.py` re-run on the T9 detector (`eval/results/latent-census-t9/census.md`):
latent-only true positives **10 → 9** (`fence_rtraw` left the tier; the other nine are the
eight fence/scope litmus that T12's gate is for, and `none-lock_rtraw`); latent reports on
labelled race-free programs 25 on **5 → 4** programs (`matrix-multiplication-norace-small`
left the tier for `structural`); `sc`: 121 pairs on 66 P1 programs and 79 on 34 P3 programs,
identical in both modes, `latent-sc` none.

### 2.3 The new false positive: an A2 violation on a real trace

`P4-matrix-multiplication-norace-small` (evcand vector-clock dump, block 92): a per-lane block
lock `ATOMG.E.CAS.STRONG.SM` 0x540 / critical section `LDG.E.STRONG.SYS` 0x590, `STG.E.STRONG.SYS`
0x5a0 / unlock `ATOMG.E.EXCH.STRONG.SM` 0x5c0. Warp 0 takes the lock at seq 1669, reads at
2027, writes at 2449 and releases at **2906**; warp 2's last CAS before its own critical
section is at **2901** (its read follows at 3280 with no CAS in between), on the same lock
words (lane 0: 0x7f4e8b005e00). So warp 2's successful CAS read the value warp 0's EXCH wrote,
yet the CAS is recorded five records **before** that EXCH: the trace's `seq` order of the
location's RMWs is not their coherence order — assumption A2 of `hb_proof.tex` §1 fails on
this trace (plausibly because the Sanitizer's memory callback runs before the atomic executes;
unverified). The model then sees warp 2's CAS acquire from warp 0's *acquire* CAS (1669); with
publish-then-tick that clock does not cover warp 0's critical section, so the section's
accesses are unordered with warp 2's — 4 DR pairs. The pre-T9 engine was silent only because
tick-before-publish (I1) happened to put warp 0's post-acquire epoch into its acquire's
published clock. Not suppressed (A4); for the paper: a fidelity finding (A2), and a decision
for the collector (record RMWs after they execute, or with the value read) — see
"remains unverified".

## 3. Cost

**`HB_STATS`** (`setup/t9_measure.sh` job 292496, c3; "before" = T5a job 287964, same helper
`t5a_stats.py`, same inputs):

| program | `last_write` + `last_reads` before | `buckets` after | peak RSS before → after |
|---|---|---|---|
| tiled_gemm N=256 | 22 MB + 329 MB = 351 MB (3.67 M readers) | 321 MB (3.87 M entries) | 4.68 → 4.65 GB |
| reduction, large input | 3.4 MB + 318 MB = 321 MB | 360 MB (1.12 M entries) | 6.75 → 6.79 GB |
| Indigo3 CC push 1296n, at 16,000 records | 0.2 MB + 19.4 MB | 16.5 MB | 60.4 → 60.4 GB (the `vc` clocks: 60.7 GB, O(threads²), T5b) |

The bucket term is at most ~12 % of a term that is itself < 6 % of engine memory.

**`hb_races` records.** Without the FastTrack collapse, Check reports every unordered record
pair: on the 554 re-scored programs the oracle's record count went from 7.2·10⁷ (recorded
engines) to 1.71·10⁹; P1 `CC_CUDA_V_Topo_Pull_Determ_*_RaceBug_*` programs from 4.6–6.8·10⁵ to
0.96–1.19·10⁸ each (70 programs grew more than 10× and past 10⁵ records). Engine and oracle
therefore aggregate `hb_races` per (a_pc, b_pc, kind, class, space, thread distance, async)
with one example record and a `count` (commit 2494aa3): no consumer needs record pairs, the
verdicts are unchanged (the re-score used record-level dumps; the aggregation changes only the
candidate weight), and the engine's race state is bounded by pc pairs.

**Local records** (`setup/t9_measure.sh` job 292558, c24): `local_mem_blocks.cu`
(2 × 32 threads) vector-clock dump 1.34 MB / 258 events / 8,352 local lanes / 8,096 spurious
`hb_races` (all local) with the main runtime → 4.6 KB / 2 events / 0 / 0 with T9. P7: of
hotspot, pathfinder, srad, stencil1d, heartwall, lavaMD and particlefilter only
particlefilter has `LDL`/`STL` in its SASS (10); its scalar-clock dump under a 600 s cap is
identical in both runtimes (kernel 0: 6.29 GB, 4,696,938 events, 0 local records) — the local
spills are not what makes the P7 dumps large.

## 4. Other observations

* `P4-graph-coloring-racy-small`: every kernel's recorded dump carries `tv_violation`
  (`TV-barrier-completion-order`) and the pre-T9 oracle raises on all 36 kernels — pre-existing,
  not a T9 change; for T3b (exit-aware assembly) and T11 (nothing reads `tv_violation`).
* P3 `CC_CUDA_V_Data_Pull_NonDeterm_*_Persist_Atomic_Block_*-100n` needed a 150 GB address-space
  cap for the Python oracle (it died under 60 GB); re-scored.

## 5. Commands

```
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_build.sh        # 292387, 292524 (aggregation)
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_check.sh        # 292391, 292525
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_check2.sh       # 292495, 292529
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_eval.sh         # 292469 (P5 + E2)
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_measure.sh      # 292496 (A); SKIP_A=1: 292558 (B)
.env/bin/python eval/baselines/t9_rescore.py prepare                     # on a normal node
sbatch --array=0-23 --export=ALL,SIZE=small eval/baselines/setup/p_t9_rescore.sh     # 292434
sbatch --array=0-17 --exclusive --export=ALL,SIZE=big eval/baselines/setup/p_t9_rescore.sh  # 292459
git archive -o before_code.tar 1a3aea5 python eval/baselines eval/aggregate.py        # the BEFORE code tree
CODE=<that tree> WHICH=before sbatch --array=0-15 eval/baselines/setup/p_t9_analyze.sh   # 292460
WHICH=after sbatch --array=0-15 eval/baselines/setup/p_t9_analyze.sh                  # 292504 (+ 292532, 292570/1 by id)
.env/bin/python eval/baselines/latent_census.py collect --stores /mnt/beegfs/$USER/cuvein_traces/t9-after \
    --out eval/results/latent-census-t9 ...                                            # 292533, 292534
.env/bin/python eval/baselines/t9_rescore.py tables
.env/bin/python eval/baselines/latent_census.py tables --out eval/results/latent-census-t9
```
Outputs: `eval/results/t9-rescore/` (before/after CSVs, `T9_RESCORE_TABLES.md`, selection,
manifest; `detail/` gitignored), `eval/results/latent-census-t9/`, `eval/results/t9-eval-*/`,
`eval/baselines/setup/t9_stats/`; stores `/mnt/beegfs/fzheng4/cuvein_traces/t9-{before,after}`.

## 6. What remains unverified

* The cause of the A2 violation (callback before execution) is inferred, not measured; how
  many kept traces violate A2 is not counted (only this program's verdict depends on it). A
  per-location check "a CAS that succeeds is not recorded before the release it observed"
  needs the values the collector does not record.
* The `hb_races` aggregation was verified by the parity tests and the simulator; the re-score
  ran with record-level dumps (verdict-equivalent by construction, not re-run aggregated).
* 4 P1 1296n programs were not re-scored (Python oracle OOM); their engine run with T9 was not
  tried. `P9-mr-cuda` hit the 4 h analysis cap on both sides (unchanged status).
* The E2 `asyncmemcpy/*` programs, P7 and 8 of 9 P9 programs have no vector-clock dump (T5b).
* Proposition "Agents" and the Part 2 superset argument are hand arguments.
* No second architecture (sm_89 only); the engine's T9 memory at P1 scale (with aggregation)
  was not measured on a full run.

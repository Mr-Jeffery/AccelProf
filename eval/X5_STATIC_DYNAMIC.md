# X5: static versus dynamic — barrier-ordered pairs by CFG shape, and PCDG variance between recordings

Branch `eval/x5-static-dynamic`, worktree `/home/fzheng4/wt-x5`, **cut from `cuVein` 4094187**
(`40941876e5ca39120954a65d20a924e4a1462d20`, "Merge fix/aggregates-default (X0)", the code freeze;
`origin/cuVein` is the same commit). Left unmerged for Jeffery; `eval/final-tables` is untouched.
Analysis only: no change to `sanalyzer/`, `nv-compute/`, `python/` or any existing `eval/` script,
no GPU, no new recording; every job ran in partition `normal`. Legend as in CLAUDE.md A4:
**proved-in-effect** = an invariant checked over the stated stores; **tested** = a specific result
asserted; **unverified** = said so.

Two scripts and their outputs (all under `eval/baselines/setup/` and `eval/results/x5/`):

| file | what it does |
|---|---|
| `barrier_ordered_bins.py` | part 1: finds every barrier-ordered pair of the X1 recording and bins it from the CFG |
| `pcdg_variance.py` | part 2: Jaccard overlap of PCDG edge sets and statically unresolved pair sets between recordings |
| `x5_common.py`, `x5_show.py`, `x5_bar_forms.py`, `test_x5_bins.py`, `p_x5_{plan,collect,report}.sh` | shared analysis wrapper, SASS printer for hand checks, dot census, the binner's unit tests, the sbatch wrappers |

## 0. Findings first

1. **The X1 confirm files contain no barrier-ordered pair.** 9,443 files in the five directories
   `confirm_final{,-long,-long-sc,-24h-vc,-24h-sc}` carry the keys `raw` (RACE reports) and `raw_sc`
   (SC reports) only: hb_class values `structural` 16,746, `benign` 3,327, none 16,673, `sc` 830,
   `latent-sc` 1; `barrier-ordered` 0 (`eval/results/x5/confirm_scan.txt`, job 314117). The cause is in
   the harness: `run_cuvein._analyze_reports` keeps the RACE and SC verdicts of each
   `sync_dominance.analyze` report and drops the ORDERED ones (`barrier-ordered` is an ORDERED class).
   The brief's input, taken literally, does not exist. **What I did instead** (analysis of existing
   recordings, the same scoring code, no substitution of another store): re-ran the harness's own
   `_analyze_reports` over the kept X1 trace of every (program, mode) that has a confirm file — the
   store its merged row came from, through `final-2026-10-view` — with `sync_dominance.analyze` observed
   from outside, and took the barrier-ordered pairs from those reports. **Check:** all 9,412 re-runs
   reproduce their confirm file's report ids and SC-report count exactly (proved-in-effect, §2.4).
2. 898 of 4,706 programs per mode (19.1 %) hold at least one barrier-ordered pair: **1,021 pairs**,
   the same 1,021 in the vector-clock and in the scalar-clock recording. By CFG bin: 599 loop-carried,
   200 partial participation, 140 early exit, 17 branch arm, 65 other (§2).
3. 123 (program, mode) groups have two or more complete recordings in the T20 parity and X1 stores
   (62 vector-clock, 61 scalar-clock programs, 367 pairs of recordings). The edge sets are identical in
   141 of 184 (vector-clock) and 139 of 183 (scalar-clock) pairs of recordings, Jaccard down to 0.7273
   and 0.7157; the statically unresolved pair sets are identical in 104 of the 108 pairs per mode in
   which one is non-empty; no pair of recordings differs in RACE versus CLEAN (§3).

## 1. Method

### 1.1 Inputs

* **X1 recording** (`eval/FINAL_SWEEP.md`, `eval/final-sweep`): stores `final-2026-10`, `-long`,
  `-long-sc`, `-24h-vc`, `-24h-sc` under `/mnt/beegfs/fzheng4/cuvein_traces/`; the per-key store of the
  merged row is `final-2026-10-view/<id>/<mode>` (a symlink into the right store); confirm files in
  `/home/fzheng4/AccelProf/eval/baselines/confirm_final*` (untracked, runtime checkout). The plan
  (`eval/results/x5/bo_plan.json`) holds 9,412 keys = 4,706 programs × 2 modes that have both a
  recording and a confirm file. Not in the plan (no recording in the view, 38 keys): 16 P6 programs
  (`needs-sm90`, never run), 1 P7 and 2 P9 programs, both modes.
* **T20 parity stores** `t20-parity` (the first T20 build, `eval/THREAD_INDEX.md` §2: `f9d2996a`) and
  `t20-parity2` (the final build `391cf9cc`); their `meta.json` records no library hashes. The X1 stores'
  `meta.json` record libsanalyzer `2201fcb7d57ae783`.
* **Verdict layer:** `python/sync_dominance.py` of this checkout = `cuVein` 4094187, the layer X1's
  analysis used (`eval/FINAL_SWEEP.md` §0). Python `/home/fzheng4/AccelProf/.env/bin/python` 3.14.4,
  networkx 3.6.1 (CLAUDE.md A2.3 says 3.10 / 3.2.1; I did not check which versions X1 ran under). CFG
  utilities used:
  `sync_dominance.parse_dot`, `HBGraph` (region graph split at sync instructions, `dom`, `postdom` with a
  virtual EXIT root, instruction-level successor map `ins_succ`).

### 1.2 Part 1 — the bins

A pair is one (kernel, ancient pc `u`, current pc `v`, space class) over all launches of the recording,
taken from the verdict records whose `hb_class` is `barrier-ordered`. Bins, first match wins (the order
of the brief):

1. **loop-carried** — `u` and `v` lie in one natural loop (back edge = an edge into a dominator; one loop
   per header) that contains a qualifying BAR (`BAR.SYNC*`, `BAR.RED*`; `BAR.ARV*` never orders).
2. **partial participation** — some qualifying barrier *between* `u` and `v` is a WARPSYNC (any mask), or a
   BAR with a count operand that is not a literal zero (BAR.RED's predicate operand is not a count).
3. **early exit** — for some barrier `s` between `u` and `v`: an EXIT/RET instruction is reachable from
   `u` without passing `s` and is not reachable from `s` (the threads taking that path never arrive).
4. **branch arm** — some barrier between `u` and `v` is not in postdom(`u`), and none of the above applies.
5. **other** — everything else.

"Between": a qualifying barrier with a CFG path `u → s` and a path `s → v`, cycles included (so a barrier
earlier in a loop body counts when the loop can be re-entered). Bins 2 and 4 use "some", as the brief
words them; §2.3 shows what that means in the data. The binner is unit-tested on hand-built CFGs, one per
bin plus precedence and the predicated-EXIT cases: 11/11 (`test_x5_bins.py`, job 314121, **tested**).

Facts the binner relies on, checked over the 858 distinct dot files of the X1 store, 233 of which contain a
BAR or WARPSYNC (job 314121, `eval/results/x5/bar_forms.txt`, Appendix C): no BAR carries a count operand
(704 `BAR.SYNC.DEFER_BLOCKING` and 40 `BAR.SYNC` with `0x0`; 16 `BAR.RED.OR` and 8 `BAR.RED.POPC` with `0x0` and a
predicate; 168 WARPSYNC with an immediate mask, 49 with a register mask) — so the "BAR with a count" test is
exercised only by the unit test; every EXIT/RET (1,874 predicated, 1,312 plain) is the last instruction of its
basic block, as the region graph assumes.

### 1.3 Part 2 — the variance

* **Recording** = (store, program, mode) with `meta.json` saying the mode was saved, not partial, and a
  finished rep. Complete recordings in `t20-parity` (122), `t20-parity2` (122), `final-2026-10` (123) and
  `final-2026-10-long` (1: P9-fpc vector-clock, also complete in the first pass). No incomplete recording
  belongs to a selected group. X1 kept one recording of its three reps per mode; the other two exist as
  walls in `meta.json` only.
* **Edge set** = {(kernel, ancient pc, current pc)} over the `edges` of all `kernel_N.json` of the
  recording (cold-miss edges, which have no ancient pc, excluded); kernel = `<dot>::<mangled name>`.
* **Statically unresolved pair set** = {(kernel, unordered pc pair, space)} of the pairs
  `sync_dominance.analyze` judged for which, in some launch, neither R1 (a barrier/warpsync dominance of
  the observed distance) nor R3 (a PC-level chain) held — read off each verdict record as
  `strength < observed_distance and hb_chain is None`; event-stream candidates are included.
* Jaccard `|A∩B| / |A∪B|` for every pair of a group's recordings; two empty sets give 1.0 and are counted
  in the "both empty" columns. Extra, labelled: the RACE report ids of the two recordings (the
  single-run verdict) with and without their race-type suffix.

## 2. Barrier-ordered pairs by CFG bin

### 2.1 Table (`eval/results/x5/barrier_ordered_tables.md`, Table 1)

| suite | programs re-analysed (per mode) | programs with ≥ 1 pair | pairs | loop-carried | partial participation | early exit | branch arm | other |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 32 | 56 | 8 | 0 | 0 | 0 | 48 |
| P3 | 60 | 12 | 22 | 6 | 0 | 0 | 0 | 16 |
| P4 | 28 | 10 | 83 | 23 | 60 | 0 | 0 | 0 |
| P5 | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P6 | 34 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| P7 | 13 | 1 | 2 | 2 | 0 | 0 | 0 | 0 |
| P9 | 8 | 2 | 17 | 0 | 0 | 0 | 17 | 0 |
| PI | 4,130 | 840 | 840 | 560 | 140 | 140 | 0 | 0 |
| **all** | **4,706** | **898** | **1,021** | **599** | **200** | **140** | **17** | **65** |

The table is the same for both modes, row by row (the appendix has both rows); the pairs are the same
1,021 in the two modes' separate recordings (Table 2). 4 pairs (P1) are barrier-ordered in one launch and
in another class in a different launch of the same recording. Per-pair rows: `barrier_ordered_pairs.csv`
(2,042 rows = 1,021 × 2 modes).

### 2.2 What is in the bins (hand-checked against the SASS, `eval/results/x5/hand_checks.txt`)

* **loop-carried** (599): PI 560, P4 23, P1 8, P3 6, P7 2.
* **partial participation** (200): every one has a WARPSYNC between `u` and `v` (e.g. `WARPSYNC 0xffffffff`
  at 0xc0 in PI `…block_shfl_persistent-DAG_100n_100e`, graph-coloring's `assignColorsKernel` 0x6d0); none
  has a BAR with a count operand; **in all 200 a full-block BAR is also between `u` and `v`** (Table 3
  column "no full-block BAR between": 0), so the bin is triggered by the WARPSYNC's presence, not by the
  absence of a full barrier. 140 of the PI pairs have `v` inside a barrier loop; in P4, 48 pairs have
  neither pc inside a barrier loop and 12 have `v` inside one (Table 6).
* **early exit** (140, all PI): e.g. PI `…block_shfl-DAG_100n_100e`: `@!P0 STS [R6], RZ` at 0x80, `@P1 EXIT`
  at 0x90 ending its block, `BAR.SYNC` at 0xa0 in the next block, `@!P1 STS [R0.X4], R7` at 0x2b0 — a path
  from `u` reaches the EXIT without the barrier (checked by hand).
* **branch arm** (17, all P9, 2 programs): in all 17 some barrier between is outside postdom(`u`); in 4 all of them
  are. By Table 6, in 13 pairs `u` lies inside a barrier loop and `v` outside it, in 4 `v` inside and `u`
  outside — e.g. P9-crs: `u` = `LDS.128` at 0x460 in the self-loop `.L_x_72` (0x270–0x730) holding
  `BAR.SYNC` at 0x380/0x3c0/0x3f0, `v` = `STS.64` at 0x810 after the loop. The barriers fail to post-dominate
  `u` through the loop's conditional back edge, so "because of a branch" here means the loop branch.
* **other** (65): none has a qualifying barrier on any CFG path between `u` and `v`, except one. 64 pairs
  (P1 48, P3 16; 32 programs, 14 `cc_vertex_data` instantiations of ECL-CC) are shared-memory byte
  accesses (opcodes `LDS.U8/STS.U8` and `STS.U8/STS.U8`; observed at warp distance; R1 strength none;
  Table 5); the one instance inspected by hand (P1 `…Warp…default-100n`, `STS.U8` at 0x140 and 0x320) has no
  BAR or WARPSYNC anywhere in the kernel. The remaining pair (P6 `memcpy-shared_writewrite_race-racy`) is `LDGSTS.E` (cp.async) at 0x70,
  `DEPBAR`, `BAR.SYNC` 0xa0, `LDS` at 0xb0 in one straight-line block; `sync_dominance.analyze` gives R1 no
  credit when the earlier access is an async copy (its T1a rule). For the 64, the class rests on the
  barrier-only clock not listing the pair and no barrier can be what ordered it; **why** the clock does not
  list a pair that the PCDG records at warp distance is not established here (a word-granular edge against a
  byte-exact conflict check is a candidate; **unverified**).

### 2.3 Sensitivity of the "some" bins

Partial participation with "every barrier between is partial" instead of "some": 0 pairs (see above).
Branch arm with "every barrier between is outside postdom(`u`)": 4 of 17.

### 2.4 Re-analysis against the confirm files

9,412 of 9,412 re-analyses reproduce the confirm file's `report_ids` and the number of SC reports
(**proved-in-effect**); 0 failed, 0 analysis timeouts or OOM. 48 keys appeared in two shard outputs (the
re-planning, §5 note b); the merge keeps one whole record per (program, mode) and compares the copies: 0
disagree on pair bins, counts or the confirm check. The pair rows of a kept record are not collapsed
(checked on P4-graph-coloring-norace-small, 6 pairs before and after the merge, job 314202).

## 3. PCDG variance between recordings

### 3.1 Table A — all pairs of recordings (`eval/results/x5/pcdg_variance_tables.md`)

| mode | programs | recording pairs | edge sets identical | edge J min / median / mean | unresolved sets identical | unresolved J min / mean | both unresolved sets empty | RACE ids identical | RACE pc-pair sets identical | RACE vs CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|
| vector-clock | 62 | 184 | 141 | 0.7273 / 1.0000 / 0.9838 | 180 | 0.9574 / 0.9991 | 76 | 169 | 180 | 0 |
| scalar-clock | 61 | 183 | 139 | 0.7157 / 1.0000 / 0.9843 | 179 | 0.9630 / 0.9995 | 75 | 174 | 181 | 0 |

By suite the edge sets differ in recording pairs of P1 (10 of 30, vector-clock), P3 (5), P4 (16), P5 (2) and
PI (10); P6, P7 and P9 are identical throughout (P7 one program, P9 one or two). Among the pairs with a
non-empty unresolved set (108 per mode), 104 are identical in each mode and 4 differ; the largest
symmetric difference is 4 pairs (vector-clock, PI-populate_worklist…, sets of 90–94) and 1 pair
(scalar-clock). In the 43 (vector-clock) and 44 (scalar-clock) recording pairs whose edge sets differ,
the unresolved set is identical in 39 and 40; it never differs while the edge sets are equal. The largest
edge differences: 30 edges in the symmetric difference (vector-clock; PI-populate_worklist…, 84–106 edges
per recording) and P5 `norace_interwarp-block_fence_hrf-indirect` (16 edges each, J 0.7778 between
`t20-parity` and each later store, 1.0 between the later two). **0 pairs common to two recordings changed their
hb_class** (class string of the common unresolved pairs). Per store pair (edge sets identical / recording
pairs, vector-clock): `t20-parity`–`t20-parity2` 45/61, `t20-parity`–X1 48/61, `t20-parity2`–X1 47/61
(scalar-clock 45, 47, 47 of 61); the other tables (B, C, D) are in the appendix.

The RACE report ids differ between recordings in 15 (vector-clock) and 9 (scalar-clock) recording pairs; with the
race-type suffix (RAW/WAR/WAW, which follows the access order seen in the recording) removed the pc-pair sets differ
in 4 and 2: PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e (vector-clock 90, 94 and 90 reports in
the three recordings, scalar-clock 91, 90 and 91) and, vector-clock only, P4-graph-connectivity-racy-small (9 and 9
reports, 7 pc pairs in common between the T20 stores and the X1 recording). The other differing pairs are
the same pc pairs with a different race type (P1 CC_CUDA_E_Topo…, P1 CC_CUDA_V_Topo_Push…, PI push_node…boundsBug…).

## 4. What the numbers mean

**For the sync pass.** The pairs the dynamic leg has to settle are the ones neither R1 nor R3 orders. Across
367 pairs of recordings of the same program that set was identical in 104 of the 108 recording pairs per mode where
it is non-empty, otherwise it differed by at most 4 pairs, and no common pair changed class; the PCDG edge sets, from which
those pairs are judged, differed in 43 and 44 recording pairs (Jaccard down to 0.72) while the unresolved set stayed the same in
39 and 40 of them. The barrier-ordered subset — the pairs that no CFG-only dominance rule certifies — was the same 1,021 pairs in the
two modes' separate recordings of all 4,706 programs, with 599 of them loop-carried, 200 partial-participation (each with a full BAR
also between), 140 early-exit and 17 branch-arm pairs; 65 (6.4 %) have no barrier between their pcs in the CFG, so their class is the
barrier-only clock's silence and not a barrier. In these data the work-list of the sync pass (unresolved pairs) varied little between
recordings (identical in 104 of 108, at most 4 pairs apart otherwise) and its barrier-ordered part was identical between the
two modes' recordings, while the edge set varied more (identical in 141 of 184 and 139 of 183); the data cover the 61–62 programs that have more than one
recording (T20 parity set: 10 each from P1, P3, P4, P5, PI, 9 from P6, one P7, one or two P9) and, for the barrier-ordered pairs,
the mode-to-mode comparison on all programs; they say nothing about an unresolved set of a program that was recorded once.

**For a single-run verdict.** In all 367 pairs of recordings (106 vector-clock and 108 scalar-clock recording pairs are CLEAN, 78 and 75
RACE, judged by the first recording of each pair) the two recordings gave the same program-level verdict: 0 flips. The set of reported pc pairs was identical in 180 of
184 and 181 of 183 recording pairs; the exceptions are two programs whose reports depend on the schedule (the PI atomicBug worklist
program, 90–94 reports; P4 graph-connectivity-racy-small, 9). So in this sample one recording would have given the verdict that every
other recording of the same program gave, and the reported pairs of all but two programs; it would not always have given the same
race-type labels (15 and 9 recording pairs). The sample is small and not random: 61–62 programs chosen as T5b's parity set, 2–4 recordings
each from three builds and different nodes and dates (so the variance measured is recording-to-recording, not schedule variance with
everything else fixed), and 4 barrier-ordered pairs of P1 already change class between launches of one recording.

## 5. Commands (exact; paths relative to `/home/fzheng4/wt-x5`, `CUVEIN_HOME=$PWD`, `PY=/home/fzheng4/AccelProf/.env/bin/python`)

```
git -C /home/fzheng4/AccelProf worktree add /home/fzheng4/wt-x5 -b eval/x5-static-dynamic cuVein     # cuVein = 4094187
sbatch eval/baselines/setup/p_x5_plan.sh                      # 314117: confirm-scan, both plans, dot census  (44 s, c13)
sbatch -J x5-check ... --wrap "test_x5_bins.py; x5_bar_forms.py"                                   # 314121: 11/11, census
# pilot (242 P3/P4/P5 keys, cancelled after 29 keys when the hand check asked for one more field), job 314122
TASK=var NSHARDS=8  sbatch --array=0-7  -J x5-var eval/baselines/setup/p_x5_collect.sh            # 314131: 368 recordings
TASK=bo  NSHARDS=24 sbatch --array=0-23 -J x5-bo  eval/baselines/setup/p_x5_collect.sh            # 314150 (314141 = the same, cancelled at once, §5 note a)
$PY eval/baselines/setup/barrier_ordered_bins.py resplit --plan eval/results/x5/bo_plan.json --base-n 24 \
    --shards 15 16 21 --done 'eval/results/x5/bo_shard*.jsonl' --out eval/results/x5/bo_extra_plan.json
TASK=bo NSHARDS=10 PLAN=eval/results/x5/bo_extra_plan.json OUTPFX=bo_xshard sbatch --array=0-9 -J x5-bo eval/baselines/setup/p_x5_collect.sh   # 314201
sbatch -J x5-report eval/baselines/setup/p_x5_report.sh       # explain + cfgfacts + both reports; final run 314362
$PY eval/baselines/setup/x5_show.py --pairs eval/results/x5/barrier_ordered_pairs.csv --per-bin 1 > eval/results/x5/hand_checks.txt   # 314307
```

Jobs, all `normal`, one CPU each, nodes c13, c14, c16–c19, c25, c48, c61–c63, c74, c77–c79 (16 CPUs each; CPU model and RAM not
recorded by this task — `eval/FINAL_SWEEP.md` §0 gives EPYC 8124P for c61–c63 and 7302P for c74, c77–c79; the others are missing).
Summed per-key analysis time: barrier plan 9,460 records (48 of them duplicates) 70,189 s — six heavy keys took about 2 to 2.5 h each
(P7-srad, P9-mr and P9-tridiagonal, both modes; none reached the 14,400 s per-key cap) — variance 368 recordings 9,847 s. Logs: `eval/x_logs/x5-*.log`.

Sequence notes: (a) 314141 was the first full run; the pilot's hand check showed the "partial participation" bin fires on a loop-path
WARPSYNC although full BARs are also between, so a `full_bar_between` field was added and the run restarted as 314150 before any of its
output was used. (b) After the first hour, shards 15, 16 and 21 of 314150 each sat on a heavy key with ~720 unstarted keys behind it; those 2,170 keys were
re-planned into 10 new shards (314201) at the request of the session that started this one, and the old tasks were cancelled once their in-flight key
was written; an old task can start its next key before the monitor cancels it, hence the 48 keys present in both an old and a new shard output (§2.4). (c) The scripts on the
branch are the final revision; 314150/314201 ran the revision before the `resplit`, `explain` and `cfgfacts` subcommands and the report's duplicate check
and Table 3/5/6 were added — the collect path (the capture of `analyze`, the binner, `PairLog`) is unchanged by those additions. (d) A few short
python commands read small files in home (plan json, shard outputs, the pair csv) on the login node for counts and for `resplit`; no BeeGFS path was read there.

## 6. What remains unverified

* The bins are the brief's rules made precise by me (§1.2): "between" with cycles, "some" semantics of partial participation and branch arm, "BAR"
  = a qualifying barrier, loops = natural loops of the region graph (irreducible control flow is not detected as a loop). Another reading of
  "an EXIT-reaching path between u and the barrier" would move pairs between bins 3, 4 and 5; the hand checks cover one pair per (suite, bin), not every pair.
* The 64 byte-access `other` pairs: why the barrier-only clock does not list them is not established. The count-operand test has no instance in
  the corpus. `partial participation` treats every WARPSYNC as partial, including `WARPSYNC 0xffffffff`.
* The re-analysis ran under Python 3.14.4 / networkx 3.6.1; the reproduction of 9,412 confirm files supports, but does not prove, that
  X1's own environment gave the same ORDERED pairs (the ORDERED pairs themselves were never persisted).
* Variance: the recordings differ in build (`t20-parity` f9d2996a, `t20-parity2` 391cf9cc, X1 2201fcb7), node and date; the T20 stores' meta record no
  library hashes; X1's other two reps are not kept; P7/P9 have one or two programs; the edge definition ignores the observed distance; the
  unresolved definition is mine (some launch left it to the dynamic leg).
* The programs recorded once in the X1 stores (all but the 61–62 of part 2) have their barrier-ordered pairs compared across the two modes only.

## Appendix A — barrier-ordered pairs, all generated tables (eval/results/x5/barrier_ordered_tables.md)

Keys in the plan (a recording and a confirm file): 9412; analysed without error: 9412; failed: 0; not yet run: 0.
Keys present in more than one shard output (deduplicated by (program, mode)): 48; duplicates whose pair bins / counts / confirm check differ from the first copy: 0.

### Table 1 -- barrier-ordered pairs by suite, mode and CFG bin

| suite | mode | confirm files re-analysed | files with >=1 pair | pairs | loop-carried | partial participation | early exit | branch arm | other | pairs also seen in another class |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 400 | 32 | 56 | 8 | 0 | 0 | 0 | 48 | 4 |
| P1 | scalar-clock | 400 | 32 | 56 | 8 | 0 | 0 | 0 | 48 | 4 |
| P3 | vector-clock | 60 | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| P3 | scalar-clock | 60 | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| P4 | vector-clock | 28 | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| P4 | scalar-clock | 28 | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| P5 | vector-clock | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P5 | scalar-clock | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P6 | vector-clock | 34 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| P6 | scalar-clock | 34 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| P7 | vector-clock | 13 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| P7 | scalar-clock | 13 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| P9 | vector-clock | 8 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| P9 | scalar-clock | 8 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| PI | vector-clock | 4130 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| PI | scalar-clock | 4130 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| all | vector-clock | 4706 | 898 | 1021 | 599 | 200 | 140 | 17 | 65 | 4 |
| all | scalar-clock | 4706 | 898 | 1021 | 599 | 200 | 140 | 17 | 65 | 4 |

A pair is one (kernel, ancient pc, current pc, space class) over all launches of the recording; "also seen in another class" counts pairs that were barrier-ordered in one launch and in another hb_class in a different launch.

### Table 2 -- the same pair in the two modes

| suite | distinct pairs | in both modes | vector-clock only | scalar-clock only |
|---|---|---|---|---|
| P1 | 56 | 56 | 0 | 0 |
| P3 | 22 | 22 | 0 | 0 |
| P4 | 83 | 83 | 0 | 0 |
| P6 | 1 | 1 | 0 | 0 |
| P7 | 2 | 2 | 0 | 0 |
| P9 | 17 | 17 | 0 | 0 |
| PI | 840 | 840 | 0 | 0 |
| all | 1021 | 1021 | 0 | 0 |
### Table 3 -- what the bins contain

| suite | mode | partial: a WARPSYNC between | partial: a BAR with a count operand | partial: no full-block BAR between u and v | early exit | branch arm | branch arm: every barrier between is outside postdom(u) | other: no qualifying barrier between u and v | other: a barrier between, none of the tests fired |
|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| P1 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| P3 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| P3 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| P4 | vector-clock | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P4 | scalar-clock | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P6 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P6 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P9 | vector-clock | 0 | 0 | 0 | 0 | 17 | 4 | 0 | 0 |
| P9 | scalar-clock | 0 | 0 | 0 | 0 | 17 | 4 | 0 | 0 |
| PI | vector-clock | 140 | 0 | 0 | 140 | 0 | 0 | 0 | 0 |
| PI | scalar-clock | 140 | 0 | 0 | 140 | 0 | 0 | 0 | 0 |
| all | vector-clock | 200 | 0 | 0 | 140 | 17 | 4 | 64 | 1 |
| all | scalar-clock | 200 | 0 | 0 | 140 | 17 | 4 | 64 | 1 |

### Table 5 -- the pairs of the `other` bin: fields of their verdict records

| suite | mode | space | observed distance | R1 strength | warp-same-instruction | event candidate | edge rescued | race type | pairs |
|---|---|---|---|---|---|---|---|---|---|
| P1 | scalar-clock | shared | warp | none | False | False | False | RAW | 24 |
| P1 | scalar-clock | shared | warp | none | False | False | False | WAW | 24 |
| P1 | vector-clock | shared | warp | none | False | False | False | RAW | 24 |
| P1 | vector-clock | shared | warp | none | False | False | False | WAW | 24 |
| P3 | scalar-clock | shared | warp | none | False | False | False | RAW | 8 |
| P3 | scalar-clock | shared | warp | none | False | False | False | WAW | 8 |
| P3 | vector-clock | shared | warp | none | False | False | False | RAW | 8 |
| P3 | vector-clock | shared | warp | none | False | False | False | WAW | 8 |
| P6 | scalar-clock | shared | block | none | False | False | False | RAW | 1 |
| P6 | vector-clock | shared | block | none | False | False | False | RAW | 1 |


### Table 6 -- the partial / early-exit / branch-arm pairs: is u (v) inside a natural loop that contains a BAR? (pairs; the two modes have the same pairs)

| suite | bin | u in a barrier loop | v in a barrier loop | pairs |
|---|---|---|---|---|
| P4 | partial participation | False | False | 48 |
| P4 | partial participation | False | True | 12 |
| P9 | branch arm | False | True | 4 |
| P9 | branch arm | True | False | 13 |
| PI | early exit | False | False | 140 |
| PI | partial participation | False | True | 140 |

### Table 4 -- the re-analysis against the X1 confirm files

9412 files re-analysed; report ids identical to the confirm file's: 9412; SC-report count identical: 9412.

### Skipped at planning

| suite | mode | reason | keys |
|---|---|---|---|
| P6 | scalar-clock | no recording in the view | 16 |
| P6 | vector-clock | no recording in the view | 16 |
| P7 | scalar-clock | no recording in the view | 1 |
| P7 | vector-clock | no recording in the view | 1 |
| P9 | scalar-clock | no recording in the view | 2 |
| P9 | vector-clock | no recording in the view | 2 |

## Appendix B — PCDG variance, all generated tables (eval/results/x5/pcdg_variance_tables.md)

368 recordings analysed without error (0 failed); 123 (program, mode) groups; 367 pairs of recordings.

Recordings by store: final-2026-10 123, final-2026-10-long 1, t20-parity 122, t20-parity2 122
libsanalyzer by store: final-2026-10: 2201fcb7d57ae783 (123); final-2026-10-long: 2201fcb7d57ae783 (1); t20-parity: None (122); t20-parity2: None (122)

### Table A -- all pairs of recordings

| suite | mode | programs | recording pairs | edges: pairs with J=1 | edges min | edges median | edges mean | unresolved: pairs with J=1 | unres. min | unres. median | unres. mean | both edge sets empty | both unresolved sets empty | RACE-id sets identical | RACE pc-pair sets identical | RACE/CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 10 | 30 | 20 | 0.9000 | 1.0000 | 0.9817 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 23 | 30 | 0 |
| P1 | scalar-clock | 10 | 30 | 25 | 0.9556 | 1.0000 | 0.9961 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 26 | 30 | 0 |
| P3 | vector-clock | 10 | 30 | 25 | 0.9474 | 1.0000 | 0.9941 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 9 | 30 | 30 | 0 |
| P3 | scalar-clock | 10 | 30 | 22 | 0.9583 | 1.0000 | 0.9923 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 9 | 30 | 30 | 0 |
| P4 | vector-clock | 10 | 30 | 14 | 0.9310 | 0.9907 | 0.9837 | 28 | 0.9630 | 1.0000 | 0.9975 | 0 | 9 | 28 | 28 | 0 |
| P4 | scalar-clock | 10 | 30 | 11 | 0.9080 | 0.9889 | 0.9727 | 28 | 0.9630 | 1.0000 | 0.9975 | 0 | 9 | 30 | 30 | 0 |
| P5 | vector-clock | 10 | 30 | 28 | 0.7778 | 1.0000 | 0.9852 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 18 | 30 | 30 | 0 |
| P5 | scalar-clock | 10 | 30 | 28 | 0.7778 | 1.0000 | 0.9852 | 30 | 1.0000 | 1.0000 | 1.0000 | 0 | 18 | 30 | 30 | 0 |
| P6 | vector-clock | 9 | 27 | 27 | 1.0000 | 1.0000 | 1.0000 | 27 | 1.0000 | 1.0000 | 1.0000 | 3 | 21 | 27 | 27 | 0 |
| P6 | scalar-clock | 9 | 27 | 27 | 1.0000 | 1.0000 | 1.0000 | 27 | 1.0000 | 1.0000 | 1.0000 | 3 | 21 | 27 | 27 | 0 |
| P7 | vector-clock | 1 | 3 | 3 | 1.0000 | 1.0000 | 1.0000 | 3 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 3 | 3 | 0 |
| P7 | scalar-clock | 1 | 3 | 3 | 1.0000 | 1.0000 | 1.0000 | 3 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 3 | 3 | 0 |
| P9 | vector-clock | 2 | 4 | 4 | 1.0000 | 1.0000 | 1.0000 | 4 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 4 | 4 | 0 |
| P9 | scalar-clock | 1 | 3 | 3 | 1.0000 | 1.0000 | 1.0000 | 3 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 3 | 3 | 0 |
| PI | vector-clock | 10 | 30 | 20 | 0.7273 | 1.0000 | 0.9557 | 28 | 0.9574 | 1.0000 | 0.9972 | 0 | 12 | 24 | 28 | 0 |
| PI | scalar-clock | 10 | 30 | 20 | 0.7157 | 1.0000 | 0.9580 | 28 | 0.9890 | 1.0000 | 0.9993 | 0 | 12 | 25 | 28 | 0 |
| all | vector-clock | 62 | 184 | 141 | 0.7273 | 1.0000 | 0.9838 | 180 | 0.9574 | 1.0000 | 0.9991 | 3 | 76 | 169 | 180 | 0 |
| all | scalar-clock | 61 | 183 | 139 | 0.7157 | 1.0000 | 0.9843 | 179 | 0.9630 | 1.0000 | 0.9995 | 3 | 75 | 174 | 181 | 0 |

### Table B -- final-2026-10 vs final-2026-10-long (1 recording pairs)

| suite | mode | programs | recording pairs | edges: pairs with J=1 | edges min | edges median | edges mean | unresolved: pairs with J=1 | unres. min | unres. median | unres. mean | both edge sets empty | both unresolved sets empty | RACE-id sets identical | RACE pc-pair sets identical | RACE/CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P9 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| all | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |

### Table B -- t20-parity vs final-2026-10 (122 recording pairs)

| suite | mode | programs | recording pairs | edges: pairs with J=1 | edges min | edges median | edges mean | unresolved: pairs with J=1 | unres. min | unres. median | unres. mean | both edge sets empty | both unresolved sets empty | RACE-id sets identical | RACE pc-pair sets identical | RACE/CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 10 | 10 | 7 | 0.9000 | 1.0000 | 0.9853 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 9 | 10 | 0 |
| P1 | scalar-clock | 10 | 10 | 8 | 0.9663 | 1.0000 | 0.9953 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 8 | 10 | 0 |
| P3 | vector-clock | 10 | 10 | 8 | 0.9474 | 1.0000 | 0.9929 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P3 | scalar-clock | 10 | 10 | 7 | 0.9583 | 1.0000 | 0.9902 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P4 | vector-clock | 10 | 10 | 6 | 0.9310 | 1.0000 | 0.9840 | 9 | 0.9630 | 1.0000 | 0.9963 | 0 | 3 | 9 | 9 | 0 |
| P4 | scalar-clock | 10 | 10 | 5 | 0.9080 | 0.9828 | 0.9752 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P5 | vector-clock | 10 | 10 | 9 | 0.7778 | 1.0000 | 0.9778 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P5 | scalar-clock | 10 | 10 | 9 | 0.7778 | 1.0000 | 0.9778 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P6 | vector-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P6 | scalar-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P7 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P7 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| P9 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| PI | vector-clock | 10 | 10 | 7 | 0.8298 | 1.0000 | 0.9603 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 4 | 8 | 10 | 0 |
| PI | scalar-clock | 10 | 10 | 7 | 0.8300 | 1.0000 | 0.9648 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 4 | 8 | 10 | 0 |
| all | vector-clock | 61 | 61 | 48 | 0.7778 | 1.0000 | 0.9836 | 60 | 0.9630 | 1.0000 | 0.9994 | 1 | 25 | 57 | 60 | 0 |
| all | scalar-clock | 61 | 61 | 47 | 0.7778 | 1.0000 | 0.9841 | 61 | 1.0000 | 1.0000 | 1.0000 | 1 | 25 | 57 | 61 | 0 |

### Table B -- t20-parity vs t20-parity2 (122 recording pairs)

| suite | mode | programs | recording pairs | edges: pairs with J=1 | edges min | edges median | edges mean | unresolved: pairs with J=1 | unres. min | unres. median | unres. mean | both edge sets empty | both unresolved sets empty | RACE-id sets identical | RACE pc-pair sets identical | RACE/CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 10 | 10 | 6 | 0.9000 | 1.0000 | 0.9739 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 7 | 10 | 0 |
| P1 | scalar-clock | 10 | 10 | 9 | 0.9889 | 1.0000 | 0.9989 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 9 | 10 | 0 |
| P3 | vector-clock | 10 | 10 | 9 | 0.9655 | 1.0000 | 0.9966 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P3 | scalar-clock | 10 | 10 | 6 | 0.9583 | 1.0000 | 0.9885 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P4 | vector-clock | 10 | 10 | 4 | 0.9425 | 0.9902 | 0.9846 | 9 | 0.9630 | 1.0000 | 0.9963 | 0 | 3 | 10 | 10 | 0 |
| P4 | scalar-clock | 10 | 10 | 4 | 0.9184 | 0.9902 | 0.9735 | 9 | 0.9630 | 1.0000 | 0.9963 | 0 | 3 | 10 | 10 | 0 |
| P5 | vector-clock | 10 | 10 | 9 | 0.7778 | 1.0000 | 0.9778 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P5 | scalar-clock | 10 | 10 | 9 | 0.7778 | 1.0000 | 0.9778 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P6 | vector-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P6 | scalar-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P7 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P7 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| P9 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| PI | vector-clock | 10 | 10 | 6 | 0.7636 | 1.0000 | 0.9476 | 9 | 0.9574 | 1.0000 | 0.9957 | 0 | 4 | 8 | 9 | 0 |
| PI | scalar-clock | 10 | 10 | 6 | 0.7255 | 1.0000 | 0.9468 | 9 | 0.9890 | 1.0000 | 0.9989 | 0 | 4 | 9 | 9 | 0 |
| all | vector-clock | 61 | 61 | 45 | 0.7636 | 1.0000 | 0.9804 | 59 | 0.9574 | 1.0000 | 0.9987 | 1 | 25 | 56 | 60 | 0 |
| all | scalar-clock | 61 | 61 | 45 | 0.7255 | 1.0000 | 0.9812 | 59 | 0.9630 | 1.0000 | 0.9992 | 1 | 25 | 59 | 60 | 0 |

### Table B -- t20-parity2 vs final-2026-10 (122 recording pairs)

| suite | mode | programs | recording pairs | edges: pairs with J=1 | edges min | edges median | edges mean | unresolved: pairs with J=1 | unres. min | unres. median | unres. mean | both edge sets empty | both unresolved sets empty | RACE-id sets identical | RACE pc-pair sets identical | RACE/CLEAN differs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 10 | 10 | 7 | 0.9444 | 1.0000 | 0.9860 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 7 | 10 | 0 |
| P1 | scalar-clock | 10 | 10 | 8 | 0.9556 | 1.0000 | 0.9942 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 9 | 10 | 0 |
| P3 | vector-clock | 10 | 10 | 8 | 0.9483 | 1.0000 | 0.9930 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P3 | scalar-clock | 10 | 10 | 9 | 0.9825 | 1.0000 | 0.9982 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 10 | 10 | 0 |
| P4 | vector-clock | 10 | 10 | 4 | 0.9583 | 0.9835 | 0.9824 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 3 | 9 | 9 | 0 |
| P4 | scalar-clock | 10 | 10 | 2 | 0.9184 | 0.9733 | 0.9695 | 9 | 0.9630 | 1.0000 | 0.9963 | 0 | 3 | 10 | 10 | 0 |
| P5 | vector-clock | 10 | 10 | 10 | 1.0000 | 1.0000 | 1.0000 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P5 | scalar-clock | 10 | 10 | 10 | 1.0000 | 1.0000 | 1.0000 | 10 | 1.0000 | 1.0000 | 1.0000 | 0 | 6 | 10 | 10 | 0 |
| P6 | vector-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P6 | scalar-clock | 9 | 9 | 9 | 1.0000 | 1.0000 | 1.0000 | 9 | 1.0000 | 1.0000 | 1.0000 | 1 | 7 | 9 | 9 | 0 |
| P7 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P7 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 1 | 1 | 1 | 0 |
| P9 | vector-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| P9 | scalar-clock | 1 | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 | 0 |
| PI | vector-clock | 10 | 10 | 7 | 0.7273 | 1.0000 | 0.9591 | 9 | 0.9574 | 1.0000 | 0.9957 | 0 | 4 | 8 | 9 | 0 |
| PI | scalar-clock | 10 | 10 | 7 | 0.7157 | 1.0000 | 0.9624 | 9 | 0.9890 | 1.0000 | 0.9989 | 0 | 4 | 8 | 9 | 0 |
| all | vector-clock | 61 | 61 | 47 | 0.7273 | 1.0000 | 0.9870 | 60 | 0.9574 | 1.0000 | 0.9993 | 1 | 25 | 55 | 59 | 0 |
| all | scalar-clock | 61 | 61 | 47 | 0.7157 | 1.0000 | 0.9876 | 59 | 0.9630 | 1.0000 | 0.9992 | 1 | 25 | 58 | 60 | 0 |

### Table C -- the 25 recording pairs with the lowest edge Jaccard

| program | mode | a | b | edges a | edges b | J edges | unres a | unres b | J unresolved | class changed (common) | verdict a/b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity2 | final-2026-10 | 84 | 91 | 0.7157 | 90 | 91 | 0.9890 | 0 | RACE/RACE |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 92 | 84 | 0.7255 | 91 | 90 | 0.9890 | 0 | RACE/RACE |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity2 | final-2026-10 | 106 | 84 | 0.7273 | 94 | 90 | 0.9574 | 0 | RACE/RACE |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity | t20-parity2 | 88 | 106 | 0.7636 | 90 | 94 | 0.9574 | 0 | RACE/RACE |
| P5-norace_interwarp-block_fence_hrf-indirect | scalar-clock | t20-parity | t20-parity2 | 16 | 16 | 0.7778 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| P5-norace_interwarp-block_fence_hrf-indirect | scalar-clock | t20-parity | final-2026-10 | 16 | 16 | 0.7778 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| P5-norace_interwarp-block_fence_hrf-indirect | vector-clock | t20-parity | t20-parity2 | 16 | 16 | 0.7778 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| P5-norace_interwarp-block_fence_hrf-indirect | vector-clock | t20-parity | final-2026-10 | 16 | 16 | 0.7778 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity | final-2026-10 | 88 | 84 | 0.8298 | 90 | 90 | 1.0000 | 0 | RACE/RACE |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity | final-2026-10 | 92 | 91 | 0.8300 | 91 | 91 | 1.0000 | 0 | RACE/RACE |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 5 | 6 | 0.8333 | 2 | 2 | 1.0000 | 0 | RACE/RACE |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | scalar-clock | t20-parity | final-2026-10 | 5 | 6 | 0.8333 | 2 | 2 | 1.0000 | 0 | RACE/RACE |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | vector-clock | t20-parity | t20-parity2 | 5 | 6 | 0.8333 | 2 | 2 | 1.0000 | 0 | RACE/RACE |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | vector-clock | t20-parity | final-2026-10 | 5 | 6 | 0.8333 | 2 | 2 | 1.0000 | 0 | RACE/RACE |
| P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | vector-clock | t20-parity | t20-parity2 | 9 | 10 | 0.9000 | 4 | 4 | 1.0000 | 0 | RACE/RACE |
| P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | vector-clock | t20-parity | final-2026-10 | 9 | 10 | 0.9000 | 4 | 4 | 1.0000 | 0 | RACE/RACE |
| P4-reduction-racy-small | scalar-clock | t20-parity | final-2026-10 | 81 | 85 | 0.9080 | 26 | 26 | 1.0000 | 0 | RACE/RACE |
| PI-conditional_edge_neighbors_block_shfl_reverse_cond_guardBug_atomicBug-power_law_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 11 | 12 | 0.9167 | 3 | 3 | 1.0000 | 0 | RACE/RACE |
| PI-conditional_edge_neighbors_block_shfl_reverse_cond_guardBug_atomicBug-power_law_200n_1000e | scalar-clock | t20-parity2 | final-2026-10 | 12 | 11 | 0.9167 | 3 | 3 | 1.0000 | 0 | RACE/RACE |
| P4-1dconv-norace-large | scalar-clock | t20-parity | t20-parity2 | 49 | 45 | 0.9184 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| P4-1dconv-norace-large | scalar-clock | t20-parity2 | final-2026-10 | 45 | 49 | 0.9184 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| P1-BFS_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Thread_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoOverflowBug_NoLivelockBug-default-1296n | vector-clock | t20-parity | t20-parity2 | 86 | 85 | 0.9213 | 0 | 0 | 1.0000 | 0 | CLEAN/CLEAN |
| PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity2 | final-2026-10 | 135 | 125 | 0.9259 | 50 | 50 | 1.0000 | 0 | RACE/RACE |
| P4-reduction-racy-small | scalar-clock | t20-parity | t20-parity2 | 81 | 81 | 0.9286 | 26 | 27 | 0.9630 | 0 | RACE/RACE |
| P4-reduction-racy-large | scalar-clock | t20-parity | t20-parity2 | 86 | 82 | 0.9310 | 27 | 27 | 1.0000 | 0 | RACE/RACE |

### Table D -- the 25 recording pairs with the lowest unresolved-pair Jaccard (both sets non-empty or one non-empty)

| program | mode | a | b | unres a | unres b | common | J unresolved | class changed (common) | J edges |
|---|---|---|---|---|---|---|---|---|---|
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity2 | final-2026-10 | 94 | 90 | 90 | 0.9574 | 0 | 0.7273 |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity | t20-parity2 | 90 | 94 | 90 | 0.9574 | 0 | 0.7636 |
| P4-reduction-racy-small | scalar-clock | t20-parity | t20-parity2 | 26 | 27 | 26 | 0.9630 | 0 | 0.9286 |
| P4-reduction-racy-small | scalar-clock | t20-parity2 | final-2026-10 | 27 | 26 | 26 | 0.9630 | 0 | 0.9529 |
| P4-reduction-racy-small | vector-clock | t20-parity | final-2026-10 | 26 | 27 | 26 | 0.9630 | 0 | 0.9880 |
| P4-reduction-racy-small | vector-clock | t20-parity | t20-parity2 | 26 | 27 | 26 | 0.9630 | 0 | 0.9881 |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity2 | final-2026-10 | 90 | 91 | 90 | 0.9890 | 0 | 0.7157 |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 91 | 90 | 90 | 0.9890 | 0 | 0.7255 |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity | final-2026-10 | 90 | 90 | 90 | 1.0000 | 0 | 0.8298 |
| PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e | scalar-clock | t20-parity | final-2026-10 | 91 | 91 | 91 | 1.0000 | 0 | 0.8300 |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 2 | 2 | 2 | 1.0000 | 0 | 0.8333 |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | scalar-clock | t20-parity | final-2026-10 | 2 | 2 | 2 | 1.0000 | 0 | 0.8333 |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | vector-clock | t20-parity | t20-parity2 | 2 | 2 | 2 | 1.0000 | 0 | 0.8333 |
| PI-push_node_neighbors_reverse_cond_atomicBug_break-counterDAG_200n_1000e | vector-clock | t20-parity | final-2026-10 | 2 | 2 | 2 | 1.0000 | 0 | 0.8333 |
| P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | vector-clock | t20-parity | t20-parity2 | 4 | 4 | 4 | 1.0000 | 0 | 0.9000 |
| P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n | vector-clock | t20-parity | final-2026-10 | 4 | 4 | 4 | 1.0000 | 0 | 0.9000 |
| P4-reduction-racy-small | scalar-clock | t20-parity | final-2026-10 | 26 | 26 | 26 | 1.0000 | 0 | 0.9080 |
| PI-conditional_edge_neighbors_block_shfl_reverse_cond_guardBug_atomicBug-power_law_200n_1000e | scalar-clock | t20-parity | t20-parity2 | 3 | 3 | 3 | 1.0000 | 0 | 0.9167 |
| PI-conditional_edge_neighbors_block_shfl_reverse_cond_guardBug_atomicBug-power_law_200n_1000e | scalar-clock | t20-parity2 | final-2026-10 | 3 | 3 | 3 | 1.0000 | 0 | 0.9167 |
| PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity2 | final-2026-10 | 50 | 50 | 50 | 1.0000 | 0 | 0.9259 |
| P4-reduction-racy-large | scalar-clock | t20-parity | t20-parity2 | 27 | 27 | 27 | 1.0000 | 0 | 0.9310 |
| P4-reduction-racy-large | vector-clock | t20-parity | final-2026-10 | 27 | 27 | 27 | 1.0000 | 0 | 0.9310 |
| PI-conditional_edge_neighbors_block_persistent_reverse_cond_guardBug-DAG_100n_200e | vector-clock | t20-parity | t20-parity2 | 2 | 2 | 2 | 1.0000 | 0 | 0.9375 |
| PI-conditional_edge_neighbors_block_persistent_reverse_cond_guardBug-DAG_100n_200e | vector-clock | t20-parity2 | final-2026-10 | 2 | 2 | 2 | 1.0000 | 0 | 0.9375 |
| PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e | vector-clock | t20-parity | final-2026-10 | 50 | 50 | 50 | 1.0000 | 0 | 0.9398 |


## Appendix C — dot census (eval/results/x5/bar_forms.txt)

```
distinct dot files 858, with BAR/WARPSYNC 233
704 ('BAR.SYNC.DEFER_BLOCKING', ('imm0',))
168 ('WARPSYNC', ('immN',))
49 ('WARPSYNC', ('reg',))
40 ('BAR.SYNC', ('imm0',))
16 ('BAR.RED.OR.DEFER_BLOCKING', ('imm0', 'pred'))
8 ('BAR.RED.POPC.DEFER_BLOCKING', ('imm0', 'pred'))
EXIT/RET placement (guarded/plain, position in the basic block):
1874 ('guarded', 'last')
1312 ('plain', 'last')
```

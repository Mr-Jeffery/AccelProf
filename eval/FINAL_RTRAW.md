# X4 — the rtraw case study (2026-10-13)

Branch `eval/final-rtraw` from `cuVein` 4094187 (X0 merged; the detector is frozen at fce124c and
nothing under `sanalyzer/`, `nv-compute/` or `python/` changed here: one driver script, one sbatch
script, the recorded dumps and this report). Runtime: the **installed** one (`ACCEL_PROF_HOME` =
the main checkout, built from ba99486 and installed by d38d057): libsanalyzer `2201fcb7`, collector
`ee78cb89`, fatbin `a2d7368b` (sha256 prefixes, checked on every node and stored in each
`node.json`). Hardware: three `rtx4060ti16g` nodes, RTX 4060 Ti 16 GB (sm_89), CUDA 13.3:
**c58** (AMD EPYC 9115, driver 580.82.07), **c62** (AMD EPYC 8124P, 580.82.07), **c77** (AMD EPYC
7302P, 580.95.05). SLURM jobs 311940 (c58), 311941 (c62), 311942 (c77), 311944 (c58, the
scalar-clock ScoR runs); smoke job 311937 (not cited). ScoR binary
`ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw` (the manifest's exe, sha256 `3ef6a298…`).

## Summary

| | runs | acquisition order | the rtraw pair (block 0's `data[0] = 1` after its unlock vs block 1's read of `data[0]`) |
|---|---|---|---|
| ScoR kernel, vector-clock, recorded clock (step 1) | 150 (50 per node) | **block 1 first in 150 / 150** | **Latent** (class SC, `latent-sc`) in 149; Strong conflict, `a2_uncertain`, in 1 (an A2-inverted trace) |
| forced-order kernel, vector-clock (step 2) | 15 (5 per node) | block 0 first in 15 / 15 (forced) | **Strong conflict** (class SC, `sc`), RAW, 1 instance, **not** `a2_uncertain` |
| forced-order kernel, scalar-clock (step 2) | 15 (5 per node) | block 0 first in 15 / 15 | **Strong conflict** (`sc`) |
| ScoR kernel, vector-clock, certain clock (step 3) | 30 (10 per node) | block 1 first in 30 / 30 | **Strong conflict** (SC, flagged) in the 20 runs on c62/c77, whose hand-off windows overlap; **Latent** (SC) in the 10 runs on c58, whose windows do not |
| ScoR kernel, scalar-clock (beyond the brief) | 50 (c58) | block 1 first in 50 / 50 | Strong conflict in 48; **ORDERED** in 2 (A2-inverted traces; R3 over-certifies, §6) |

1. **Block 0 never acquires the lock first**: 0 of 150 vector-clock recordings on three nodes of
   three CPU models, and 0 of the 80 further ScoR recordings (30 certain, 50 scalar-clock). On this
   hardware the acquisition order of the ScoR kernel is deterministic, so the paper shows the racy
   order with the forced kernel. The window schedule is **not** the same everywhere, though. Block 1
   always wins with its first CAS and block 0 spins. On c62 and c77 (100 / 100) block 0's winning
   CAS is recorded inside block 1's unlock window. On c58 (49 / 50) block 1's exit record closes
   that window first. In 1 of 50 on c58, block 0's winning CAS is recorded *before* the unlock it
   read from (A2).
2. **The racy order's pair is an SC, not a DR.** Both accesses are `volatile` and lower to
   `LDG/STG.E.STRONG.SYS`. Under T10's token rule (`hb_proof.tex` §7, the labeling paragraph:
   "a load or store is strong at the scope its `.STRONG.<scope>` token names … `volatile`
   included") they are strong at system scope. That covers the two threads (different blocks of
   one grid), so the pair is morally strong. An unordered morally strong conflict is not a data
   race under PTX §8.7.1. It is an unordered strong conflict, the `sc` class: reported,
   informational at the PTX operating points, and a report under ScoRD's notion (D2, amended). In
   the forced kernel no RMW window on the lock overlaps, so the report is **not** `a2_uncertain`
   (0 of 1 instance).
3. **The certain clock does not turn the recorded run into a Race**, contrary to
   `eval/CERTAIN_CLOCK.md` (§0 and §5). (a) Where it reports the pair, the pair is a **Strong
   conflict** (SC). The DR it adds is the plain `dummy` store *inside* the two critical sections
   (pcs 0x170 / 0x2f0), a pair the fenced lock orders in every schedule. The certain clock reports
   it only because it cannot certify a contended hand-off. T16's own detail files show the same
   split: `cer_pairs` = {[320, 832]: SC, [368, 752]: DR}. So the program-level "RACE (a TP gained)"
   of `CERTAIN_CLOCK.md` rests on the `dummy` pair, not on the rtraw race. (b) It reports at all
   only when the hand-off's windows overlap. On c58's schedule the unlock window is closed by block
   1's exit record before block 0's winning CAS, the certain clock accepts the edge, and the pair
   stays Latent (10 / 10 recordings; 49 / 49 same-trace replays).
4. **Finding (detector, not fixed: code freeze):** on the A2-inverted trace, R3's landing rule
   misses the writer's own unlock. The chain `0x1b0 → 0x330` (block 1's unlock → block 0's unlock)
   certifies the racy pair as ORDERED. In scalar-clock mode (no `hb_races` veto) that hides the
   report: 2 of 50 real recordings on c58. §6 has the mechanism and a proposed fix.

**Paragraph for the paper.** *On the RTX 4060 Ti, ScoR's `race_interblock_none-lock_rtraw` always
gives the lock to block 1 first (0 of 150 vector-clock recordings on three nodes show the other
order). In that execution block 1's fenced unlock hands the lock to block 0 before block 0's
post-unlock store, so the store is ordered after block 1's read. No static rule certifies that
order for every schedule, and cuVein reports the pair as Latent (class SC: both accesses are
`volatile`, hence strong at system scope). The other acquisition order is reached with the same
code under a flag that forces block 0 first. There the pair is reported in both modes as an
unordered strong conflict: one RAW instance, not A2-uncertain, since no window of the lock hand-off
overlaps. The certain clock reports the recorded run's pair only where the hand-off windows overlap
(100 of the 150 recordings, all of them on two of the three nodes), and then as a strong conflict.*

## 1. The kernels and the pair

Both kernels share one source structure. Block 0 runs `lock (CAS spin); fence; dummy = data[0];
fence; unlock (EXCH); data[0] = 1`. Block 1 runs `lock; fence; dummy = data[0]; fence; unlock`.
The forced kernel adds an unfenced flag `go`: block 0 raises it after its last access, and block 1
spins on it before locking. Under the instance gate it is neither a release nor an acquire (T18,
`write_after_unlock_other_schedule.cu`). SASS from the dots (identical on the three nodes, md5
equal per kernel):

| role | ScoR pc | forced pc | SASS |
|---|---|---|---|
| block 1 flag spin (forced only) | — | 0x0b0 | `ATOMG.E.ADD.STRONG.GPU` |
| block 1 lock CAS | 0x0b0 | 0x150 | `ATOMG.E.CAS.STRONG.GPU` |
| block 1 read of `data[0]` (**the pair's read**) | 0x140 | 0x1e0 | `LDG.E.STRONG.SYS` |
| block 1 `dummy` store | 0x170 | 0x210 | `STG.E` |
| block 1 unlock | 0x1b0 | 0x250 | `ATOMG.E.EXCH.STRONG.GPU` |
| block 0 lock CAS | 0x230 | 0x2d0 | `ATOMG.E.CAS.STRONG.GPU` |
| block 0 read of `data[0]` | 0x2c0 | 0x360 | `LDG.E.STRONG.SYS` |
| block 0 `dummy` store | 0x2f0 | 0x3b0 | `STG.E` |
| block 0 unlock | 0x330 | 0x3f0 | `ATOMG.E.EXCH.STRONG.GPU` |
| block 0 `data[0] = 1` (**the pair's write**) | 0x340 | 0x400 | `STG.E.STRONG.SYS` |
| block 0 raises `go` (forced only) | — | 0x410 | `ATOMG.E.EXCH.STRONG.GPU` |

Each critical section is `MEMBAR.SC.GPU; CCTL.IVALL` after the CAS and `MEMBAR.SC.GPU; CCTL.IVALL`
before the unlock. The hand-off is fenced on both sides, so the instance gate treats the unlock as
a release and the winning CAS as an acquire.

**How the order is read from a dump** (`final_rtraw.py analyze`). A block's CAS attempts are its
records on the lock word before its first other record. The last of them is the winning CAS (the
loop exits only on success, and one thread's records are in program order). The first acquirer is
the block whose winning CAS has the smaller `seq`. This is cross-checked by the order of the two
critical sections' first records. A critical-section record is issued after the CAS returned, so
that order does not depend on A2. The two orders agree on 260 / 260 runs. *Window* is T14's: an
RMW's window is [its `seq`, the `seq` of its thread's next record), exits included. The hand-off
overlaps when the next RMW on the lock word after the first owner's unlock is recorded inside the
unlock's window. "A2" in the tables means the second owner's winning CAS is recorded *before* the
unlock it read from.

## 2. Step 1 — the ScoR kernel, 150 vector-clock recordings

`YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock`, the sidecar, the lossless dump
(`BASELINE_HB_DUMP=1`), `YOSEMITE_HB_STATS=0`, no other `YOSEMITE_*` or `CUVEIN_*` variable (each
run's `meta.json` lists the exact set). 50 runs per node, every one rc 0, one kernel JSON.

| node | runs | block 0 first | block 1 first | A2-inverted | hand-off windows overlap | pair Latent (SC) | pair Strong conflict |
|---|---|---|---|---|---|---|---|
| c58 | 50 | 0 | 50 | 1 | 0 | 49 | 1 (flagged) |
| c62 | 50 | 0 | 50 | 0 | 50 | 50 | 0 |
| c77 | 50 | 0 | 50 | 0 | 50 | 50 | 0 |
| **all** | **150** | **0** | **150** | **1** | **100** | **149** | **1** |

**Block 0 never acquires first in 150 runs.** The paper therefore says the acquisition order is
deterministic on this hardware and uses the forced kernel (§3). The three window schedules, with
the records of one run each (lock-word RMWs; `@seq[..window end)`):

| schedule | runs | lock word | the pair | verdict |
|---|---|---|---|---|
| **A** (c58 run 1) | c58: 49 | b1 CAS 0x0b0@0[..3) wins; b0 CAS 0x230 @1, @2, @4, @6[..9) fail; **b1 unlock 0x1b0@7[..8)**, b1 exit @8; **b0 CAS 0x230@9 wins**; b0 unlock 0x330@12 | read 0x140@3 (b1), write 0x340@13 (b0): WAR | Latent (SC); `hb_races` empty; the hand-off edge 7→9 does not overlap |
| **B** (c62 run 1) | c62: 50, c77: 50 | as A up to b0 CAS @6[..8); **b1 unlock 0x1b0@7[..9)**; **b0 CAS 0x230@8 wins** (inside the unlock's window); b1 exit @9; b0 unlock @12 | read @3, write @13: WAR | Latent (SC); `hb_races` empty; the edge 7→8 overlaps |
| **C** (c58 run 3) | c58: 1 | b0 CAS @1, @2, @4, **@6[..9) wins**, recorded before **b1 unlock 0x1b0@7[..8)**; b1 exit @8; b0 unlock 0x330@11 | read @3, write @12: WAR | Strong conflict (SC, 1 instance, `a2_uncertain` 1/1) plus a Race on the `dummy` WAW 0x170→0x2f0 (DR, 1/1 flagged) |

In A and B the pair is ordered in the execution by block 1's read → unlock (fenced) → block 0's
winning CAS (fenced) → block 0's write. No static certificate exists: R1 none, R3 declines (the
write lies past its own thread's release, `_past_release`), the barrier-only clock leaves it
unordered (`hb_races_sync_only` holds [0x140, 0x340]). The pair has no dependency edge and is found
as an event-stream candidate. Hence `latent-sc`: a Latent verdict of class SC. At program level
this is CLEAN at both operating points with one SC report (149 / 150). Schedule C is A2 in vivo on
the installed runtime, the same "fourth CAS wins before the unlock" schedule
`eval/A2_WINDOWS.md` §10 recorded under the T15 collector. The recorded chain runs 6→7, the
wrong way, so the hand-off is lost and both the pair and the `dummy` WAW come out unordered. Both
reports are flagged. The program reads RACE at Race alone, flagged reports only.

## 3. Step 2 — the forced-order kernel

`python/testdata/write_after_unlock_other_schedule.cu`, built on each node exactly as
`test_hb_substitutions._trace` builds it (`nvcc -arch=native -lineinfo --cudart shared`; the host
ELF differs per node, the SASS is identical). 5 recordings per mode per node with the dump, the
same environment as step 1 apart from the mode. Every one of the 30 has the same schedule. The
flag forced block 0 first in 30 / 30 (`a2_aware.without_flag`). Records of c58 run 1 (vector-clock;
the scalar-clock runs have the same seqs):

```
 b1 0x0b0 ADD go   @0 @2 @4 @6 @8 @10 @12   (spin; @12 reads go = 1)
 b0 0x2d0 CAS lock @1  (wins, 1 attempt)     b0 0x360 read data @3   b0 0x3b0 dummy @5
 b0 0x3f0 EXCH lock @7 [..9)                 b0 0x400 write data @9  b0 0x410 EXCH go @11   exit @13
 b1 0x150 CAS lock @14 (wins, 1 attempt)     b1 0x1e0 read data @15  b1 0x210 dummy @16
 b1 0x250 EXCH lock @17                      exit @18
```

* **vector-clock (15 / 15 identical):** `hb_races` holds the pair, `a_pc` 0x400 (block 0, tid 0)
  → `b_pc` 0x1e0 (block 1, tid 1024), RAW, class SC, count 1, `a2_uncertain` 0. Verdict `SC`,
  class `sc`: **Strong conflict**, not flagged. No other report. Program: CLEAN at both operating
  points, one SC report.
* **DR or SC:** SC. The read is `LDG.E.STRONG.SYS` and the write `STG.E.STRONG.SYS` (`volatile`).
  Under T10's rule both are strong at `sys` scope, which includes both threads (different blocks,
  distance grid), on one 4-byte location. They are morally strong, hence not a data race under PTX
  §8.7.1 but an unordered strong conflict (`hb_proof.tex` §7's labeling paragraph; D9; D12 for the
  class). Under the pre-T10 `generic` policy it was a DR (`test_hb_substitutions` asserts the
  class per policy).
* **`a2_uncertain`: not flagged.** The lock word's only cross-block edge is block 0's unlock @7
  [..9) → block 1's CAS @14. That window is closed by block 0's data store @9, so no lock window
  overlaps. The only overlapping windows are on `go` (block 1's spin @10[..12) ∋ block 0's `go`
  store @11, and that store's window [..13) ∋ the spin @12): 2 uncertain edges in `hb_chain`. The
  flag is unfenced (rel = acq = 0), so those edges order nothing. The same trace replayed under the
  certain clock refuses exactly those 2 edges and gives the identical report.
* **scalar-clock (15 / 15 identical):** verdict `SC`, class `sc`: **Strong conflict**. There is no
  barrier, so the barrier-only clock leaves the pair unordered. R1 has nothing. R3 has no chain: the
  write's PO-next RMW is the unfenced `go` store, so no release-fenced start exists. The class comes
  from R2: both pcs are coherent at `sys` ≥ grid. Program CLEAN with one SC report.

## 4. Step 3 — the certain clock

**Recordings** (`YOSEMITE_HB_GATE_POLICY=certain`, 10 per node; every dump carries
`hb_gate_policy: certain`):

| node | runs | schedule | chain edges refused | the pair | other reports | program (Race alone) |
|---|---|---|---|---|---|---|
| c58 | 10 | A | 2 of 7 (0→1, 6→7) | **Latent** (SC); the hand-off 7→9 accepted | none | CLEAN |
| c62 | 10 | B | 3 of 7 (0→1, 6→7, **7→8**) | **Strong conflict** (WAR, SC, 1 instance, `a2_uncertain` 1/1) | `dummy` WAW 0x170→0x2f0 **Race** (structural DR, 1/1 flagged) | RACE |
| c77 | 10 | B | 3 of 7 | Strong conflict (as c62) | `dummy` WAW Race (as c62) | RACE |

**The same 150 recorded traces replayed under the certain clock** (`hb_oracle --gate-policy
certain`, `hb_races` swapped in as `t16_rescore.py` does): schedule B (100) → Strong conflict +
`dummy` Race; schedule A (49) → Latent; schedule C (1) → Strong conflict + `dummy` Race. The
replays and the recordings agree schedule for schedule.

**Against `eval/CERTAIN_CLOCK.md`**, which says the certain clock "turns it from Latent into a Race
… reports the rtraw pair as a `structural` DR plus an SC pair". That is **not confirmed**, on two
counts:

1. *The rtraw pair is the SC; the DR is the `dummy` pair.* T16's detail files
   (`/home/fzheng4/wt-t16/eval/results/t16-rescore/detail-{main,exits}/P5-race_interblock_none-lock_rtraw.json`)
   record `cer_pairs` = [[320, 832] (0x140 / 0x340, the rtraw pair): SC 1], [[368, 752] (0x170 /
   0x2f0, `dummy`): DR 1]. The `dummy` stores sit inside the two fenced critical sections. The lock
   orders them in every schedule, so this DR is not a race of the program. It is the incompleteness
   the certain clock pays on a contended hand-off. The program-level "RACE, a TP gained" at the
   Race (sound) point therefore comes from a pair that does not race, while the rtraw pair itself is
   an SC: informational under PTX counting, a report under ScoRD's notion.
2. *It depends on the schedule.* T16's two dumps (copied to `eval/results/final-rtraw/t16-dumps/`)
   are of schedule B or worse. `evcand` (c68, pre-T3b, no exit records): block 0 wins at seq 8 and
   block 1's unlock window never closes. `t12-eval-t12rb` (c70, 2026-09-30, job 294733): block 0
   wins at seq 8 inside the unlock's window [7, 9). On the installed runtime, c58 lands in schedule
   A and the certain clock leaves the pair Latent.

Suggested correction for `CERTAIN_CLOCK.md` §0/§5, left to Jeffery because X2 works on
`eval/final-certain` in parallel: *"…`race_interblock_none-lock_rtraw` goes from CLEAN to RACE in
the recordings whose lock hand-off windows overlap: the rtraw pair is reported as an SC and the
`dummy` stores inside the critical sections as a DR, both flagged; the DR is ordered by the lock in
every schedule. Where block 1's exit closes the unlock window before block 0's winning CAS (c58,
X4), the certain clock accepts the hand-off and the program stays CLEAN."* For X2's sweep: the
Race (sound) verdict of this program depends on the node the sweep lands on.

## 5. The three verdicts, with the record-level evidence

| | kernel, run | acquisition (winning CAS) | hand-off (unlock window → next lock RMW) | read | write | verdict | class | `a2_uncertain` |
|---|---|---|---|---|---|---|---|---|
| **recorded** | ScoR, c62 run 1 (schedule B, 100 runs) | b1 @0; b0 @8 (5th attempt) | b1 unlock @7[..9) → b0 CAS @8: overlap, accepted | 0x140 @3 | 0x340 @13 | **Latent** | SC (`latent-sc`) | — (no instance) |
| **recorded** | ScoR, c58 run 1 (schedule A, 49 runs) | b1 @0; b0 @9 (5th) | b1 unlock @7[..8) → b0 CAS @9: no overlap | 0x140 @3 | 0x340 @13 | **Latent** | SC (`latent-sc`) | — |
| **forced** | forced, c58 run 1 (all 30) | b0 @1; b1 @14 | b0 unlock @7[..9) → b1 CAS @14: no overlap | 0x1e0 @15 | 0x400 @9 | **Strong conflict** (RAW) | SC (`sc`) | 0 / 1 |
| **certain** | ScoR, c62 run 1 (20 recordings) | b1 @0; b0 @8 | @7[..9) → @8: overlap, **refused** | 0x140 @3 | 0x340 @13 | **Strong conflict** (WAR) | SC (`sc`) | 1 / 1 |
| **certain** | ScoR, c58 run 1 (10 recordings) | b1 @0; b0 @9 | @7[..8) → @9: certain, accepted | 0x140 @3 | 0x340 @13 | **Latent** | SC (`latent-sc`) | — |

## 6. Finding: R3 certifies the racy pair on the A2-inverted trace (scalar-clock mode)

On schedule C (c58: vector-clock run 3, scalar-clock runs 20 and 38) the lock word's records are
…b0 CAS 0x230@6 (wins), b1 unlock 0x1b0@7, b0 unlock 0x330@11. The trace's atomic dependency edges
are therefore `0xb0→0x230, 0x230→0x230, 0x230→0x1b0, 0x1b0→0x330`. Schedules A/B have
`0x1b0→0x230` and `0x230→0x330` instead. R3 (`HBGraph.chain`) starts at the read's release point
0x1b0 and hops `0x1b0→0x330`, landing exactly on the write's acquire point from the trace (its
PO-previous RMW, block 0's own unlock 0x330). T12's landing rule (`_past_release`, non-CAS branch)
should decline a landing on a release: it fires when a CAS pc shares the landing RMW's location,
`frozenset((c, acq)) in same_loc`. But `same_loc` holds only the pc pairs of observed edges, and
in trace C no edge joins 0x330 to a CAS pc. The relation is not transitive (0x330 ~ 0x1b0 ~ 0x230),
so the rule does not fire and R3 returns the chain ['0x1b0', '0x330']. Ablation check on the
scalar-clock reading of the traces (offline, `sync_dominance.analyze`):

| trace | gate on (default) | `CUVEIN_R3_PAST_RELEASE=0` |
|---|---|---|
| A (scor-recorded c58 run 1) | `SC`, no chain | ORDERED, chain 0x1b0 → 0x230 → 0x330 |
| B (scor-recorded c62 run 1) | `SC`, no chain | ORDERED, chain 0x1b0 → 0x230 → 0x330 |
| C (scor-scalar-clock c58 run 20) | **ORDERED**, chain 0x1b0 → 0x330 | ORDERED, chain 0x1b0 → 0x330 |

On A and B `_past_release` is what declines the pair. On C its landing check finds no CAS pc
paired with 0x330, so the gate on and off agree.

* **vector-clock mode:** no effect on the verdict. `hb_races` holds the pair (the inversion hid the
  hand-off from HbClock too) and vetoes R3: Strong conflict, flagged.
* **scalar-clock mode:** the pair is **ORDERED**, a missed report, in 2 of 50 real recordings on
  c58. The program still reads RACE, but only through the `dummy` WAW, which R3 cannot order on that
  trace (its chain needs `0x1b0→0x230`). That is a false report on a pair the lock orders.
* **Proposed fix (not implemented; the freeze admits a bug fix with a failing test, Jeffery
  decides):** take the landing rule's "a CAS on acq's location" over the transitive closure of
  `same_loc`, i.e. location classes as connected components. Equivalently, take location identity
  from the records' addresses, which the dump and `hb_rmw_points` already key. Failing test: the
  scalar-clock dump `eval/results/final-rtraw/scor-scalar-clock/c58/run20/kernel_0.json` with its
  dot. Expected `SC`/`sc` for 0x140→0x340; today `ORDERED` with `hb_chain` ['0x1b0', '0x330'].
  It is the A2 exposure of pc-level R3 (`hb_proof.tex` §5's failure mode (a)), reached here through
  a recording rather than the canary.

## 7. Checks

* **HbClock == specification**, **tested** on every vector-clock dump: 195 / 195 (150 recorded,
  30 certain, 15 forced). The checked keys are `hb_races` at the parity key (pc pair, kind, class,
  space, distance, async, count, `a2_uncertain`), `hb_races_sync_only` and `hb_chain` against
  `hb_oracle.analyze(records=True)` under the dump's own policy.
* **Aggregates path == records path** (X0's parity), **tested**: 260 / 260 dumps give the same
  pair verdict and the same other reports under the default (aggregates) and under
  `CUVEIN_PREFER_RECORDS=1`.
* `tv_violation` absent on 260 / 260.
* Acquisition order by winning CAS == order of the critical sections: 260 / 260.
* No green-set run: no detector, collector or test file changed. The installed runtime's green set
  is X0's (job 311899: 312 passed + 2 skipped, gate 55, no-dump 31).

## 8. Commands

```
# recordings: one job per node, the installed runtime (ACCEL_PROF_HOME=/home/fzheng4/AccelProf)
W=/home/fzheng4/AccelProf/.claude/worktrees/wt-x4 sbatch --job-name=x4-rtraw-c58 -w c58 eval/baselines/setup/p_final_rtraw.sh   # 311940
W=... sbatch --job-name=x4-rtraw-c62 -w c62 eval/baselines/setup/p_final_rtraw.sh                                              # 311941
W=... sbatch --job-name=x4-rtraw-c77 -w c77 eval/baselines/setup/p_final_rtraw.sh                                              # 311942
W=... LABELS=scor-scalar-clock sbatch --job-name=x4-rtraw-sc-c58 -w c58 eval/baselines/setup/p_final_rtraw.sh                  # 311944
# inside each job (store /mnt/beegfs/fzheng4/cuvein_traces/final-rtraw, then copied to eval/results/final-rtraw):
final_rtraw.py record --exe ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw --label scor-recorded --runs 50
final_rtraw.py record --exe <same> --label scor-certain --policy certain --runs 10
final_rtraw.py record --src python/testdata/write_after_unlock_other_schedule.cu --label forced-vector-clock --runs 5
final_rtraw.py record --src <same> --label forced-scalar-clock --mode scalar-clock --runs 5
final_rtraw.py record --exe <ScoR> --label scor-scalar-clock --mode scalar-clock --runs 50            # job 311944 only
# each run, in run<k>/ (the env is blib.base_env's plus YOSEMITE_HB_STATS=0 [+ the policy]):
YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=<mode> YOSEMITE_ATOMIC_SCOPE_FILE=<cfg>/atomic_scope.txt YOSEMITE_HB_STATS=0 \
  [YOSEMITE_HB_GATE_POLICY=certain] accelprof -t pc_dependency_analysis -n 1 ./<binary>
# analysis (login node, no GPU)
.env/bin/python eval/baselines/final_rtraw.py analyze eval/results/final-rtraw
.env/bin/python eval/baselines/final_rtraw.py tables  eval/results/final-rtraw
# T16's two rtraw dumps (BeeGFS, from a normal node)
srun -p normal -n 1 -t 5 cp -r /mnt/beegfs/fzheng4/cuvein_traces/{evcand,t12-eval-t12rb}/P5-race_interblock_none-lock_rtraw/{vector-clock,dots,meta.json} <dest>
```

## 9. Files

* `eval/baselines/final_rtraw.py` (record / analyze / tables), `eval/baselines/setup/p_final_rtraw.sh`.
* `eval/results/final-rtraw/<label>/<node>/`: `node.json` (GPU, CPU, CUDA, runtime hashes, binary
  hash, job), `cfg/` (dot, sidecar), `run<k>/{kernel_0.json, meta.json, accelprof.err}`. The labels
  are `scor-recorded` (3 × 50), `scor-certain` (3 × 10), `forced-vector-clock` and
  `forced-scalar-clock` (3 × 5 each), `scor-scalar-clock` (c58 × 50). The same dumps are on BeeGFS
  under `cuvein_traces/final-rtraw/`.
* `eval/results/final-rtraw/runs.csv`, `runs.json` (one row per run: order, windows, the pair's
  verdict on both paths, HbClock == oracle, the certain replay), `runs_summary.md` (generated tables
  and every distinct schedule).
* `eval/results/final-rtraw/t16-dumps/{evcand,t12-eval-t12rb}/`: the two dumps T16's rtraw claim
  rests on (§4).

## 10. What remains unverified

* **That block 0 can never win on this hardware.** Only that it did not in 230 ScoR recordings on
  three nodes with one runtime build. T15/T18 showed that the collector build moves the window
  schedule, and nothing here rules out a build or node that moves the acquisition order.
* **Why c58 lands in schedule A and c62/c77 in B.** The three nodes differ in CPU model (EPYC
  9115 / 8124P / 7302P) and c77 in driver (580.95.05). The schedule is per node and stable (50 / 50
  or 49 / 50), but its cause is not isolated. Host-side timing of the record drain is a candidate;
  it is untested.
* **The racy order's verdict on the real ScoR binary** is shown through the forced kernel: the same
  source plus an unfenced flag, different pcs. That the flag is gate-neutral (rel = acq = 0) rests
  on the instance gate's fence inventory and on `test_hb_substitutions`, not on a proof here.
* **The certain clock's soundness rests on A2w** (an RMW has taken effect by its thread's next
  record), which is not measured (D15). The Strong-conflict reports of the certain runs are sound
  under it. The `dummy` DR shows they are not complete.
* **The R3 hole of §6** is shown on 3 recordings (1 vector-clock, 2 scalar-clock). How often
  `same_loc`'s missing transitivity certifies a pair elsewhere in the corpus is not measured: that
  needs the fix and a re-score.
* The 1 / 150 (vector-clock) and 2 / 50 (scalar-clock) rates of schedule C on c58 are counts, not
  rates with confidence intervals; nothing is claimed beyond "occurs".

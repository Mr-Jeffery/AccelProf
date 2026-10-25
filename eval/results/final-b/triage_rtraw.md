# P5-race_interblock_none-lock_rtraw: X1 CLEAN, X1b RACE (triage, 2026-10-24)

The coordinating session's triage of the CLEAN → RACE change in `eval/FINAL_SWEEP_B.md` §9. Paths
without a directory are under `eval/results/final-b/`.

**Result.** X1b's RACE is a false report. Its only race report is the WAW on `dummy` between the two
critical sections (pcs 0x170 / 0x2f0, lines 37 and 28), which the fenced lock orders in every
schedule. The labelled race, the rtraw pair, is a strong conflict (SC) in both runs, not a data race.
The change comes from the recording: every X1b recording of the program is A2-inverted, which loses the
lock hand-off.

## The program

Two blocks of one thread (`ScoR/microbenchmarks/src/race_interblock_none-lock_rtraw.cu`). Each block
runs: lock (`atomicCAS` spin), `__threadfence()`, `dummy = data[0]`, `__threadfence()`, unlock
(`atomicExch`). Block 0 then writes `data[0] = 1` after its unlock (line 31).

- **The labelled race (the rtraw pair):** block 0's `data[0] = 1` (pc 0x340) against block 1's read of
  `data[0]` (pc 0x140, line 37).
  - `data` is `volatile`, so both lower to `.STRONG.SYS`. The pair is morally strong: an unordered
    strong conflict, not a data race under PTX (FINAL_RTRAW.md §0, finding 2).
  - Block 1 acquired the lock first in the 4 recordings whose kernel JSON is kept (one per mode in each
    run), as in all 230 of X4's. In that order the pair is also ordered in the execution: block 1's
    read, its unlock, block 0's CAS, block 0's write.
- **The reported pair:** the `dummy` stores (plain `STG.E`, pcs 0x170 block 1 / 0x2f0 block 0). Both sit
  inside the critical sections, between `MEMBAR.SC.GPU` after the winning CAS and `MEMBAR.SC.GPU` before
  the unlock. The lock orders them in either acquisition order.

## What the recordings show

The lock word's coherence profile is the recorded order of the RMWs on `lock`, per thread (tid 1024 is
block 1, tid 0 is block 0). The dependency edges are from the kernel JSON's `edges`
(`current_pc <- ancient_pc`). Read from the stores `final-2026-10` and `final-2026-11` (job on `normal`,
`checks/rt_edges2.py`).

| | X1 | X1b |
|---|---|---|
| node, runtime | c62 (EPYC 8124P, driver 580.82.07), 4094187 | c79 (EPYC 7302P, driver 615.71.09), f551ca0 |
| recordings | 6 (3 per mode), all `events=15` | 6 (3 per mode), all `events=14` |
| lock word, recorded order | b1 CAS (wins); b0 CAS x4 (fail); b1 unlock; b0 CAS (wins, 5th try); b0 unlock | b1 CAS (wins); b0 CAS x4, **the 4th wins**; b1 unlock; b0 unlock |
| lock word edges | 0x230 <- 0x1b0 (**the hand-off**), 0x330 <- 0x230 | 0x330 <- 0x1b0; **no hand-off edge** |
| `dummy` WAW 0x170 / 0x2f0 | ORDERED | RACE (vector-clock: `structural` DR, `a2_uncertain`) |
| rtraw pair 0x140 / 0x340 | SC (`latent-sc` in vector-clock, `sc` in scalar-clock) | SC (vector-clock: `a2_uncertain`) |
| verdict, both modes | CLEAN | RACE (1), the `dummy` WAW |

In X1b, block 0's winning CAS is recorded before block 1's unlock, the write it read 0 from. That is
the A2 inversion: FINAL_RTRAW.md's schedule C. The lost hand-off leaves the two critical sections
unordered, so the `dummy` WAW is reported. X4 (FINAL_RTRAW.md §2) saw schedule C only on c58: 1 of 50
vector-clock and 2 of 50 scalar-clock recordings. Here it is every recording on c79.

The 6 X1b rows all report the same pair. The store keeps only the last recording's kernel JSON, so the
edges above are read from one recording per mode. The other 4 are inferred: each reports the `dummy`
WAW, which happens only when the hand-off is lost, and each has 14 events.

## Not T23, not the verdict code

Job 320161 (`checks/rtt23-320161.log`) analysed both recordings with X1b's verdict code, R3's location
closure off and on. X1's recording is CLEAN both ways and X1b's is RACE both ways. In scalar-clock
mode, T23's closure moves only the rtraw pair, from ORDERED to SC. That ORDERED was FINAL_RTRAW.md §6's
R3 hole on schedule C, which T23 fixed. The closure does not touch the `dummy` pair.

## Not established

Why c79 inverts in every recording. It differs from X1's c62 in CPU, driver and runtime build. c79 is
the only node with driver 615.71.09. c77, also an EPYC 7302P, gave schedule B in 50 of 50 in X4 (driver
580.95.05, the X4 runtime). Re-recording the program a few times on c79 and on c62 with the f551ca0
runtime would tell node from runtime (two GPU nodes for a few minutes, not run).

## For the scoring

- X1b's RACE matches ScoR's RACE label, so X1b counts it as a detection, one in each mode (P5 RACE /
  CLEAN: 5 / 28 vector-clock and 3 / 30 scalar-clock, against X1's 4 / 29 and 2 / 31).
- But the reported pair does not race, and the labelled pair is an SC in both runs. Scored by pair, X1b
  has a false positive here and X1 a CLEAN; neither reports the rtraw pair as a data race.
- In vector-clock mode both X1b reports carry `a2_uncertain`. An operating point that drops flagged
  reports reads CLEAN, as X1 did. Scalar-clock rows carry no such flag.
- Which counting to use is Jeffery's call.

# Paper numbers that change under the per-binary unit (X10, 2026-11-03)

Read from `cuRacePaper` main at 55c7c14; nothing in the paper was edited. Sources: `eval/BASELINES_SUMMARY.md` §1
(per binary) and `eval/PER_BINARY_TABLES.md` §1 (collector-only mode, C4's CSV). The paper's aggregate is
Indigo3 + Indigo 1.3 + ECL + ScoR applications + cuHadron in scope. Indigo 1.3 is already per code (= per binary)
in the paper; the cuHadron, ECL and HeCBench rows are one run per binary and do not change, except
SuperCollider's cuHadron cell, which moves to the in-scope denominator.

## Table 4 (`tables/coverage.tex`, tab:eval-accuracy)

| where | old | new |
|---|---|---|
| :6 caption, programs | "Indigo3: 100 codes × 2 builds × 2 inputs; ScoR applications: 7 codes × 4 inputs; cuHadron: 25 codes × 2 builds" | count binaries: "Indigo3: 200 binaries (100 codes × 2 atomic builds), 2 inputs each; ScoR applications: 14 binaries (7 codes × racy / race-free), 2 inputs each; cuHadron: 50 binaries (25 codes × racy / fixed)"; a binary is reported if any of its runs reports |
| :6 caption | "cuHadron counts the 20 per-kernel inputs, except for SuperCollider (all 34)" | "cuHadron counts the 20 per-kernel binaries for every tool" |
| :11 header | "Program-inputs" | "Binaries" |
| :13 Indigo3 programs / labels | 400; 200 / 200 / 0 | 200; 100 / 100 / 0 |
| :13 Indigo3, cuRace VC / SC / CO | 200/200, 0/200 (each) | 100/100, 0/100 (each) |
| :13 Indigo3, racecheck | 4/200, 0/200 | 4/100, 0/100 |
| :13 Indigo3, iGUARD | 196/200, 100/200 | **100/100, 52/100** |
| :17 ScoR apps programs / labels | 28; 14 / 14 / 0 | 14; 7 / 7 / 0 |
| :17 ScoR apps, cuRace VC / SC | 14/14, 2/14 | 7/7, 1/7 |
| :17 ScoR apps, cuRace CO | 14/14, 6/14 | 7/7, 3/7 |
| :17 ScoR apps, racecheck | 0/13, 0/14; 1 TO | 0/6, 0/7; 1 TO |
| :17 ScoR apps, iGUARD | 12/14, 7/14 | 7/7, 4/7 |
| :18 cuHadron, SuperCollider | 9/13, 0/21 | **5/6, 0/14** (misses `interwave/global_writewrite_race`) |
| :21 aggregate programs / labels | 1,098; 486 / 468 / 144 | 884; 379 / 361 / 144 (200 + 590 + 60 + 14 + 20) |
| :21 aggregate, cuRace VC / SC | 486/486, 18/468 | 379/379, 17/361 |
| :21 aggregate, cuRace CO | 486/486, 54/468 | 379/379, 51/361 |
| :21 aggregate, racecheck | 48/485, 0/468; 1 TO | 48/378, 0/361; 1 TO |
| :21 aggregate, iGUARD | 467/486, 267/468 | 366/379, 216/361 |
| :21 aggregate, HiRace | 266/266, 0/180 | unchanged |
| :21 aggregate, SuperCollider | 51/58, 0/65 | 47/51, 0/58 |

## Prose

| where | old | new |
|---|---|---|
| `introduction.tex:98-99` | "all 486 labelled races, with false positives on 18 of 468 race-free programs" | "all 379 labelled racy binaries, with false positives on 17 of 361 race-free binaries" |
| `conclusion.tex:9` | "all 486 labelled races, with false positives on 18 of 468 race-free programs" | same replacement; "4,725 program-inputs" stays (it counts runs); the same suites count 971 binaries (4,725 runs) |
| `evaluation.tex:38` | "all 486 labelled races and 18 false positives among 468 race-free programs" | "all 379 racy binaries and 17 false positives among 361 race-free binaries" |
| `evaluation.tex:38` | "\Comode reports the same 486 races and 54 false positives, 32 of them in Indigo 1.3 … the 36 false positives" | "the same 379 and 51 false positives, 32 of them in Indigo 1.3 … the 34 false positives" (51 − 17) |
| `evaluation.tex:43` (comment) | 54 = 32 + 16 + 6; 486 = 200 + 266 + 14 + 6; 468 = 200 + 180 + 60 + 14 + 14 | 51 = 32 + 16 + 3; 379 = 100 + 266 + 7 + 6; 361 = 100 + 180 + 60 + 7 + 14 |
| `evaluation.tex:47` | "racecheck detects 4 of the 200 Indigo3 races" | "4 of the 100 racy Indigo3 binaries" |
| `evaluation.tex:47` | "iGUARD detects 467 of the 486 pre-registered races but reports races in 267 of the 468 race-free programs, 100 of 200 in Indigo3" | "366 of the 379 … in 216 of the 361 race-free binaries, 52 of 100 in Indigo3"; the 52 include 8 BFS codes reported only on their default build (§3 of `PER_BINARY_TABLES.md`) |
| `evaluation.tex:47` | "On cuHadron it misses the inter-wave write-write test. It also reports four cuHadron races that \ourwork does not, three involving host code and one between two kernels" | the first sentence stands; the second describes out-of-scope binaries, which the in-scope cell no longer counts — keep it as a sentence about the out-of-scope rows or move it to Appendix E |
| `evaluation.tex:54` | "The 18 false positives … The two ScoR applications are the two inputs of `reduction`" | "The 17 false positives … The ScoR application is `reduction` (on both inputs)" |
| `discussion.tex:15`, `appendix_eval.tex:42` | "196 of 200 in Indigo3" | per binary "96 of 100" if every racy Indigo3 code with a shared-memory race is one of racecheck's four — **not verified** (`shared_mem` is 0 for every Indigo3 manifest row) |
| `appendix_eval.tex:306` | "18 of 468 race-free programs rather than 54" | "17 of 361 race-free binaries rather than 51" |
| `appendix_eval.tex` Table tab:eval-accuracy-union and tab:eval-countings | Indigo3 / ScoR / aggregate cells per run | need the same fold under the union counting; **not computed here** (the union counting is not in `make_tables.py`) |
| `appendix_eval.tex` tab:eval-indigo-pi | per program-input | unchanged (it is the per-run appendix) |

## Per-binary statements the paper can add

- Indigo3: every tool gives the same verdict on both atomic builds of every code except iGUARD, on 8 race-free BFS
  codes (default build only, `Missing blkfence`).
- Indigo 1.3: every racy binary races on some input (oracle, all seven inputs covered); cuRace and HiRace report
  all 266, so the per-binary count needs no oracle argument.

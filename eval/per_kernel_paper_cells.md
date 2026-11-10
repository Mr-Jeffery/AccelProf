# Paper cells that would change under the per-kernel unit (X13, 2026-11-10; read only)

Read from `cuRacePaper` main at `df8100e` (local copy `/home/jeffery/Documents/cuRacePaper`); nothing in the paper was edited. Table 4 (`tables/coverage.tex`, `tab:eval-accuracy`) is generated from `numbers/table-accuracy.csv` and `numbers/corpus.csv` through `\nv{...}` macros, so each cell below is a key; its present value is the paper's per-program-input / Indigo-1.3-per-code count, reproduced exactly by X13's gate (`--unit run`, `eval/results/per-kernel/gate_run.md`). New values: `eval/results/per-kernel/table4_kernel_cells.csv` (HeCBench = SuperCollider's 10 applications on the native binaries, labels from 6a8c46c4, tridiagonal labels the agent's proposal adopted by Jeffery without review).

## Table 4 itself
- `tables/coverage.tex:6` caption: "the third column gives the programs, then the labels" - the unit becomes the kernel (one `__global__` function; launches fold into it); add the fold rule and that cuHadron's "50 (34 run, 20 per-kernel)" counts binaries whose kernels are 38 (34 runnable) / 20 (in scope).
- `tables/coverage.tex:11` header "Programs / labels" -> "Kernels / labels".
- Cell keys: `numbers/table-accuracy.csv` lines below (the macro rows in `tables/coverage.tex:15-35` read them).

## `numbers/table-accuracy.csv` (old -> new)
| table-accuracy.csv | key | old | new |
|---|---|---|---|
| :3 | `accuracy.indigo3.iguard.racy-reported` | 196 | 100 |
| :6 | `accuracy.indigo3.collector-only.racy-reported` | 200 | 100 |
| :7 | `accuracy.indigo3.scalar-clock.racy-reported` | 200 | 100 |
| :8 | `accuracy.indigo3.vector-clock.racy-reported` | 200 | 100 |
| :10 | `accuracy.indigo3.iguard.race-free-reported` | 100 | 52 |
| :45 | `accuracy.scor-apps.racecheck.racy-finished` | 13 | 8 |
| :46 | `accuracy.scor-apps.racecheck.racy-timeout` | 1 | 3 |
| :47 | `accuracy.scor-apps.iguard.racy-reported` | 12 | 11 |
| :50 | `accuracy.scor-apps.collector-only.racy-reported` | 14 | 11 |
| :51 | `accuracy.scor-apps.scalar-clock.racy-reported` | 14 | 11 |
| :52 | `accuracy.scor-apps.vector-clock.racy-reported` | 14 | 11 |
| :54 | `accuracy.scor-apps.iguard.race-free-reported` | 7 | 4 |
| :58 | `accuracy.scor-apps.scalar-clock.race-free-reported` | 2 | 1 |
| :59 | `accuracy.scor-apps.vector-clock.race-free-reported` | 2 | 1 |
| :74 | `accuracy.hecbench-sc10.racecheck.racy-reported` | 3 | 4 |
| :75 | `accuracy.hecbench-sc10.iguard.racy-reported` | 2 | 9 |
| :77 | `accuracy.hecbench-sc10.supercollider.racy-reported` | 5 | 15 |
| :78 | `accuracy.hecbench-sc10.collector-only.racy-reported` | 5 | 15 |
| :79 | `accuracy.hecbench-sc10.scalar-clock.racy-reported` | 4 | 6 |
| :80 | `accuracy.hecbench-sc10.scalar-clock.racy-finished` | 4 | 6 |
| :81 | `accuracy.hecbench-sc10.scalar-clock.racy-timeout` | 1 | 9 |
| :82 | `accuracy.hecbench-sc10.vector-clock.racy-reported` | 3 | 4 |
| :83 | `accuracy.hecbench-sc10.vector-clock.racy-finished` | 3 | 4 |
| :84 | `accuracy.hecbench-sc10.vector-clock.racy-timeout` | 2 | 13 |
| :86 | `accuracy.hecbench-sc10.iguard.race-free-reported` | 3 | 6 |
| :89 | `accuracy.hecbench-sc10.collector-only.race-free-reported` | 1 | 6 |
| :90 | `accuracy.hecbench-sc10.scalar-clock.race-free-reported` | 0 | 2 |
| :93 | `accuracy.all-preregistered.racecheck.racy-finished` | 485 | 380 |
| :94 | `accuracy.all-preregistered.racecheck.racy-timeout` | 1 | 3 |
| :95 | `accuracy.all-preregistered.iguard.racy-reported` | 467 | 370 |
| :98 | `accuracy.all-preregistered.supercollider.racy-run` | 58 | 60 |
| :99 | `accuracy.all-preregistered.collector-only.racy-reported` | 486 | 383 |
| :100 | `accuracy.all-preregistered.scalar-clock.racy-reported` | 486 | 383 |
| :101 | `accuracy.all-preregistered.vector-clock.racy-reported` | 486 | 383 |
| :103 | `accuracy.all-preregistered.iguard.race-free-reported` | 219 | 168 |
| :106 | `accuracy.all-preregistered.supercollider.race-free-run` | 65 | 67 |
| :108 | `accuracy.all-preregistered.scalar-clock.race-free-reported` | 2 | 1 |
| :109 | `accuracy.all-preregistered.vector-clock.race-free-reported` | 2 | 1 |


Keys not listed are unchanged per kernel. Cells whose display changes without a key change: the HeCBench cells now carry kernel TO counts (`scalar-clock` 6/6 + 9 TO, `vector-clock` 4/4 + 13 TO; today "4/4, 1 TO" and "3/3, 2 TO"); `accuracy.hecbench-sc10.vector-clock.racy-finished/-timeout` therefore 4 and 13; no TO key exists for SuperCollider/iGUARD/collector-only on HeCBench (none changes).
Per-kernel cuHadron cells for SuperCollider use all 34 runnable binaries (38 kernels): `accuracy.cuhadron.supercollider.racy-reported` 9 is unchanged but its denominator `corpus.cuhadron.runnable.racy` becomes 15 and `...race-free` 23 (see below); `accuracy.cuhadron.supercollider.race-free-reported` stays 0.

## `numbers/corpus.csv`
| numbers/corpus.csv key | old | new (per kernel) |
|---|---|---|
| `corpus.indigo3.programs` | 400 | 400 kernels (200 binaries x 2) |
| `corpus.indigo3.racy` / `.race-free` / `.unlabelled` | 200 / 200 / 0 | 100 / 300 / 0 |
| `corpus.indigo13.codes` / `.racy` / `.race-free` / `.unlabelled` | 590 / 266 / 180 / 144 | 590 kernels / 266 / 180 / 144 (one kernel per code: unchanged) |
| `corpus.indigo13-sc99.*` | 99 / 45 / 44 / 10 | unchanged (one kernel per code) |
| `corpus.scor-apps.programs` | 28 | 24 kernels (14 binaries; `reduction` counts 1 launched kernel each) |
| `corpus.scor-apps.racy` / `.race-free` | 14 / 14 | 11 / 13 |
| `corpus.cuhadron.in-scope` (programs) / `.in-scope.racy` / `.in-scope.race-free` | 20 / 6 / 14 | 20 kernels / 6 / 14 (unchanged: single-kernel binaries) |
| `corpus.cuhadron.runnable` / `.runnable.racy` / `.runnable.race-free` | 34 / 13 / 21 | 38 kernels / 15 / 23 (the four `interkernel/*` binaries have two kernels each; labels proposed) |
| `corpus.cuhadron.racy` / `.race-free` (50 programs) | 21 / 29 | missing (the 16 sm_90 binaries have no cubin, their kernels are unknown) |
| `corpus.hecbench-sc10.programs` | 10 | 49 kernels (10 binaries) |
| `corpus.hecbench-sc10.racy` / `.race-free` | 5 / 5 | 15 / 34 |
| `corpus.all-preregistered.programs` | 1,038 | 1,034 kernels (400 + 590 + 24 + 20) |
| `corpus.all-preregistered.racy` / `.race-free` / `.unlabelled` | 486 / 408 / 144 | 383 / 507 / 144 |
| `corpus.program-inputs` (`introduction.tex:169`, `evaluation.tex:7`, `conclusion.tex:11`) | program-inputs | the unit word becomes kernels; the count is not recomputed here (the paper's value is a sum over program-inputs that includes the 4,130 Indigo 1.3 runs) - missing |

## Prose that reads these keys (file:line; the sentence changes only through the macro values unless a note says so)
- appendix_eval.tex:11: corpus.cuhadron.host-copy-codes, corpus.cuhadron.in-scope, corpus.cuhadron.in-scope.race-free, corpus.cuhadron.in-scope.racy, corpus.cuhadron.multi-stream-codes, corpus.cuhadron.needs-sm90, corpus.cuhadron.out-of-scope-codes, corpus.cuhadron.out-of-scope-word, corpus.cuhadron.runnable, corpus.cuhadron.runnable.race-free, corpus.cuhadron.runnable.racy, corpus.cuhadron.unified-memory-codes, corpus.hecbench-sc10.differing-binaries-word, corpus.hecbench-sc10.identical-binaries-word, corpus.hecbench-sc10.identical-binaries-word-lower, corpus.hecbench-sc10.label-changed-word, corpus.hecbench-sc10.programs, corpus.hecbench-sc10.programs-word, corpus.hecbench-sc10.race-free, corpus.hecbench-sc10.racy, corpus.hecbench.unlabelled, corpus.scor-apps.applications, corpus.scor-litmus.labelled-kernels
- appendix_eval.tex:13: corpus.baseline-detectors-word, corpus.hecbench-sc10.programs, corpus.hecbench.unlabelled, corpus.indigo13-sc99.codes, corpus.indigo13.codes
- appendix_eval.tex:17: corpus.hecbench-sc10.differing-binaries-word
- appendix_eval.tex:23: corpus.hecbench-sc10.atomiccas.commits-between-revisions
- appendix_eval.tex:24: corpus.hecbench-sc10.dxtc2.commits-between-revisions
- appendix_eval.tex:25: corpus.hecbench-sc10.knn.commits-between-revisions
- appendix_eval.tex:26: corpus.hecbench-sc10.tridiagonal.commits-between-revisions
- appendix_eval.tex:27: corpus.hecbench-sc10.expdist.commits-between-revisions
- appendix_eval.tex:28: corpus.hecbench-sc10.mr.commits-between-revisions
- appendix_eval.tex:54: corpus.indigo3.race-free, corpus.indigo3.racy
- appendix_eval.tex:55: corpus.indigo13.race-free, corpus.indigo13.racy
- appendix_eval.tex:56: corpus.scor-apps.race-free, corpus.scor-apps.racy
- appendix_eval.tex:57: corpus.scor-litmus.race-free, corpus.scor-litmus.racy
- appendix_eval.tex:58: corpus.cuhadron.in-scope.race-free, corpus.cuhadron.in-scope.racy, corpus.cuhadron.runnable.race-free, corpus.cuhadron.runnable.racy
- appendix_eval.tex:65: corpus.indigo13.racy, corpus.indigo3.racy, corpus.scor-litmus.racy
- appendix_eval.tex:67: corpus.indigo3.race-free, corpus.scor-apps.race-free, corpus.scor-litmus.racy
- appendix_eval.tex:78: accuracy.indigo3.collector-only.racy-reported, accuracy.indigo3.scalar-clock.racy-reported, accuracy.indigo3.vector-clock.racy-reported, corpus.indigo3.race-free, corpus.indigo3.racy
- appendix_eval.tex:79: corpus.indigo13.race-free, corpus.indigo13.racy
- appendix_eval.tex:80: accuracy.scor-apps.collector-only.racy-reported, accuracy.scor-apps.scalar-clock.race-free-reported, accuracy.scor-apps.scalar-clock.racy-reported, accuracy.scor-apps.vector-clock.race-free-reported, accuracy.scor-apps.vector-clock.racy-reported, corpus.scor-apps.race-free, corpus.scor-apps.racy
- appendix_eval.tex:81: corpus.scor-litmus.race-free, corpus.scor-litmus.racy
- appendix_eval.tex:82: corpus.cuhadron.in-scope.race-free, corpus.cuhadron.in-scope.racy
- appendix_eval.tex:83: accuracy.hecbench-sc10.collector-only.race-free-reported, accuracy.hecbench-sc10.collector-only.racy-reported, accuracy.hecbench-sc10.scalar-clock.race-free-reported, accuracy.hecbench-sc10.scalar-clock.racy-finished, accuracy.hecbench-sc10.scalar-clock.racy-reported, accuracy.hecbench-sc10.scalar-clock.racy-timeout, accuracy.hecbench-sc10.vector-clock.racy-finished, accuracy.hecbench-sc10.vector-clock.racy-reported, accuracy.hecbench-sc10.vector-clock.racy-timeout, corpus.hecbench-sc10.race-free, corpus.hecbench-sc10.racy
- appendix_eval.tex:88: corpus.scor-litmus.race-free, corpus.scor-litmus.racy, corpus.scor-litmus.scor-racy
- appendix_eval.tex:92: corpus.scor-litmus.kernels
- appendix_eval.tex:138: corpus.indigo13.hirace-graphs-word, corpus.indigo13.inputs-per-code-word
- appendix_eval.tex:142: corpus.indigo13-sc99.codes, corpus.indigo13.codes, corpus.indigo13.inputs-per-code-word
- appendix_eval.tex:149: corpus.indigo13.race-free-rows, corpus.indigo13.racy-rows, corpus.indigo13.runs-per-tool, corpus.indigo13.unlabelled-rows
- appendix_eval.tex:150: corpus.indigo13-sc99.race-free-rows, corpus.indigo13-sc99.racy-rows, corpus.indigo13-sc99.runs-per-tool, corpus.indigo13-sc99.unlabelled-rows
- appendix_eval.tex:155: corpus.indigo13.inputs-per-code-word, corpus.indigo13.large-graphs-word, corpus.indigo13.race-free-rows, corpus.indigo13.racy-rows
- appendix_eval.tex:167: corpus.indigo13.inputs-per-code-word, corpus.indigo13.racy
- appendix_eval.tex:170: corpus.indigo13-sc99.codes, corpus.indigo13-sc99.racy-rows, corpus.indigo13.inputs-per-code-word
- appendix_eval.tex:247: corpus.hecbench-sc10.identical-binaries-word-lower, corpus.hecbench-sc10.label-changed-word
- appendix_eval.tex:252: corpus.cuhadron.host-copy-codes-word, corpus.cuhadron.host-copy-inputs-word, corpus.cuhadron.multi-stream-codes-word, corpus.cuhadron.out-of-scope, corpus.cuhadron.runnable, corpus.cuhadron.unified-memory-codes-word
- appendix_eval.tex:266: accuracy.indigo3.iguard.race-free-reported, corpus.indigo13.race-free, corpus.indigo13.race-free-rows, corpus.indigo3.race-free, corpus.scor-litmus.labelled-kernels, corpus.scor-litmus.scor-racy
- conclusion.tex:11: accuracy.all-preregistered.collector-only.racy-reported, accuracy.all-preregistered.scalar-clock.race-free-reported, accuracy.all-preregistered.scalar-clock.racy-reported, corpus.all-preregistered.race-free, corpus.all-preregistered.racy, corpus.program-inputs, corpus.suites-word
- discussion.tex:92: corpus.all-preregistered.racy, corpus.indigo13.racy, corpus.indigo3.racy, corpus.scor-litmus.racy
- discussion.tex:109: corpus.hecbench.applications
- discussion.tex:110: corpus.hecbench-sc10.programs-word, corpus.hecbench.unlabelled
- evaluation.tex:7: corpus.baseline-detectors-word, corpus.program-inputs, corpus.suites-word
- evaluation.tex:15: corpus.cuhadron.in-scope, corpus.cuhadron.in-scope.race-free, corpus.cuhadron.in-scope.racy, corpus.cuhadron.runnable, corpus.hecbench-sc10.programs, corpus.hecbench-sc10.race-free, corpus.hecbench-sc10.racy, corpus.hecbench.unlabelled, corpus.indigo13-sc99.codes, corpus.indigo13-sc99.runs-per-tool, corpus.indigo13.codes, corpus.indigo13.inputs-per-code, corpus.indigo13.inputs-per-code-word, corpus.indigo13.runs-per-tool, corpus.scor-apps.applications, corpus.scor-litmus.labelled-kernels
- evaluation.tex:20: corpus.cuhadron.sc-binaries-compared, corpus.hecbench-sc10.programs, corpus.hecbench.unlabelled, corpus.indigo13-sc99.codes, corpus.indigo13.inputs-per-code-word
- evaluation.tex:48: accuracy.all-preregistered.collector-only.racy-reported, accuracy.all-preregistered.scalar-clock.race-free-reported, accuracy.all-preregistered.scalar-clock.racy-reported, corpus.all-preregistered.race-free, corpus.all-preregistered.racy, corpus.indigo13.inputs-per-code-word, corpus.indigo13.racy-rows
- evaluation.tex:67: accuracy.all-preregistered.iguard.race-free-reported, accuracy.all-preregistered.iguard.racy-reported, accuracy.indigo3.iguard.race-free-reported, corpus.all-preregistered.race-free, corpus.all-preregistered.racy, corpus.indigo13-sc99.codes, corpus.indigo13-sc99.racy, corpus.indigo13.inputs-per-code-word, corpus.indigo13.race-free, corpus.indigo13.racy, corpus.indigo3.race-free, corpus.indigo3.racy
- evaluation.tex:74: corpus.scor-litmus.racy
- evaluation.tex:79: corpus.hecbench-sc10.programs-word, corpus.hecbench-sc10.racy-word, corpus.hecbench.unlabelled
- evaluation.tex:97: corpus.hecbench-sc10.programs-word, corpus.hecbench.unlabelled
- introduction.tex:169: corpus.program-inputs
- introduction.tex:170: corpus.suites-word
- introduction.tex:172: accuracy.all-preregistered.collector-only.racy-reported
- introduction.tex:173: corpus.all-preregistered.racy
- introduction.tex:176: corpus.all-preregistered.race-free
- introduction.tex:178: accuracy.all-preregistered.scalar-clock.racy-reported
- introduction.tex:180: accuracy.all-preregistered.scalar-clock.race-free-reported
- introduction.tex:217: corpus.baseline-detectors-word, corpus.suites-word
- main.tex:187: corpus.suites-word
- main.tex:188: accuracy.all-preregistered.collector-only.racy-reported
- main.tex:192: accuracy.all-preregistered.scalar-clock.race-free-reported

Plain-text statements that no macro covers and that would change:
- `evaluation.tex:48`: "\Vclock gives the same ratios as \sclock on every suite but one: ... \texttt{expdist} finishes only with \sclock" - per kernel the two clocks differ on HeCBench only: scalar-clock 6/6 with 9 TO/ERR, vector-clock 4/4 with 13 TO/ERR (the four expdist kernels time out in vector-clock; atomicCAS times out in both).
- `evaluation.tex:74`: "The two false positives are the two inputs of ScoR's reduction" - per kernel the clocks have one false positive kernel (`reduceSinglePass<512u, true>` of `reduction_norace`); 2 -> 1 (`accuracy.all-preregistered.{scalar,vector}-clock.race-free-reported`).
- `main.tex:179-180`: "lowers false positives to just two" -> one (per kernel); `main.tex:201` yanbo's check note "4,665 / 486 / 2 of 408": 486 -> 383, 2 of 408 -> 1 of 507.
- `evaluation.tex:50-63` (comments with 485/486, 40/408, 38 = 32 + 6, 408 = ..., 219 = ...): per kernel 383, 40/507, collector-only 40 = 32 + 8, 507 = 300 + 180 + 13 + 14, iGUARD 168 = 52 + 108 + 4 + 4; comments only.
- Appendix E (`appendix_eval.tex:54-58, 78-83`) per-suite rows read `corpus.*` and `accuracy.*` keys above; `appendix_eval.tex:266` (iGUARD's false-positive rate) reads `accuracy.indigo3.iguard.race-free-reported` (100 -> 52) and `corpus.indigo3.race-free` (200 -> 300).

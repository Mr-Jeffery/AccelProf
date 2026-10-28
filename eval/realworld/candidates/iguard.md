# T21c: iGUARD on the candidates outside shared memory

iGUARD (SOSP'21, commit 3eb5003, NVBit 1.8, sm_89) instruments global memory only. Of the 18 T21c
oracles (`eval/realworld/oracle/*.json`, field `space`), 17 are `shared`. They are out of iGUARD's
scope and were not run. One is `global`: **llmc-new-1**, a cross-block hand-off through global `scratch`
in `layernorm_backward_kernel10`.

Job 320918 (c2, RTX 4060 Ti, driver 615.71.09, CUDA 13.4 runtime), harness
`eval/realworld/harness/t21c_iguard.sh`, runner `eval/baselines/run_iguard.py`, 3 reps on the same
relinked binary cuVein recorded. Results: `eval/results/realworld_t21c/iguard.csv`. Rep 1 log:
`candidates/logs/iguard-llmc-new-1-rep1.txt`.

| rep | verdict | reports | kind | wall (s) | native (s) |
|---|---|---|---|---|---|
| 1 | RACE | 8 | Missing gpufence | 1.72 | 0.88 |
| 2 | RACE | 8 | Missing gpufence | 1.57 | 0.88 |
| 3 | RACE | 8 | Missing gpufence | 1.37 | 0.88 |

All 6 block sizes ran and printed "All results match" under the tool.

The 8 reports are the same 8 `LDG.E.128` loads that cuVein's triage found (`triage/llmc-new-1.md`).
iGUARD names each by SASS offset only, so the lines below come from `nvdisasm -g`:

| SASS offset | line-table line | statement (triage) |
|---|---|---|
| 0x4e60, 0x4ed0, 0x4f00, 0x4f40 | layernorm_backward.cu:1217 | `dbias128` load, L1214 |
| 0x4eb0, 0x4f20, 0x4f50, 0x4f60 | layernorm_backward.cu:1218 | `dweight128` load, L1215 |

iGUARD reports only the racing access, not the earlier store (the `STG.E.128` at 0x4a50/0x4a60,
L1194–L1195). Its kind, "Missing gpufence", is the triage's cause: the only ordering between blocks is
CTA-scope `bar.sync` plus a relaxed `atomicInc` on another address.

**Verdict: DETECTED.** By the T21c rule (a report line within ±2 of an oracle endpoint), 4 of the 8
match, the L1217 group. That is the same count as cuVein's scalar-clock run. The L1218 group is the same race,
3 lines from the oracle's L1215. Both tools report the same instructions, so the line-table
attribution affects them equally.

# T21b: iGUARD on the targets whose race is in global memory

iGUARD (SOSP'21, commit 3eb5003, NVBit 1.8, sm_89) instruments global memory only. Of the 50 T21b
oracles (`eval/realworld/oracle/*.json`, field `space`), 41 are `shared`: out of scope, not run. The 9
`global` ones are amrex-1, cccl-3, cccl-4, cmssw-1, ginkgo-5, llmc-new-1, pytorch-3, pytorch-4, raft-1.
llmc-new-1 was run under T21c (`study/realworld-candidates`, `eval/realworld/candidates/iguard.md`:
DETECTED). amrex-1 was skipped (see below).

Job 321057 (array of 2: buggy on c56, driver 580.105.08; fixed on c2, driver 615.71.09), harness
`eval/realworld/harness/t21b_iguard.sh`, runner `eval/baselines/run_iguard.py`, 3 reps per build, cap
min(max(10x native, 120), 1200) s. Raw rows: `eval/results/realworld/iguard-shard{0,1}_2.csv`. Every
rep of a build gave the same verdict.

iGUARD names a report by its racing access only (one endpoint, as a SASS offset). The lines below come
from `eval/realworld/harness/iguard_map.py` (cubin line table via `nvdisasm -g`). A buggy build is
DETECTED when a report's line is within ±2 of an endpoint of a primary/family/extra oracle pair; a fixed
build is CLEAN-FOR-PAIR when no report is at the pair's lines.

| target | buggy | reports (line) | fixed | cuVein (scalar-clock), buggy / fixed |
|---|---|---|---|---|
| cccl-4 | **DETECTED** | driver_buggy.cu:68, :85 (oracle B, Missing blkfence); 5 more on CUB look-back strong ld/st (strong_load.cuh:100, strong_store.cuh:90, Missing gpufence) | RACE: the 3 look-back reports only, CLEAN-FOR-PAIR | DETECTED / CLEAN-FOR-PAIR |
| cmssw-1 | **DETECTED** | prefixScan.h:172 (primary B), :179 (extra B, load and store) | RACE at fixed L175, L182 (the same accesses, now volatile `STRONG.SYS`): RESIDUAL-AS-EXPECTED | DETECTED / RESIDUAL-AS-EXPECTED (REVIEW item 2) |
| pytorch-3 | **DETECTED** | MultiMarginLoss.cu:125 (primary B, Missing blkfence) | CLEAN | DETECTED / CLEAN-FOR-PAIR |
| pytorch-4 | **DETECTED** | Sorting.cu:86 (primary), :85 (extra), Missing blkfence | CLEAN (cuVein's residual, minIndexFound read vs atomicMin, not reported) | DETECTED / RESIDUAL-AS-EXPECTED |
| cccl-3 | MISSED | none | CLEAN | DETECTED (DR+SC) / RESIDUAL-AS-EXPECTED |
| ginkgo-5 | MISSED | none | CLEAN | DETECTED / CLEAN-FOR-PAIR |
| raft-1 | MISSED | none | CLEAN | DETECTED (DR+SC) / RESIDUAL-AS-EXPECTED |

**Totals (7 targets run): iGUARD 4 DETECTED, 3 MISSED; cuVein 7 DETECTED.** Adding llmc-new-1 (T21c),
iGUARD detects 5 of the 8 global-memory targets it was run on.

The 3 misses are not instrumentation failures: each log shows the oracle's kernel launched and hooked
(cccl-3 `DeviceTopKKernel`, ginkgo-5 `compute_lookup_small/large`, raft-1 `radix_kernel`), and iGUARD
reported nothing for them. Two of the three (cccl-3, raft-1) are atomicAdd-vs-plain/volatile hand-offs;
ginkgo-5 is a lost update on a packed word inside one block. Why iGUARD misses them was not
investigated.

**amrex-1, skipped.** All 6 reps (buggy and fixed) hit the derived 120 s cap (native 0.9–1.3 s).
A rerun at cuVein's 1,200 s cap (job 321060) was cancelled at about 15 min on request. cuVein missed
this target too (m4: vector-clock TIMEOUT, scalar-clock analysis timeout). For the record only, not
scored: in the 120 s it had, the buggy log already held 40 reports, including the oracle's L86 store
and stencil loads L207–L232 (AMReX_MLNodeLap_3D_K.H) and the extra pair's L77 store; the fixed log held
2, neither at an oracle line.

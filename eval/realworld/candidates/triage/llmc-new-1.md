# Triage: llmc-new-1 (T21c step 3)

Pinned commit: karpathy/llm.c `f1e2ace651495b74ae22d45d1723443fd00ecd3a`. Route R1: the repo's own `dev/cuda/layernorm_backward.cu`, kernel 10, with host-only edits (B=1, T=64, timing sweep off; `targets/llmc-new-1/target.sh`).
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/llmc-new-1-buggy.json`). 6 kernel JSONs, all `layernorm_backward_kernel10`: grids 1088/544/272/136/68/68 blocks of 32/64/128/256/512/512 threads (`kernel_0..5.json`; the 1024-thread request runs at 512). `n_race = 8`, `n_sc = 0`. Each of the 8 reports appears in all 6 JSONs.
`recall.csv` matched the 4 reports with the load at L1217 (inside ±2 lines of the oracle read L1214–L1215). `other_reports.csv` holds the 4 with the load at L1218.

## Groups

| # | kernel | pcs (a store / b load) | file:line pair as attributed | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `layernorm_backward_kernel10` | `STG.E.128` 0x4a50 / `LDG.E.128` 0x4e60, 0x4ed0, 0x4f00, 0x4f40 | `common.h:168 < layernorm_backward.cu:1194` / `layernorm_backward.cu:1217` | 4 (matched) | **(a) DR** | `scratch_dbias` partial of block A (L1194) vs the last block's load of it (L1214). Cross-block. The only ordering is CTA-scope `bar.sync` plus a relaxed `atomicInc` on another address. |
| 2 | `layernorm_backward_kernel10` | `STG.E.128` 0x4a60 / `LDG.E.128` 0x4eb0, 0x4f20, 0x4f50, 0x4f60 | `common.h:168 < layernorm_backward.cu:1194` / `layernorm_backward.cu:1218` | 4 (other_reports) | **(a) DR**, same race as group 1 | The `scratch_dweight` half of the same hand-off: store L1195 vs load L1215. |

Class counts: (a) 2 groups (8 reports). They form one race, with one dossier: `eval/realworld/findings/llmc-new-1.md`. (b) 0, (c) 0, (d) 0. Neither group is a same-value WAW.

## Why the 8 reports are one race

The attributed lines are off from the real statements because of how the line table is built, not because the race is somewhere else. The SASS (sm_89, `nvdisasm -g` of the traced binary) settles which array each pc touches:

- **Stores.**
  - 0x4a50: `STG.E.128 [R2.64+0x80], R4`. R4 comes from `LDS.128 [R15.X4]` (`dbias_shared + i`). The address is `scratch + 4*(2*C*blockIdx + i)`. So this is the `scratch_dbias` store, **L1194**.
  - 0x4a60: `STG.E.128 [R12.64+0x80], R8`. R8 comes from `LDS.128` of `dweight_shared`. The address adds `C` (`c[0x0][0x1b0]`). So this is the `scratch_dweight` store, **L1195**.
  - The inline-call-site entry gives L1194 for both stores. Both are `store128` calls (common.h:168) inlined from adjacent lines.
- **Loads.** The 4-way-unrolled `read_block_idx` loop has eight `LDG.E.128`.
  - Four use the base `scratch + 4*offset`: 0x4e60, 0x4ed0, 0x4f00, 0x4f40. These are `dbias128`, **L1214**.
  - Four use the base plus `C`: 0x4eb0, 0x4f20, 0x4f50, 0x4f60. These are `dweight128`, **L1215**.
  - ptxas tagged each load with the line of its first use, L1217 or L1218 (`dbias_accum[k] += dbias128[k]` and the `dweight` line). It did not tag them with the `load128` line.
- **Pairing.** Every report pairs the dbias store with a dbias load, or the dweight store with a dweight load. No cross pairs exist.
  - The 4 reports per group are the 4 unrolled loads.
  - L1218 is 3 lines from L1215, outside the ±2 window. That is why group 2 landed in `other_reports.csv`.
- **Remainder loop.** The loop's remainder copy has loads at 0x5220, 0x5240, 0x5380, 0x53c0, 0x53e0 and 0x53f0. They have no report. Their pcs do not occur in any kernel JSON's `nodes`. That fits the grid sizes: all six grids are multiples of 4, so the remainder never ran. This is not a missed report.

## Reasoning (one race)

- **Accesses.** Block A thread t stores 16 bytes at `scratch_dbias + 4t + 2*C*A` (L1194) and the same at `scratch_dweight` (L1195). This happens after `__syncthreads` L1183 and before `__syncthreads` L1197 (`BAR.SYNC` 0x4890, 0x4a90).
- **Hand-off.** Thread 0 then does `ATOMG.E.INC.STRONG.GPU` on `scratch[0]` (0x4af0, L1201) and stores the result to shared `tmp_flag` (0x4b00). After `BAR.SYNC` 0x4b20 (L1203), the block that read `gridDim.x-1` loads every block's partials (0x4e60…).
- **Concrete pair.** In the 68-block launch (`kernel_4.json`), take block 0, thread 0: it stores `scratch_dbias[0..3]`. The last block, say block 67, thread 0, loads the same 16 bytes at `read_block_idx = 0`.
- **Trace evidence.** The trace edges confirm the distance. For 0x4e60 ← 0x4a50: `intra_grid 25600`, with `intra_thread 1600` (the last block reading its own partials). For 0x4eb0 ← 0x4a60: the same.
- **Why nothing orders them.** The kernel's SASS contains no `MEMBAR` at all (grep count 0). Between the store and the load there are only `BAR.SYNC`, `ATOMG.E.INC.STRONG.GPU` and the `STS`/`LDS` of the flag. The kernel's three `WARPSYNC` (0x0f50 and 0x4850 with mask 0xffffffff, 0x5d20 with a register mask) order only lanes of one warp, and they lie elsewhere.
  - `bar.sync` synchronizes only threads of one CTA.
  - The atomic is relaxed, gpu scope, on a different address. In PTX §8.7 a relaxed RMW forms a release pattern only when a `fence.sc`/`fence.acq_rel` precedes it in the same thread. Here no fence precedes it.
  - The reading block has no acquire fence after it observes the flag.
  - So there is no base-causality path from block A's `STG` to the last block's `LDG`. Both accesses are plain (weak) and overlap, so the pair is a data race (DR).
- **The author's own idiom.** The author's kernel 5 in the same file (L535) does have a `__threadfence()` before its flag atomic. Even that has no acquire on the reader side.
- **Observed effect.** Native runs: 3/3 printed `All results match` (`eval/realworld/native/llmc-new-1-buggy.json`). No wrong output has been observed. The race is formal under PTX: it needs a store to stay invisible at L2 after the same SM's later atomic has completed there.

## Racecheck cannot see it (claim checked)

- `eval/realworld/racecheck/llmc-new-1-buggy.txt` says only `racecheck n/a: global-memory target`. The harness did not run racecheck.
- The claim holds by the tool's documented scope. The Compute Sanitizer documentation, v2026.3.0 (the version used for the other targets, `compute-sanitizer 2026.3.0.0`), says of racecheck: "Currently, this tool only supports detecting accesses to on-chip shared memory." Its other race features (cluster/distributed shared memory, async copies into shared memory) all have shared memory as the checked target.
  - Source: https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html, section "Racecheck Tool".
- No other Compute Sanitizer tool checks inter-thread ordering of global memory. memcheck, initcheck and synccheck check other properties (not checked further).
- The paper may therefore say: cuRace reports this race and racecheck cannot report it by construction (global memory).
- Not done: an empirical racecheck run on `layernorm_backward`. The dossier's reproducer lists racecheck under "TO BE RUN" so the coordinator can confirm that it reports nothing.

## Note on the oracle

The oracle (`eval/realworld/oracle/llmc-new-1.json`, read-only) lists the reads as L1214–L1215. That is right for the source. It is the SASS line table that attributes the loads to L1217–L1218. If the scoring wants all 8 reports counted as matched, the fix is in how the attribution maps a load to its statement (the line of the first use instead of the load), not in the oracle. Nothing was changed.

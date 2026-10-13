# T16 re-score: the certain clock on the kept stores

Generated 2026-10-11 20:01 by `eval/baselines/t16_rescore.py tables` from the program details and the `parallel.py analyze` CSVs under `eval/results/t16-rescore/`.


## Set `main`: 594 programs, 464 with an RMW pc, 464 re-scored, 0 failed, 0 pending

- Kernels re-scored: 4571 (0 with exit records).
- **Parity of the default policy**: oracle(recorded) == the stored hb_races on 4571 of 4571 kernels (**proved-in-effect**).
- **Invariant Rep_certain >= Rep_recorded**: holds on 4571 of 4571 kernels (**proved-in-effect**).

### Chain edges per suite (vector-clock dumps; the certain policy's counters)

Chain edges = morally strong successor pairs r -> q on one location (the edges the recorded clock takes). `uncertain` = r's window still open at q (refused by the certain clock); `cross-warp` = the uncertain edges between RMWs of different warps, the quantity `eval/A2_WINDOWS.md` reports as 12.6 M of 29.9 M successor edges (42 %) over the evcand dumps (the lanes of one warp instruction always overlap); `open-ended` = the releaser's window never closed before the kernel's end (on a dump without exit records every thread's last RMW); `unsafe` = disjoint windows but a possible coherence intermediate not morally strong with the edge (refused as well).

| pset | kernels | chain edges | uncertain (windows overlap) | % | cross-warp | % | open-ended | unsafe | refused | refused % |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 3608 | 5,920,046 | 5,008,094 | 84.6 % | 2,865,232 | 48.4 % | 1,620,156 | 0 | 5,008,094 | 84.6 % |
| P2 | 41 | 569 | 215 | 37.8 % | 211 | 37.1 % | 144 | 0 | 215 | 37.8 % |
| P3 | 631 | 787,071 | 752,728 | 95.6 % | 106,749 | 13.6 % | 368,983 | 0 | 752,728 | 95.6 % |
| P4 | 258 | 23,125,522 | 18,181,495 | 78.6 % | 9,615,277 | 41.6 % | 35,026 | 4,476 | 18,185,971 | 78.6 % |
| P5 | 33 | 114 | 70 | 61.4 % | 70 | 61.4 % | 26 | 2 | 72 | 63.2 % |
| **all** | 4571 | 29,833,322 | 23,942,602 | 80.3 % | 12,587,539 | 42.2 % | 2,024,335 | 4,478 | 23,947,080 | 80.3 % |

### Reports the certain clock adds (pc pairs / instances beyond the recorded clock)

| pset | new DR pc pairs | new SC pc pairs | added instances | of which a2_uncertain |
|---|---|---|---|---|
| P4 | 0 | 445 | 4,377,805 | 4,377,805 (100.0 %) |
| P5 | 1 | 4 | 5 | 5 (100.0 %) |

### Verdicts: recorded -> certain (`parallel.py analyze`, this checkout)

Race alone under `certain` is the **Race (sound)** column; FP / TP as programs over the labelled ones (ERROR/TIMEOUT excluded).

| pset | mode | R u L FP / TP (recorded) | R u L FP / TP (certain) | Race alone FP / TP (recorded) | **Race (sound)** FP / TP | labelled CLEAN / RACE |
|---|---|---|---|---|---|---|
| P1 | cuVein-SC | 0 / 196 | 0 / 196 | 0 / 196 | **0 / 196** | 188 / 196 |
| P1 | cuVein-VC | 0 / 174 | 0 / 174 | 0 / 174 | **0 / 174** | 187 / 174 |
| P2 | cuVein-SC | 0 / 25 | 0 / 25 | 0 / 25 | **0 / 25** | 28 / 30 |
| P2 | cuVein-VC | 0 / 25 | 0 / 25 | 0 / 25 | **0 / 25** | 28 / 30 |
| P3 | cuVein-SC | 16 / 0 | 16 / 0 | 16 / 0 | **16 / 0** | 58 / 0 |
| P3 | cuVein-VC | 14 / 0 | 14 / 0 | 14 / 0 | **14 / 0** | 56 / 0 |
| P4 | cuVein-SC | 2 / 14 | 2 / 14 | 2 / 14 | **2 / 14** | 14 / 14 |
| P4 | cuVein-VC | 2 / 9 | 2 / 9 | 2 / 9 | **2 / 9** | 9 / 9 |
| P5 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 14 / 19 |
| P5 | cuVein-VC | 1 / 3 | 1 / 4 | 1 / 3 | **1 / 4** | 14 / 19 |
| P6 | cuVein-SC | 0 / 5 | 0 / 5 | 0 / 5 | **0 / 5** | 17 / 11 |
| P6 | cuVein-VC | 0 / 5 | 0 / 5 | 0 / 5 | **0 / 5** | 17 / 10 |
| P9 | cuVein-SC | 1 / 0 | 1 / 0 | 1 / 0 | **1 / 0** | 2 / 0 |
| P9 | cuVein-VC | 1 / 0 | 1 / 0 | 1 / 0 | **1 / 0** | 1 / 0 |

### Programs whose verdict differs between the policies (1)

| pset | mode | program | label | R u L | Race alone | classes recorded | classes certain |
|---|---|---|---|---|---|---|---|
| P5 | cuVein-VC | `P5-race_interblock_none-lock_rtraw` | RACE | CLEAN -> RACE | CLEAN -> RACE | latent-sc=1 | sc=1 structural=1 |

### New pc pairs under certain, by program (450)

| program | kernel | pc pair | class | instances | a2_uncertain |
|---|---|---|---|---|---|
| `P4-reduction-norace-large` | kernel_0.json | 0x440 / 0x5a0 | SC | 1920 | 1920 |
| `P4-reduction-norace-large` | kernel_0.json | 0x5e0 / 0x730 | SC | 960 | 960 |
| `P4-reduction-norace-large` | kernel_0.json | 0xfd0 / 0x1120 | SC | 128 | 128 |
| `P4-reduction-norace-large` | kernel_0.json | 0x1160 / 0x12b0 | SC | 64 | 64 |
| `P4-reduction-norace-large` | kernel_0.json | 0x12f0 / 0x1420 | SC | 32 | 32 |
| `P4-reduction-norace-small` | kernel_0.json | 0x2a0 / 0x400 | SC | 512 | 512 |
| `P4-reduction-norace-small` | kernel_0.json | 0x440 / 0x5a0 | SC | 256 | 256 |
| `P4-reduction-norace-small` | kernel_0.json | 0x5e0 / 0x730 | SC | 128 | 128 |
| `P4-reduction-norace-small` | kernel_0.json | 0xfd0 / 0x1120 | SC | 128 | 128 |
| `P4-reduction-norace-small` | kernel_0.json | 0x1160 / 0x12b0 | SC | 64 | 64 |
| `P4-reduction-norace-small` | kernel_0.json | 0x12f0 / 0x1420 | SC | 32 | 32 |
| `P4-reduction-racy-large` | kernel_0.json | 0xfa0 / 0x10f0 | SC | 128 | 128 |
| `P4-reduction-racy-large` | kernel_0.json | 0x1130 / 0x1280 | SC | 64 | 64 |
| `P4-reduction-racy-small` | kernel_0.json | 0x2a0 / 0x400 | SC | 512 | 512 |
| `P4-reduction-racy-small` | kernel_0.json | 0xfa0 / 0x10f0 | SC | 128 | 128 |
| `P4-reduction-racy-small` | kernel_0.json | 0x1130 / 0x1280 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xd90 / 0x15d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xdf0 / 0x1650 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xe20 / 0x16d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xed0 / 0x1750 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_0.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_0.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_1.json | 0x1050 / 0x2510 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_10.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_10.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_11.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_11.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xd90 / 0x15d0 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xd90 / 0x1e00 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xdf0 / 0x1650 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xdf0 / 0x1f80 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xe20 / 0x16d0 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xe20 / 0x2100 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xed0 / 0x1750 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xed0 / 0x2270 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_12.json | 0x1050 / 0x1970 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_12.json | 0x1050 / 0x2510 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xd90 / 0x1e00 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xdf0 / 0x1f80 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xe20 / 0x2100 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xed0 / 0x2270 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_13.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_13.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_14.json | 0x1050 / 0x1970 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_14.json | 0x1050 / 0x2510 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_15.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_15.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xd90 / 0x15d0 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xdf0 / 0x1650 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xe20 / 0x16d0 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xed0 / 0x1750 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_16.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xd90 / 0x1e00 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xdf0 / 0x1f80 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xe20 / 0x2100 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xed0 / 0x2270 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_17.json | 0x1050 / 0x1970 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_17.json | 0x1050 / 0x2510 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xd90 / 0x1e00 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xdf0 / 0x1f80 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xe20 / 0x2100 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xed0 / 0x2270 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_18.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xd90 / 0x1e00 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xdf0 / 0x1f80 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xe20 / 0x2100 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xed0 / 0x2270 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_19.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_2.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_20.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_20.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_21.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_22.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_22.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_23.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xd90 / 0x1e00 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xdf0 / 0x1f80 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xe20 / 0x2100 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xed0 / 0x2270 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_24.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_24.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xd90 / 0x1e00 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xdf0 / 0x1f80 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xe20 / 0x2100 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xed0 / 0x2270 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_25.json | 0x1050 / 0x1970 | SC | 70 | 70 |
| `P4-rule-110-norace-large` | kernel_25.json | 0x1050 / 0x2510 | SC | 71 | 71 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_26.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_26.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xd90 / 0x15d0 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xd90 / 0x1e00 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xdf0 / 0x1650 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xdf0 / 0x1f80 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xe20 / 0x16d0 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xe20 / 0x2100 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xed0 / 0x1750 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xed0 / 0x2270 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_27.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_27.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_28.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_28.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xd90 / 0x1e00 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xdf0 / 0x1f80 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xe20 / 0x2100 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xed0 / 0x2270 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_29.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_29.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_3.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_30.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_30.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xd90 / 0x1e00 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xdf0 / 0x1f80 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xe20 / 0x2100 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xed0 / 0x2270 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_31.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xd90 / 0x1e00 | SC | 253 | 253 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xdf0 / 0x1f80 | SC | 253 | 253 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xe20 / 0x2100 | SC | 253 | 253 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xed0 / 0x2270 | SC | 253 | 253 |
| `P4-rule-110-norace-large` | kernel_32.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_32.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xd90 / 0x1e00 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xdf0 / 0x1f80 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xe20 / 0x2100 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xed0 / 0x2270 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_33.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_33.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_34.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_34.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xd90 / 0x1e00 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xdf0 / 0x1f80 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xe20 / 0x2100 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xed0 / 0x2270 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_35.json | 0x1050 / 0x1970 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_35.json | 0x1050 / 0x2510 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_36.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_36.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_37.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_37.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xd90 / 0x1e00 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xdf0 / 0x1f80 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xe20 / 0x2100 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xed0 / 0x2270 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_38.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_38.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xd90 / 0x1e00 | SC | 227 | 227 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xdf0 / 0x1f80 | SC | 227 | 227 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xe20 / 0x2100 | SC | 227 | 227 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xed0 / 0x2270 | SC | 227 | 227 |
| `P4-rule-110-norace-large` | kernel_39.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_4.json | 0x1050 / 0x1970 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_4.json | 0x1050 / 0x2510 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xd90 / 0x1e00 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xdf0 / 0x1f80 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xe20 / 0x2100 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xed0 / 0x2270 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_40.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_41.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xd90 / 0x15d0 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xd90 / 0x1e00 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xdf0 / 0x1650 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xdf0 / 0x1f80 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xe20 / 0x16d0 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xe20 / 0x2100 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xed0 / 0x1750 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xed0 / 0x2270 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_42.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_42.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_43.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_44.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_44.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xd90 / 0x1e00 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xdf0 / 0x1f80 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xe20 / 0x2100 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xed0 / 0x2270 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_45.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_45.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xd90 / 0x1e00 | SC | 226 | 226 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xdf0 / 0x1f80 | SC | 226 | 226 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xe20 / 0x2100 | SC | 226 | 226 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xed0 / 0x2270 | SC | 226 | 226 |
| `P4-rule-110-norace-large` | kernel_46.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_46.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_47.json | 0x1050 / 0x1970 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_47.json | 0x1050 / 0x2510 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xd90 / 0x1e00 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xdf0 / 0x1f80 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xe20 / 0x2100 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xed0 / 0x2270 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_48.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_49.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xd90 / 0x1e00 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xdf0 / 0x1f80 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xe20 / 0x2100 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xed0 / 0x2270 | SC | 228 | 228 |
| `P4-rule-110-norace-large` | kernel_5.json | 0x1050 / 0x1970 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_5.json | 0x1050 / 0x2510 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_50.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xd90 / 0x15d0 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xdf0 / 0x1650 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xe20 / 0x16d0 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xed0 / 0x1750 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_51.json | 0x1050 / 0x1970 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_51.json | 0x1050 / 0x2510 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_52.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_52.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xd90 / 0x1e00 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xdf0 / 0x1f80 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xe20 / 0x2100 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xed0 / 0x2270 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_53.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_53.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_54.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_54.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xd90 / 0x1e00 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xdf0 / 0x1f80 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xe20 / 0x2100 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xed0 / 0x2270 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_55.json | 0x1050 / 0x2510 | SC | 70 | 70 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xd90 / 0x15d0 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xdf0 / 0x1650 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xe20 / 0x16d0 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xed0 / 0x1750 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_56.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_56.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xd90 / 0x15d0 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xd90 / 0x1e00 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xdf0 / 0x1650 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xdf0 / 0x1f80 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xe20 / 0x16d0 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xe20 / 0x2100 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xed0 / 0x1750 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xed0 / 0x2270 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_57.json | 0x1050 / 0x1970 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_57.json | 0x1050 / 0x2510 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_58.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_58.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_59.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_6.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_60.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_60.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xd90 / 0x1e00 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xdf0 / 0x1f80 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xe20 / 0x2100 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xed0 / 0x2270 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_61.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_62.json | 0x1050 / 0x2510 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_63.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_63.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_63.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_63.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_63.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_63.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_7.json | 0xd90 / 0x1e00 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_7.json | 0xdf0 / 0x1f80 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_7.json | 0xe20 / 0x2100 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_7.json | 0xed0 / 0x2270 | SC | 229 | 229 |

_... 50 more in the detail JSONs._

## Set `exits`: 97 programs, 77 with an RMW pc, 77 re-scored, 0 failed, 0 pending

- Kernels re-scored: 539 (539 with exit records).
- **Parity of the default policy**: oracle(recorded) == the stored hb_races on 539 of 539 kernels (**proved-in-effect**).
- **Invariant Rep_certain >= Rep_recorded**: holds on 539 of 539 kernels (**proved-in-effect**).

### Chain edges per suite (vector-clock dumps; the certain policy's counters)

Chain edges = morally strong successor pairs r -> q on one location (the edges the recorded clock takes). `uncertain` = r's window still open at q (refused by the certain clock); `cross-warp` = the uncertain edges between RMWs of different warps, the quantity `eval/A2_WINDOWS.md` reports as 12.6 M of 29.9 M successor edges (42 %) over the evcand dumps (the lanes of one warp instruction always overlap); `open-ended` = the releaser's window never closed before the kernel's end (on a dump without exit records every thread's last RMW); `unsafe` = disjoint windows but a possible coherence intermediate not morally strong with the edge (refused as well).

| pset | kernels | chain edges | uncertain (windows overlap) | % | cross-warp | % | open-ended | unsafe | refused | refused % |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 64 | 13,809 | 9,341 | 67.6 % | 6,497 | 47.0 % | 0 | 0 | 9,341 | 67.6 % |
| P3 | 104 | 170,832 | 165,497 | 96.9 % | 17,652 | 10.3 % | 0 | 0 | 165,497 | 96.9 % |
| P4 | 333 | 40,847,840 | 33,366,389 | 81.7 % | 19,790,221 | 48.4 % | 0 | 8,959 | 33,375,348 | 81.7 % |
| P5 | 33 | 114 | 64 | 56.1 % | 64 | 56.1 % | 0 | 2 | 66 | 57.9 % |
| PI | 5 | 16 | 7 | 43.8 % | 7 | 43.8 % | 0 | 0 | 7 | 43.8 % |
| **all** | 539 | 41,032,611 | 33,541,298 | 81.7 % | 19,814,441 | 48.3 % | 0 | 8,961 | 33,550,259 | 81.8 % |

### Reports the certain clock adds (pc pairs / instances beyond the recorded clock)

| pset | new DR pc pairs | new SC pc pairs | added instances | of which a2_uncertain |
|---|---|---|---|---|
| P4 | 0 | 457 | 4,389,006 | 4,389,006 (100.0 %) |
| P5 | 1 | 2 | 3 | 3 (100.0 %) |

### Verdicts: recorded -> certain (`parallel.py analyze`, this checkout)

Race alone under `certain` is the **Race (sound)** column; FP / TP as programs over the labelled ones (ERROR/TIMEOUT excluded).

| pset | mode | R u L FP / TP (recorded) | R u L FP / TP (certain) | Race alone FP / TP (recorded) | **Race (sound)** FP / TP | labelled CLEAN / RACE |
|---|---|---|---|---|---|---|
| P1 | cuVein-SC | 0 / 7 | 0 / 7 | 0 / 7 | **0 / 7** | 2 / 7 |
| P1 | cuVein-VC | 0 / 7 | 0 / 7 | 0 / 7 | **0 / 7** | 2 / 7 |
| P3 | cuVein-SC | 2 / 0 | 2 / 0 | 2 / 0 | **2 / 0** | 10 / 0 |
| P3 | cuVein-VC | 2 / 0 | 2 / 0 | 2 / 0 | **2 / 0** | 10 / 0 |
| P4 | cuVein-SC | 2 / 12 | 2 / 12 | 2 / 12 | **2 / 12** | 13 / 12 |
| P4 | cuVein-VC | 2 / 12 | 2 / 12 | 2 / 12 | **2 / 12** | 13 / 12 |
| P5 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 14 / 19 |
| P5 | cuVein-VC | 1 / 3 | 1 / 4 | 1 / 3 | **1 / 4** | 14 / 19 |
| P6 | cuVein-SC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 6 / 3 |
| P6 | cuVein-VC | 0 / 2 | 0 / 2 | 0 / 2 | **0 / 2** | 6 / 3 |
| PI | cuVein-SC | 0 / 4 | 0 / 4 | 0 / 4 | **0 / 4** | 3 / 5 |
| PI | cuVein-VC | 0 / 4 | 0 / 4 | 0 / 4 | **0 / 4** | 3 / 5 |

### Programs whose verdict differs between the policies (1)

| pset | mode | program | label | R u L | Race alone | classes recorded | classes certain |
|---|---|---|---|---|---|---|---|
| P5 | cuVein-VC | `P5-race_interblock_none-lock_rtraw` | RACE | CLEAN -> RACE | CLEAN -> RACE | latent-sc=1 | sc=1 structural=1 |

### New pc pairs under certain, by program (460)

| program | kernel | pc pair | class | instances | a2_uncertain |
|---|---|---|---|---|---|
| `P4-reduction-norace-large` | kernel_0.json | 0x440 / 0x5a0 | SC | 1888 | 1888 |
| `P4-reduction-norace-large` | kernel_0.json | 0x5e0 / 0x730 | SC | 960 | 960 |
| `P4-reduction-norace-large` | kernel_0.json | 0xfd0 / 0x1120 | SC | 128 | 128 |
| `P4-reduction-norace-large` | kernel_0.json | 0x1160 / 0x12b0 | SC | 64 | 64 |
| `P4-reduction-norace-large` | kernel_0.json | 0x12f0 / 0x1420 | SC | 32 | 32 |
| `P4-reduction-norace-small` | kernel_0.json | 0x440 / 0x5a0 | SC | 256 | 256 |
| `P4-reduction-norace-small` | kernel_0.json | 0x5e0 / 0x730 | SC | 128 | 128 |
| `P4-reduction-norace-small` | kernel_0.json | 0xfd0 / 0x1120 | SC | 128 | 128 |
| `P4-reduction-norace-small` | kernel_0.json | 0x1160 / 0x12b0 | SC | 32 | 32 |
| `P4-reduction-norace-small` | kernel_0.json | 0x12f0 / 0x1420 | SC | 32 | 32 |
| `P4-reduction-racy-large` | kernel_0.json | 0x440 / 0x5a0 | SC | 1280 | 1280 |
| `P4-reduction-racy-large` | kernel_0.json | 0xfa0 / 0x10f0 | SC | 128 | 128 |
| `P4-reduction-racy-large` | kernel_0.json | 0x1130 / 0x1280 | SC | 64 | 64 |
| `P4-reduction-racy-small` | kernel_0.json | 0x2a0 / 0x400 | SC | 512 | 512 |
| `P4-reduction-racy-small` | kernel_0.json | 0x440 / 0x5a0 | SC | 224 | 224 |
| `P4-reduction-racy-small` | kernel_0.json | 0xfa0 / 0x10f0 | SC | 128 | 128 |
| `P4-reduction-racy-small` | kernel_0.json | 0x1130 / 0x1280 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_0.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_0.json | 0x1050 / 0x1970 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_0.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xd90 / 0x1e00 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xdf0 / 0x1f80 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xe20 / 0x2100 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_1.json | 0xed0 / 0x2270 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_1.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xd90 / 0x15d0 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xdf0 / 0x1650 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xe20 / 0x16d0 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xed0 / 0x1750 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_10.json | 0x1050 / 0x1970 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_10.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_11.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_11.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_11.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_12.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_12.json | 0x1050 / 0x1970 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_12.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xd90 / 0x15d0 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xd90 / 0x1e00 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xdf0 / 0x1650 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xdf0 / 0x1f80 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xe20 / 0x16d0 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xe20 / 0x2100 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xed0 / 0x1750 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0xed0 / 0x2270 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_13.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_13.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xd90 / 0x15d0 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xdf0 / 0x1650 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xe20 / 0x16d0 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xed0 / 0x1750 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_14.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_14.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xd90 / 0x15d0 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xd90 / 0x1e00 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xdf0 / 0x1650 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xdf0 / 0x1f80 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xe20 / 0x16d0 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xe20 / 0x2100 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xed0 / 0x1750 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0xed0 / 0x2270 | SC | 250 | 250 |
| `P4-rule-110-norace-large` | kernel_15.json | 0x1050 / 0x1970 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_15.json | 0x1050 / 0x2510 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_16.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_16.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_17.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_17.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_17.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_18.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_18.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_18.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xd90 / 0x1e00 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xdf0 / 0x1f80 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xe20 / 0x2100 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_19.json | 0xed0 / 0x2270 | SC | 248 | 248 |
| `P4-rule-110-norace-large` | kernel_19.json | 0x1050 / 0x2510 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xd90 / 0x1e00 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xdf0 / 0x1f80 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xe20 / 0x2100 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_2.json | 0xed0 / 0x2270 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_2.json | 0x1050 / 0x1970 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_2.json | 0x1050 / 0x2510 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_20.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_20.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_20.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xd90 / 0x1e00 | SC | 252 | 252 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xdf0 / 0x1f80 | SC | 252 | 252 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xe20 / 0x2100 | SC | 252 | 252 |
| `P4-rule-110-norace-large` | kernel_21.json | 0xed0 / 0x2270 | SC | 252 | 252 |
| `P4-rule-110-norace-large` | kernel_21.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_22.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_22.json | 0x1050 / 0x1970 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_22.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xd90 / 0x1e00 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xdf0 / 0x1f80 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xe20 / 0x2100 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_23.json | 0xed0 / 0x2270 | SC | 232 | 232 |
| `P4-rule-110-norace-large` | kernel_23.json | 0x1050 / 0x2510 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xd90 / 0x1e00 | SC | 230 | 230 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xdf0 / 0x1f80 | SC | 230 | 230 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xe20 / 0x2100 | SC | 230 | 230 |
| `P4-rule-110-norace-large` | kernel_24.json | 0xed0 / 0x2270 | SC | 230 | 230 |
| `P4-rule-110-norace-large` | kernel_24.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_24.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xd90 / 0x1e00 | SC | 225 | 225 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xdf0 / 0x1f80 | SC | 225 | 225 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xe20 / 0x2100 | SC | 225 | 225 |
| `P4-rule-110-norace-large` | kernel_25.json | 0xed0 / 0x2270 | SC | 225 | 225 |
| `P4-rule-110-norace-large` | kernel_25.json | 0x1050 / 0x2510 | SC | 59 | 59 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_26.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_26.json | 0x1050 / 0x1970 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_26.json | 0x1050 / 0x2510 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xe20 / 0x2100 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_27.json | 0xed0 / 0x2270 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_27.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xd90 / 0x1e00 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xdf0 / 0x1f80 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xe20 / 0x2100 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_28.json | 0xed0 / 0x2270 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_28.json | 0x1050 / 0x2510 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_29.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_29.json | 0x1050 / 0x2510 | SC | 56 | 56 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xd90 / 0x1e00 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xdf0 / 0x1f80 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xe20 / 0x2100 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_3.json | 0xed0 / 0x2270 | SC | 233 | 233 |
| `P4-rule-110-norace-large` | kernel_3.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_3.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_30.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_30.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_30.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xd90 / 0x1e00 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xdf0 / 0x1f80 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xe20 / 0x2100 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0xed0 / 0x2270 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_31.json | 0x1050 / 0x2510 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_32.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_32.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xd90 / 0x1e00 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xdf0 / 0x1f80 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xe20 / 0x2100 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_33.json | 0xed0 / 0x2270 | SC | 246 | 246 |
| `P4-rule-110-norace-large` | kernel_33.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_33.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_34.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_34.json | 0x1050 / 0x1970 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_34.json | 0x1050 / 0x2510 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xd90 / 0x1e00 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xdf0 / 0x1f80 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xe20 / 0x2100 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_35.json | 0xed0 / 0x2270 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_35.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_35.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_36.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_36.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_36.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xd90 / 0x15d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xdf0 / 0x1650 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xe20 / 0x16d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xed0 / 0x1750 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_37.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_37.json | 0x1050 / 0x2510 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xd90 / 0x1e00 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xdf0 / 0x1f80 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xe20 / 0x2100 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_38.json | 0xed0 / 0x2270 | SC | 229 | 229 |
| `P4-rule-110-norace-large` | kernel_38.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_39.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_39.json | 0x1050 / 0x1970 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_39.json | 0x1050 / 0x2510 | SC | 58 | 58 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_4.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_4.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_4.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xd90 / 0x1e00 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xdf0 / 0x1f80 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xe20 / 0x2100 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_40.json | 0xed0 / 0x2270 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_40.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_40.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_41.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_41.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_42.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_42.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xd90 / 0x1e00 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xdf0 / 0x1f80 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xe20 / 0x2100 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_43.json | 0xed0 / 0x2270 | SC | 236 | 236 |
| `P4-rule-110-norace-large` | kernel_43.json | 0x1050 / 0x1970 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_43.json | 0x1050 / 0x2510 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xd90 / 0x1e00 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xdf0 / 0x1f80 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xe20 / 0x2100 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_44.json | 0xed0 / 0x2270 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_44.json | 0x1050 / 0x2510 | SC | 57 | 57 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xd90 / 0x1e00 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xdf0 / 0x1f80 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xe20 / 0x2100 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_45.json | 0xed0 / 0x2270 | SC | 249 | 249 |
| `P4-rule-110-norace-large` | kernel_45.json | 0x1050 / 0x2510 | SC | 70 | 70 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xd90 / 0x15d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xdf0 / 0x1650 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xe20 / 0x16d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xed0 / 0x1750 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_46.json | 0x1050 / 0x1970 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_46.json | 0x1050 / 0x2510 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_47.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_47.json | 0x1050 / 0x1970 | SC | 67 | 67 |
| `P4-rule-110-norace-large` | kernel_47.json | 0x1050 / 0x2510 | SC | 68 | 68 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xd90 / 0x1e00 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xdf0 / 0x1f80 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xe20 / 0x2100 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_48.json | 0xed0 / 0x2270 | SC | 245 | 245 |
| `P4-rule-110-norace-large` | kernel_48.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_48.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xd90 / 0x15d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xdf0 / 0x1650 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xe20 / 0x16d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xed0 / 0x1750 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_49.json | 0x1050 / 0x1970 | SC | 62 | 62 |
| `P4-rule-110-norace-large` | kernel_49.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_5.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_5.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_5.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xd90 / 0x15d0 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xdf0 / 0x1650 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xe20 / 0x16d0 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xed0 / 0x1750 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_50.json | 0x1050 / 0x1970 | SC | 69 | 69 |
| `P4-rule-110-norace-large` | kernel_50.json | 0x1050 / 0x2510 | SC | 70 | 70 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xd90 / 0x1e00 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xdf0 / 0x1f80 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xe20 / 0x2100 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_51.json | 0xed0 / 0x2270 | SC | 244 | 244 |
| `P4-rule-110-norace-large` | kernel_51.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_51.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xd90 / 0x15d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xd90 / 0x1e00 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xdf0 / 0x1650 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xdf0 / 0x1f80 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xe20 / 0x16d0 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xe20 / 0x2100 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xed0 / 0x1750 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0xed0 / 0x2270 | SC | 239 | 239 |
| `P4-rule-110-norace-large` | kernel_52.json | 0x1050 / 0x1970 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_52.json | 0x1050 / 0x2510 | SC | 60 | 60 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xd90 / 0x1e00 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xdf0 / 0x1f80 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xe20 / 0x2100 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_53.json | 0xed0 / 0x2270 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_53.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_53.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xd90 / 0x15d0 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xd90 / 0x1e00 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xdf0 / 0x1650 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xdf0 / 0x1f80 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xe20 / 0x16d0 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xe20 / 0x2100 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xed0 / 0x1750 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0xed0 / 0x2270 | SC | 237 | 237 |
| `P4-rule-110-norace-large` | kernel_54.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_54.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xd90 / 0x1e00 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xdf0 / 0x1f80 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xe20 / 0x2100 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_55.json | 0xed0 / 0x2270 | SC | 234 | 234 |
| `P4-rule-110-norace-large` | kernel_55.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_55.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xd90 / 0x1e00 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xdf0 / 0x1f80 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xe20 / 0x2100 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_56.json | 0xed0 / 0x2270 | SC | 231 | 231 |
| `P4-rule-110-norace-large` | kernel_56.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xd90 / 0x15d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xd90 / 0x1e00 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xdf0 / 0x1650 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xdf0 / 0x1f80 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xe20 / 0x16d0 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xe20 / 0x2100 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xed0 / 0x1750 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0xed0 / 0x2270 | SC | 243 | 243 |
| `P4-rule-110-norace-large` | kernel_57.json | 0x1050 / 0x1970 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_57.json | 0x1050 / 0x2510 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xd90 / 0x1e00 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xdf0 / 0x1f80 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xe20 / 0x2100 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_58.json | 0xed0 / 0x2270 | SC | 242 | 242 |
| `P4-rule-110-norace-large` | kernel_58.json | 0x1050 / 0x2510 | SC | 64 | 64 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xd90 / 0x1e00 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xdf0 / 0x1f80 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xe20 / 0x2100 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_59.json | 0xed0 / 0x2270 | SC | 240 | 240 |
| `P4-rule-110-norace-large` | kernel_59.json | 0x1050 / 0x1970 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_59.json | 0x1050 / 0x2510 | SC | 63 | 63 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xd90 / 0x1e00 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xdf0 / 0x1f80 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xe20 / 0x2100 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_6.json | 0xed0 / 0x2270 | SC | 241 | 241 |
| `P4-rule-110-norace-large` | kernel_6.json | 0x1050 / 0x1970 | SC | 65 | 65 |
| `P4-rule-110-norace-large` | kernel_6.json | 0x1050 / 0x2510 | SC | 66 | 66 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xd90 / 0x1e00 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xdf0 / 0x1f80 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xe20 / 0x2100 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_60.json | 0xed0 / 0x2270 | SC | 238 | 238 |
| `P4-rule-110-norace-large` | kernel_60.json | 0x1050 / 0x1970 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_60.json | 0x1050 / 0x2510 | SC | 61 | 61 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xd90 / 0x1e00 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xdf0 / 0x1f80 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xe20 / 0x2100 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_61.json | 0xed0 / 0x2270 | SC | 247 | 247 |
| `P4-rule-110-norace-large` | kernel_61.json | 0x1050 / 0x1970 | SC | 70 | 70 |
| `P4-rule-110-norace-large` | kernel_61.json | 0x1050 / 0x2510 | SC | 71 | 71 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xd90 / 0x1e00 | SC | 235 | 235 |
| `P4-rule-110-norace-large` | kernel_62.json | 0xdf0 / 0x1f80 | SC | 235 | 235 |

_... 60 more in the detail JSONs._

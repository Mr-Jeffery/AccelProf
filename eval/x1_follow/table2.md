| # | commit | date | merge | scalar-clock mode at this commit | knobs | bfs SC wall (s) | SC kernels | SC Kernel2 #13 / #15 (s) | bfs VC wall (s) | VC kernels | VC Kernel2 #13 / #15 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `d38d057 (= ba99486 build)` | 2026-10-13 | installed runtime (X1) | sync instance online | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 69 / not reached | **600.0 (cap)** | 15/24 | 483 / not reached |
| 1 | `b7d463e` | 2026-09-22 | Sept-22 runtime (eval merge) | records dumped only (no HbClock) | NO_ENGINE, dump | 18.6 | 24/24 | 0 / 0 | 75.3 | 24/24 | 2 / 4 |
| 2 | `1a45653` | 2026-09-23 | T8 | records dumped only (no HbClock) | MODE, dump | 18.6 | 24/24 | 0 / 0 | 75.1 | 24/24 | 3 / 4 |
| 3 | `6d843e3` | 2026-09-23 | T5a | records dumped only (no HbClock) | MODE, dump, STATS | 18.6 | 24/24 | 0 / 1 | 80.7 | 24/24 | 2 / 4 |
| 4 | `07d2798` | 2026-09-23 | T2 | records dumped only (no HbClock) | MODE, dump, STATS | 18.6 | 24/24 | 0 / 0 | 81.6 | 24/24 | 3 / 5 |
| 5 | `bc32a1f` | 2026-09-23 | T1a | records dumped only (no HbClock) | MODE, dump, STATS | 18.9 | 24/24 | 1 / 1 | 80.3 | 24/24 | 3 / 5 |
| 6 | `3331d35` | 2026-09-23 | T1a review | records dumped only (no HbClock) | MODE, dump, STATS | 18.3 | 24/24 | 0 / 1 | 80.8 | 24/24 | 3 / 5 |
| 7 | `0b64d34` | 2026-09-28 | T3b | records dumped only (no HbClock) | MODE, dump, STATS | 19.1 | 24/24 | 0 / 1 | 83.3 | 24/24 | 3 / 4 |
| 8 | `ebc464f` | 2026-09-28 | T9 | records dumped only (no HbClock) | MODE, dump, STATS | 19.2 | 24/24 | 0 / 0 | **600.1 (cap)** | 15/24 | 316 / not reached |
| 9 | `870dbb6` | 2026-09-28 | T3b×T9 fix | records dumped only (no HbClock) | MODE, dump, STATS | 19.0 | 24/24 | 1 / 1 | **600.1 (cap)** | 15/24 | 323 / not reached |
| 10 | `33a985c` | 2026-09-29 | T14 | records dumped only (no HbClock) | MODE, dump, STATS | 19.0 | 24/24 | 1 / 1 | **600.0 (cap)** | 13/24 | not reached / not reached |
| 11 | `be82754` | 2026-09-29 | T10 | records dumped only (no HbClock) | MODE, dump, STATS | 19.2 | 24/24 | 1 / 1 | **600.0 (cap)** | 13/24 | not reached / not reached |
| 12 | `b3bfdf3` | 2026-09-30 | T5b | records dumped only (no HbClock) | MODE, dump, STATS | 19.5 | 24/24 | 1 / 1 | **600.1 (cap)** | 13/24 | not reached / not reached |
| 13 | `7849a70` | 2026-09-30 | T12 | records dumped only (no HbClock) | MODE, dump, STATS | 19.1 | 24/24 | 0 / 1 | **600.0 (cap)** | 15/24 | 457 / not reached |
| 14 | `de565c0` | 2026-09-30 | T15 | records dumped only (no HbClock) | MODE, dump, STATS | 19.4 | 24/24 | 1 / 1 | **600.1 (cap)** | 15/24 | 447 / not reached |
| 15 | `b6c9055` | 2026-10-01 | T17 | records dumped only (no HbClock) | MODE, dump, STATS | 19.3 | 24/24 | 0 / 1 | **600.0 (cap)** | 15/24 | 440 / not reached |
| 16 | `0a25f7d` | 2026-10-05 | T18 | records dumped only (no HbClock) | MODE, dump, STATS | 19.3 | 24/24 | 1 / 0 | **600.0 (cap)** | 15/24 | 444 / not reached |
| 17 | `d67ed41` | 2026-10-05 | T4 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 209 / not reached | **600.1 (cap)** | 15/24 | 428 / not reached |
| 18 | `3c7eefd` | 2026-10-10 | T19 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 82 / not reached | **600.0 (cap)** | 15/24 | 495 / not reached |
| 19 | `d3f1e98` | 2026-10-11 | T16 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 83 / not reached | **600.1 (cap)** | 15/24 | 492 / not reached |
| 20 | `ba99486` | 2026-10-12 | T20 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.0 (cap)** | 15/24 | 67 / not reached | **600.0 (cap)** | 15/24 | 487 / not reached |
| — | `installed`, YOSEMITE_HB_STATS unset | | control | sync instance online | MODE, DUMP=0 | **600.0 (cap)** | 15/24 | 67 / not reached | | | |

| nbody run | wall (s) | kernels finished | per-kernel time of the finished kernels (s) | µs / event of finished `accelerate_particles` launches |
|---|---|---|---|---|
| nbody-sc-0a25f7d | 600.1 (cap) | 6 + #6 truncated at the kill (19,609,470 records) | #0: 219, #1: 0, #2: 0, #3: 209, #4: 1, #5: 0 | #0: 6.84, #3: 6.53 |
| nbody-sc-d67ed41 | 600.1 (cap) | 6 | #0: 230, #1: 43, #2: 0, #3: 216, #4: 43, #5: 0 | #0: 7.19, #3: 6.75 |
| nbody-vc-0b64d34 | 600.0 (cap) | 3 | #0: 416, #1: 45, #2: 0 | #0: 13.00 |
| nbody-vc-ebc464f | 600.1 (cap) | 3 | #0: 431, #1: 43, #2: 0 | #0: 13.47 |

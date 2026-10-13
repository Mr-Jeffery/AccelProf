| run | value at | RMWs | values ok | cross-warp pairs | overlapping | inverted | inverted, non-overlapping | exec-interval violations |
|---|---|---|---|---|---|---|---|---|
| part 1 | after | 8 | True | 0 | 0 | 0 | 0 | 0 |
| part 2 | after | 8 | True | 28 | 28 | 5 | 0 | 0 |
| part 4 | after | 256 | True | 28672 | 28672 | 4096 | 0 | 0 |
| part 1 | next | 8 | True | 0 | 0 | 0 | 0 | 0 |
| part 2 | next | 8 | True | 28 | 28 | 5 | 0 | 0 |
| part 4 | next | 256 | True | 28672 | 28672 | 1024 | 0 | 0 |

| warps | value at | reps | critical sections | failed CAS | values ok | cross-warp lock-RMW pairs | overlapping | inverted | inverted, non-overlapping | S_k+1 recorded before E_k | hand-offs (k>=1) | rate | inverted by type ('X<trace Y': X recorded first, Y first in coherence order) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | after | 5 | 160 | 165 | True | 11750 | 320 | 0 | 0 | 0 (0, 0, 0, 0, 0) | 155 | 0.0% | {} |
| 4 | after | 5 | 320 | 1955 | True | 504170 | 5461 | 11 | 0 | 4 (1, 0, 1, 1, 1) | 315 | 1.3% | {'E<trace F': 3, 'F<trace S': 4, 'S<trace E': 4} |
| 16 | after | 5 | 1280 | 39835 | True | 168161867 | 533628 | 140 | 0 | 52 (10, 11, 5, 15, 11) | 1275 | 4.1% | {'E<trace F': 28, 'F<trace E': 7, 'F<trace S': 41, 'S<trace E': 52, 'F<trace F': 3, 'S<trace F': 9} |
| 2 | next | 5 | 160 | 165 | True | 11750 | 320 | 0 | 0 | 0 (0, 0, 0, 0, 0) | 155 | 0.0% | {} |
| 4 | next | 5 | 320 | 1948 | True | 500828 | 5462 | 10 | 0 | 2 (1, 0, 0, 0, 1) | 315 | 0.6% | {'F<trace S': 6, 'S<trace E': 2, 'E<trace F': 2} |
| 16 | next | 5 | 1280 | 40930 | True | 177205381 | 562648 | 184 | 0 | 48 (7, 8, 10, 7, 16) | 1275 | 3.8% | {'E<trace F': 30, 'F<trace E': 22, 'F<trace S': 55, 'S<trace E': 48, 'F<trace F': 15, 'S<trace F': 14} |

## Item 6: cost table (section (a) of FINAL_TABLES.md), collector-only from C1's rows

Wall in seconds, µs per record in parentheses; native wall = median of the program's native runs in the same job. Records = `events=` (collector-only: records drained, `accelprof -v`; scalar/vector-clock: `hb_events_count`). Different hosts per column (node in `cost_co_rows.csv`).

| program | records (C1) | native (s) C1 / X1b | **collector-only (C1)** | scalar-clock sharded N=16 (X1b) | vector-clock (X1b) | C1 node |
|---|---|---|---|---|---|---|
| P7-heartwall-cuda | 8,071,484,636 | 0.769 / 0.872 | **2,347.6 (0.2908)** | 5,728.7 (0.7097) | 61,435.9 (7.611) | c61 |
| P9-knn-cuda | 11,144,912,500 | 13.092 / 12.001 | **3,739.8 (0.3356)** | 9,680.4 (0.8686) | 58,674.2 (5.265) | c76 |
| P7-nbody-cuda | 320,355,120 | 14.570 / 14.144 | **59.9 (0.1868)** | 391.0 (1.221) | 11,252.4 (35.12) | c74 |
| P7-bfs-cuda | 7,436,165 | 1.069 / 1.371 | **4.8 (0.649)** | 12.1 (1.625) | 11,500.6 (1,547) | c63 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | 1,023 | 0.218 / 0.271 | **1.1 (1,045)** | 2.6 (2,582) | 1.6 (1,547) | c62 |
| P6-interkernel-global_readwrite_race-fixed | 1,000,004 | 0.771 / 0.770 | **5.3 (5.342)** | 5.5 (5.478) | 6.9 (6.933) | c74 |

Fits (OLS of tool wall on records), wall = intercept + slope × records:

| scope | column | runtime | n | intercept (s) | slope (µs/record) | R² |
|---|---|---|---|---|---|---|
| program set above | collector-only | f551ca0 (C1) | 6 | -24.61 | 0.3226 | 0.994 |
| program set above | scalar-clock sharded N=16 | f551ca0 (X1b) | 6 | -23.26 | 0.8166 | 0.987 |
| program set above | vector-clock | f551ca0 (X1b) | 6 | 5,993 | 5.47 | 0.924 |
| all complete (id,mode) rows | collector-only | f551ca0 (C1) | 4708 | 0.1028 | 0.4027 | 0.964 |
| suite P1 | collector-only | f551ca0 (C1) | 400 | 1.473 | 0.04359 | 0.000707 |
| suite P3 | collector-only | f551ca0 (C1) | 60 | 1.373 | -0.6025 | 0.00468 |
| suite P4 | collector-only | f551ca0 (C1) | 28 | 1.513 | 0.3555 | 0.591 |
| suite P5 | collector-only | f551ca0 (C1) | 33 | 1.333 | -2,853 | 0.000958 |
| suite P6 | collector-only | f551ca0 (C1) | 34 | 6.242 | 0.8157 | 0.938 |
| suite P7 | collector-only | f551ca0 (C1) | 14 | -577.9 | 0.4114 | 0.968 |
| suite P9 | collector-only | f551ca0 (C1) | 9 | 104.5 | 0.4151 | 0.778 |
| suite PI | collector-only | f551ca0 (C1) | 4130 | 1.181 | 0.7144 | 0.0028 |
| all complete (id,mode) rows | scalar-clock sharded N=16 | f551ca0 (X1b) | 4706 | 3.741 | 1.32 | 0.706 |
| suite P1 | scalar-clock sharded N=16 | f551ca0 (X1b) | 400 | 2.041 | 1.672 | 0.311 |
| suite P3 | scalar-clock sharded N=16 | f551ca0 (X1b) | 60 | 2.109 | 6.471 | 0.055 |
| suite P4 | scalar-clock sharded N=16 | f551ca0 (X1b) | 28 | 2.184 | 0.6983 | 0.885 |
| suite P5 | scalar-clock sharded N=16 | f551ca0 (X1b) | 33 | 1.725 | 9,420 | 0.00859 |
| suite P6 | scalar-clock sharded N=16 | f551ca0 (X1b) | 34 | 4.742 | 1.719 | 0.987 |
| suite P7 | scalar-clock sharded N=16 | f551ca0 (X1b) | 12 | 537.8 | 1.616 | 0.603 |
| suite P9 | scalar-clock sharded N=16 | f551ca0 (X1b) | 9 | 473.5 | 0.9792 | 0.883 |
| suite PI | scalar-clock sharded N=16 | f551ca0 (X1b) | 4130 | 1.453 | 5.42 | 0.0333 |
| all complete (id,mode) rows | vector-clock | f551ca0 (X1b) | 4704 | 11.92 | 6.256 | 0.91 |
| suite P1 | vector-clock | f551ca0 (X1b) | 400 | 0.7736 | 29.24 | 0.535 |
| suite P3 | vector-clock | f551ca0 (X1b) | 60 | 1.902 | 29.61 | 0.474 |
| suite P4 | vector-clock | f551ca0 (X1b) | 28 | -0.8294 | 48.73 | 0.495 |
| suite P5 | vector-clock | f551ca0 (X1b) | 33 | 1.867 | 3.827e+04 | 0.0654 |
| suite P6 | vector-clock | f551ca0 (X1b) | 34 | -158.6 | 29.89 | 0.944 |
| suite P7 | vector-clock | f551ca0 (X1b) | 11 | 2,066 | 6.132 | 0.891 |
| suite P9 | vector-clock | f551ca0 (X1b) | 8 | 1,537 | 5.88 | 0.916 |
| suite PI | vector-clock | f551ca0 (X1b) | 4130 | 0.9801 | 46.56 | 0.113 |

X3's section (a) collector-only fit (X1-follow, d38d057, 4 points on one host type each): intercept −1.757 s (`-n 1`) / 4.128 s (default), slope 0.2946 / 0.07542 µs per record. C1's runs are `-n 1`; the six-program fit above uses the six programs of the section.

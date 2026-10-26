| program | column | runtime | records | native (s) | tool wall (s) | us / record | node(s) |
|---|---|---|---|---|---|---|---|
| P7-heartwall-cuda | collector-only (-n 1) | d38d057 (X1-follow) | 8071484636 | 0.768 | 2345.058 | 0.2905 | c66 |
| P7-heartwall-cuda | collector-only (-n default) | d38d057 (X1-follow) | 8071484636 | 0.818 | 626.399 | 0.07761 | c61 |
| P7-heartwall-cuda | scalar-clock serial N=1 | d38d057 (X1) | 8071484636 | 0.778 | 32057.217 | 3.972 | c52 |
| P7-heartwall-cuda | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 8071484636 | 1.299 | 57990.516 | 7.185 | c66 |
| P7-heartwall-cuda | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 8071484636 | 1.021 | 4663.926 | 0.5778 | c63 |
| P7-heartwall-cuda | scalar-clock sharded N=16 | f551ca0 (X1b) | 8071484636 | 0.872 | 5728.658 | 0.7097 | c24 |
| P7-heartwall-cuda | vector-clock | d38d057 (X1) | 8071484636 | 0.883 | 35574.705 | 4.407 | c58 |
| P7-heartwall-cuda | vector-clock | f551ca0 (X1b) | 8071484636 | 0.937 | 61435.923 | 7.611 | c75 |
| P9-knn-cuda | collector-only (-n 1) | d38d057 (X1-follow) | 11144912500 | 13.542 | 3304.053 | 0.2965 | c61 |
| P9-knn-cuda | collector-only (-n default) | d38d057 (X1-follow) | 11144912500 | 13.692 | 834.968 | 0.07492 | c66 |
| P9-knn-cuda | scalar-clock serial N=1 | d38d057 (X1) | 11144912500 | 13.744 | 44762.407 | 4.016 | c66 |
| P9-knn-cuda | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 11144912500 | 18.763 | 46577.088 | 4.179 | c62 |
| P9-knn-cuda | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 11144912500 | 13.645 | 7567.589 | 0.679 | c60 |
| P9-knn-cuda | scalar-clock sharded N=16 | f551ca0 (X1b) | 11144912500 | 12.001 | 9680.410 | 0.8686 | c74 |
| P9-knn-cuda | vector-clock | d38d057 (X1) | 11144912500 | 13.549 | 57215.724 | 5.134 | c62 |
| P9-knn-cuda | vector-clock | f551ca0 (X1b) | 11144912500 | 13.793 | 58674.223 | 5.265 | c64 |
| P7-nbody-cuda | collector-only (-n 1) | d38d057 (X1-follow) |  |  | missing |  |  |
| P7-nbody-cuda | collector-only (-n default) | d38d057 (X1-follow) |  |  | missing |  |  |
| P7-nbody-cuda | scalar-clock serial N=1 | d38d057 (X1) | 320355120 | 12.399 | 8014.964 | 25.02 | c66 |
| P7-nbody-cuda | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 320355120 | 14.179 | 3783.024 | 11.81 | c40 |
| P7-nbody-cuda | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 320355120 | 14.195 | 387.443 | 1.209 | c40 |
| P7-nbody-cuda | scalar-clock sharded N=16 | f551ca0 (X1b) | 320355120 | 14.144 | 390.996 | 1.221 | c41 |
| P7-nbody-cuda | vector-clock | d38d057 (X1) | 320355120 | 12.394 | 8197.555 | 25.59 | c62 |
| P7-nbody-cuda | vector-clock | f551ca0 (X1b) | 320355120 | 14.256 | 11252.449 | 35.12 | c24 |
| P7-bfs-cuda | collector-only (-n 1) | d38d057 (X1-follow) |  |  | missing |  |  |
| P7-bfs-cuda | collector-only (-n default) | d38d057 (X1-follow) |  |  | missing |  |  |
| P7-bfs-cuda | scalar-clock serial N=1 | d38d057 (X1) | 7436165 | 1.421 | 1506.546 | 202.6 | c74 |
| P7-bfs-cuda | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 7436165 | 2.436 | 39.546 | 5.318 | c40 |
| P7-bfs-cuda | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 7436165 | 1.521 | 13.880 | 1.867 | c40 |
| P7-bfs-cuda | scalar-clock sharded N=16 | f551ca0 (X1b) | 7436165 | 1.371 | 12.085 | 1.625 | c74 |
| P7-bfs-cuda | vector-clock | d38d057 (X1) | 7436165 | 0.819 | 6289.863 | 845.8 | c51 |
| P7-bfs-cuda | vector-clock | f551ca0 (X1b) | 7436165 | 1.546 | 11500.605 | 1547 | c44 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | collector-only (-n 1) | d38d057 (X1-follow) | 1019 | 0.267 | 1.477 | 1449 | c66 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | collector-only (-n default) | d38d057 (X1-follow) | 1023 | 0.217 | 1.060 | 1036 | c66 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | scalar-clock serial N=1 | d38d057 (X1) | 1019 | 0.217 | 0.868 | 851.8 | c51 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) |  |  | missing |  |  |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) |  |  | missing |  |  |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | scalar-clock sharded N=16 | f551ca0 (X1b) | 1017 | 0.271 | 2.626 | 2582 | c73 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | vector-clock | d38d057 (X1) | 1019 | 0.217 | 0.868 | 851.8 | c51 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | vector-clock | f551ca0 (X1b) | 1017 | 0.271 | 1.573 | 1547 | c73 |
| P6-interkernel-global_readwrite_race-fixed | collector-only (-n 1) | d38d057 (X1-follow) | 1000004 | 0.768 | 3.871 | 3.871 | c66 |
| P6-interkernel-global_readwrite_race-fixed | collector-only (-n default) | d38d057 (X1-follow) | 1000004 | 0.718 | 3.553 | 3.553 | c66 |
| P6-interkernel-global_readwrite_race-fixed | scalar-clock serial N=1 | d38d057 (X1) | 1000004 | 0.719 | 4.926 | 4.926 | c60 |
| P6-interkernel-global_readwrite_race-fixed | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) |  |  | missing |  |  |
| P6-interkernel-global_readwrite_race-fixed | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) |  |  | missing |  |  |
| P6-interkernel-global_readwrite_race-fixed | scalar-clock sharded N=16 | f551ca0 (X1b) | 1000004 | 0.770 | 5.478 | 5.478 | c41 |
| P6-interkernel-global_readwrite_race-fixed | vector-clock | d38d057 (X1) | 1000004 | 0.719 | 5.578 | 5.578 | c60 |
| P6-interkernel-global_readwrite_race-fixed | vector-clock | f551ca0 (X1b) | 1000004 | 0.770 | 6.933 | 6.933 | c41 |

| scope | column | runtime | n | intercept (s) | slope (us/record) | R2 |
|---|---|---|---|---|---|---|
| program set above | collector-only (-n 1) | d38d057 (X1-follow) | 4 | -1.757 | 0.2946 | 0.9998 |
| program set above | collector-only (-n default) | d38d057 (X1-follow) | 4 | 4.128 | 0.07542 | 0.9995 |
| program set above | scalar-clock N=1 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 4 | 3242 | 4.882 | 0.8584 |
| program set above | scalar-clock N=16 (T22-cont perf build) | T22-cont perf build (SHARDED_SYNC II.10) | 4 | 18.36 | 0.6426 | 0.988 |
| program set above | scalar-clock serial N=1 | d38d057 (X1) | 6 | 1989 | 3.807 | 0.9828 |
| program set above | scalar-clock sharded N=16 | f551ca0 (X1b) | 6 | -23.26 | 0.8166 | 0.9871 |
| program set above | vector-clock | d38d057 (X1) | 6 | 2913 | 4.595 | 0.9737 |
| program set above | vector-clock | f551ca0 (X1b) | 6 | 5993 | 5.47 | 0.9239 |
| all complete (id,mode) rows | scalar-clock sharded N=16 | f551ca0 (X1b) | 4706 | 3.741 | 1.32 | 0.7057 |
| suite P1 | scalar-clock sharded N=16 | f551ca0 (X1b) | 400 | 2.041 | 1.672 | 0.3115 |
| suite P3 | scalar-clock sharded N=16 | f551ca0 (X1b) | 60 | 2.109 | 6.471 | 0.05504 |
| suite P4 | scalar-clock sharded N=16 | f551ca0 (X1b) | 28 | 2.184 | 0.6983 | 0.8853 |
| suite P5 | scalar-clock sharded N=16 | f551ca0 (X1b) | 33 | 1.725 | 9420 | 0.008587 |
| suite P6 | scalar-clock sharded N=16 | f551ca0 (X1b) | 34 | 4.742 | 1.719 | 0.9873 |
| suite P7 | scalar-clock sharded N=16 | f551ca0 (X1b) | 12 | 537.8 | 1.616 | 0.6027 |
| suite P9 | scalar-clock sharded N=16 | f551ca0 (X1b) | 9 | 473.5 | 0.9792 | 0.883 |
| suite PI | scalar-clock sharded N=16 | f551ca0 (X1b) | 4130 | 1.453 | 5.42 | 0.03331 |
| all complete (id,mode) rows | vector-clock | f551ca0 (X1b) | 4704 | 11.92 | 6.256 | 0.91 |
| suite P1 | vector-clock | f551ca0 (X1b) | 400 | 0.7736 | 29.24 | 0.5347 |
| suite P3 | vector-clock | f551ca0 (X1b) | 60 | 1.902 | 29.61 | 0.4745 |
| suite P4 | vector-clock | f551ca0 (X1b) | 28 | -0.8294 | 48.73 | 0.4948 |
| suite P5 | vector-clock | f551ca0 (X1b) | 33 | 1.867 | 3.827e+04 | 0.06535 |
| suite P6 | vector-clock | f551ca0 (X1b) | 34 | -158.6 | 29.89 | 0.9438 |
| suite P7 | vector-clock | f551ca0 (X1b) | 11 | 2066 | 6.132 | 0.8912 |
| suite P9 | vector-clock | f551ca0 (X1b) | 8 | 1537 | 5.88 | 0.9159 |
| suite PI | vector-clock | f551ca0 (X1b) | 4130 | 0.9801 | 46.56 | 0.1128 |
| all complete (id,mode) rows | scalar-clock serial N=1 | d38d057 (X1) | 4705 | 5.066 | 4.082 | 0.9243 |
| suite P1 | scalar-clock serial N=1 | d38d057 (X1) | 400 | 0.8671 | 6.32 | 0.7534 |
| suite P3 | scalar-clock serial N=1 | d38d057 (X1) | 60 | 0.9924 | 6.109 | 0.4222 |
| suite P4 | scalar-clock serial N=1 | d38d057 (X1) | 28 | 1.413 | 2.023 | 0.787 |
| suite P5 | scalar-clock serial N=1 | d38d057 (X1) | 33 | 1.028 | -7890 | 0.05879 |
| suite P6 | scalar-clock serial N=1 | d38d057 (X1) | 34 | -46.69 | 10.41 | 0.9532 |
| suite P7 | scalar-clock serial N=1 | d38d057 (X1) | 12 | 1441 | 3.246 | 0.903 |
| suite P9 | scalar-clock serial N=1 | d38d057 (X1) | 8 | 707.4 | 4.445 | 0.9346 |
| suite PI | scalar-clock serial N=1 | d38d057 (X1) | 4130 | 0.9237 | 13.6 | 0.1532 |
| all complete (id,mode) rows | vector-clock | d38d057 (X1) | 4705 | 9.833 | 5.077 | 0.9112 |
| suite P1 | vector-clock | d38d057 (X1) | 400 | 0.2405 | 22.19 | 0.4764 |
| suite P3 | vector-clock | d38d057 (X1) | 60 | 0.7015 | 29.9 | 0.4438 |
| suite P4 | vector-clock | d38d057 (X1) | 28 | -1.196 | 33.96 | 0.6212 |
| suite P5 | vector-clock | d38d057 (X1) | 33 | 1.057 | -6709 | 0.02534 |
| suite P6 | vector-clock | d38d057 (X1) | 34 | -177.9 | 32.83 | 0.943 |
| suite P7 | vector-clock | d38d057 (X1) | 12 | 1700 | 3.99 | 0.9479 |
| suite P9 | vector-clock | d38d057 (X1) | 8 | 939.7 | 5.521 | 0.9608 |
| suite PI | vector-clock | d38d057 (X1) | 4130 | 0.4605 | 53.98 | 0.1114 |

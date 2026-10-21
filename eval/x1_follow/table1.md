| program / configuration | host (CPU) | tool wall (s) | native wall (s) | wall / native | memory (MB) | events | µs / event | kernels | |
|---|---|---|---|---|---|---|---|---|---|
| P7 heartwall-cuda — X1 vector-clock (1 rep, final-24h-vc) | c58 (9115) | 35,574.7 | 0.883 | 40,288× | 6,194 peak (summed VmRSS) | 8,071,484,636 (X1 `events=`) | 4.407 | 104 |  |
| P7 heartwall-cuda — X1 scalar-clock (1 rep, final-24h-sc) | c52 (9115) | 32,057.2 | 0.778 | 41,205× | 6,186 peak (summed VmRSS) | 8,071,484,636 (X1 `events=`) | 3.972 | 104 |  |
| P7 heartwall-cuda — collector-only, -n 1 | c66 (8124P) | 2,345.1 | 0.768 | 3,053× | 986 MaxRSS (VmHWM) | 8,071,484,636 (drained, this run) | 0.2905 | 104 |  |
| P7 heartwall-cuda — collector-only, default workers | c61 (8124P) | 626.4 | 0.818 | 766× | 1,009 MaxRSS (VmHWM) | 8,071,484,636 (drained, this run) | 0.07761 | 104 |  |
| P9 knn-cuda — X1 vector-clock (1 rep, final-24h-vc) | c62 (8124P) | 57,215.7 | 13.549 | 4,223× | 22,198 peak (summed VmRSS) | 11,144,912,500 (X1 `events=`) | 5.134 | 300 |  |
| P9 knn-cuda — X1 scalar-clock (1 rep, final-24h-sc) | c66 (8124P) | 44,762.4 | 13.744 | 3,257× | 20,558 peak (summed VmRSS) | 11,144,912,500 (X1 `events=`) | 4.016 | 300 |  |
| P9 knn-cuda — collector-only, -n 1 | c61 (8124P) | 3,304.1 | 13.542 | 244× | 1,009 MaxRSS (VmHWM) | 11,144,912,500 (drained, this run) | 0.2965 | 300 |  |
| P9 knn-cuda — collector-only, default workers | c66 (8124P) | 835.0 | 13.692 | 61× | 1,048 MaxRSS (VmHWM) | 11,144,912,500 (drained, this run) | 0.07492 | 300 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 vector-clock (3 reps, final) | c51 (9115) | 0.868 | 0.217 | 4× | 851 peak (summed VmRSS) | 1,019 (X1 `events=`) | 851.8 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 scalar-clock (3 reps, final) | c51 (9115) | 0.868 | 0.217 | 4× | 848 peak (summed VmRSS) | 1,019 (X1 `events=`) | 851.8 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — collector-only, -n 1 | c66 (8124P) | 1.477 | 0.267 | 6× | 848 MaxRSS (VmHWM) | 1,019 (drained, this run) | 1449 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — collector-only, default workers | c66 (8124P) | 1.060 | 0.217 | 5× | 850 MaxRSS (VmHWM) | 1,023 (drained, this run) | 1036 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 configuration, scalar-clock, same host | c66 (8124P) | 1.094 | 0.217 | 5× | 849 MaxRSS (VmHWM) | 1,005 (drained, this run) | 1089 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 configuration, vector-clock, same host | c66 (8124P) | 1.197 | 0.216 | 6× | 852 MaxRSS (VmHWM) | 1,019 (drained, this run) | 1175 | 13 |  |
| P6 interkernel-global_readwrit — X1 vector-clock (3 reps, final) | c60 (8124P) | 5.578 | 0.719 | 8× | 856 peak (summed VmRSS) | 1,000,004 (X1 `events=`) | 5.578 | 2 |  |
| P6 interkernel-global_readwrit — X1 scalar-clock (3 reps, final) | c60 (8124P) | 4.926 | 0.719 | 7× | 855 peak (summed VmRSS) | 1,000,004 (X1 `events=`) | 4.926 | 2 |  |
| P6 interkernel-global_readwrit — collector-only, -n 1 | c66 (8124P) | 3.871 | 0.768 | 5× | 856 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 3.871 | 2 |  |
| P6 interkernel-global_readwrit — collector-only, default workers | c66 (8124P) | 3.553 | 0.718 | 5× | 861 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 3.553 | 2 |  |
| P6 interkernel-global_readwrit — X1 configuration, scalar-clock, same host | c66 (8124P) | 4.907 | 0.717 | 7× | 857 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 4.907 | 2 |  |
| P6 interkernel-global_readwrit — X1 configuration, vector-clock, same host | c66 (8124P) | 5.256 | 0.768 | 7× | 858 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 5.256 | 2 |  |

# iGUARD on the P7 HeCBench overhead set (14 apps)

Never run before (BASELINES.md footnote 3). Job 321654 (c56, c61, c62, c63; RTX 4060 Ti), script
`eval/baselines/setup/p_iguard_p7.sh`, runner `eval/baselines/run_iguard.py --pset P7`, 3 reps, cap
min(max(10x native, 120), 1200) s. Rows: `eval/results/baselines-iguard-shardp7_{0..3}_4.csv`. Every
rep of an app gave the same verdict. cuVein columns are from `eval/results/baselines-cuvein.csv`
(scalar-clock rep 1; its caps were escalated to 5,400 s and 86,400 s for the slow apps).

| app | iGUARD | reports (line) | iGUARD wall / native (s) | cuVein SC verdict (line) | cuVein SC wall (s) |
|---|---|---|---|---|---|
| backprop | CLEAN | | 3.1 / 0.39 | CLEAN | 5.3 |
| bezier-surface | CLEAN | | 27.6 / 20.3 | CLEAN | 306 |
| bfs | RACE | 13: bfs.cu:31, 40, 41, 59, 60 (Missing gpufence, Missing warpsync) | 25.4 / 1.59 | RACE (bfs.cu:38, 40, 41) | 1,507 |
| bitonic-sort | CLEAN | | 78.8 / 32.1 | CLEAN | 3,707 |
| hotspot | CLEAN | | 0.87 / 0.81 | CLEAN | 109 |
| lavaMD | CLEAN | | 3.0 / 0.49 | CLEAN | 1,502 |
| nbody | CLEAN | | 22.0 / 12.3 | CLEAN | 8,015 |
| pathfinder | RACE | 1: main.cu:114 (Missing gpufence) | 55.2 / 1.66 | RACE (main.cu:114) | 19,225 |
| srad | CLEAN | | 27.2 / 0.52 | CLEAN | 2,537 |
| haversine | TIMEOUT (120 s) | | — / 2.82 | CLEAN | 6,932 |
| heartwall | TIMEOUT (120 s) | | — / 1.44 | RACE (kernel.h:1979, 1980) | 32,057 |
| mandelbrot | TIMEOUT (120 s) | | — / 2.53 | CLEAN | 2,422 |
| particlefilter | TIMEOUT (120 s) | | — / 1.42 | RACE, partial (OOM after 3 kernels) | 5,791 |
| stencil1d | TIMEOUT (120 s) | | — / 5.14 | TIMEOUT (86,400 s) | — |

On the 9 apps iGUARD finished, its verdict agrees with cuVein's on every one (2 RACE at the same or
nearby lines, 7 CLEAN). The 5 timeouts got only the derived 120 s cap; cuVein's caps on the same
apps went to 5,400 s and 86,400 s. A longer-cap iGUARD pass on those 5 has not been run.

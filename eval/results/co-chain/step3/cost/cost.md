## Re-time on A5's node class (c26, Xeon Silver 4110) and on c25 (EPYC 7302P): closure off vs on, same 47 recordings

analysis_s of rep 1, mode collector-only (one value per program), sum over the sample; factor = sum(on) / sum(off); per-program max = largest on/off over the programs of the group with off >= 0.2 s.

| host | pass | group | n | sum off (s) | sum on (s) | factor | per-program max | sum chain_s (s) |
|---|---|---|---|---|---|---|---|---|
| c26 | 1 | P1 | 8 | 8.01 | 7.57 | 0.9446 | 1.283 | 0.018 |
| c26 | 1 | P3 | 4 | 3.81 | 5.41 | 1.4196 | 2.237 | 0.007 |
| c26 | 1 | P4 | 8 | 28.17 | 28.30 | 1.0047 | 1.182 | 0.055 |
| c26 | 1 | P5 | 4 | 1.84 | 1.92 | 1.0425 | 1.267 | 0.000 |
| c26 | 1 | P6 | 4 | 1.54 | 1.66 | 1.0731 | 1.092 | 0.002 |
| c26 | 1 | PI | 12 | 5.76 | 6.31 | 1.0955 | 1.398 | 0.000 |
| c26 | 1 | HeCBench | 7 | 18.66 | 18.83 | 1.0093 | 1.101 | 0.133 |
| c26 | 1 | all | 47 | 67.78 | 69.98 | 1.0324 | 2.237 | 0.215 |
| c26 | 2 | P1 | 8 | 7.05 | 7.68 | 1.0891 | 1.254 | 0.018 |
| c26 | 2 | P3 | 4 | 3.82 | 3.98 | 1.0438 | 1.193 | 0.006 |
| c26 | 2 | P4 | 8 | 27.93 | 29.22 | 1.0462 | 1.534 | 0.055 |
| c26 | 2 | P5 | 4 | 2.05 | 2.06 | 1.0020 | 1.196 | 0.000 |
| c26 | 2 | P6 | 4 | 1.75 | 1.92 | 1.0949 | 1.180 | 0.002 |
| c26 | 2 | PI | 12 | 5.82 | 6.21 | 1.0675 | 1.213 | 0.000 |
| c26 | 2 | HeCBench | 7 | 18.40 | 18.66 | 1.0142 | 1.061 | 0.137 |
| c26 | 2 | all | 47 | 66.81 | 69.72 | 1.0436 | 1.534 | 0.218 |
| c25 | 1 | P1 | 8 | 5.85 | 6.12 | 1.0458 | 1.089 | 0.010 |
| c25 | 1 | P3 | 4 | 3.09 | 3.29 | 1.0643 | 1.169 | 0.004 |
| c25 | 1 | P4 | 8 | 22.51 | 22.79 | 1.0125 | 1.109 | 0.038 |
| c25 | 1 | P5 | 4 | 1.50 | 1.58 | 1.0581 | 1.128 | 0.000 |
| c25 | 1 | P6 | 4 | 1.37 | 1.40 | 1.0182 | 1.053 | 0.002 |
| c25 | 1 | PI | 12 | 5.01 | 5.46 | 1.0894 | 1.517 | 0.000 |
| c25 | 1 | HeCBench | 7 | 14.84 | 15.59 | 1.0510 | 1.401 | 0.088 |
| c25 | 1 | all | 47 | 54.17 | 56.23 | 1.0381 | 1.517 | 0.142 |
| c25 | 2 | P1 | 8 | 5.98 | 6.87 | 1.1491 | 1.915 | 0.011 |
| c25 | 2 | P3 | 4 | 3.30 | 3.39 | 1.0276 | 1.091 | 0.004 |
| c25 | 2 | P4 | 8 | 22.96 | 23.50 | 1.0233 | 1.367 | 0.038 |
| c25 | 2 | P5 | 4 | 1.61 | 1.65 | 1.0229 | 1.168 | 0.000 |
| c25 | 2 | P6 | 4 | 1.39 | 1.54 | 1.1050 | 1.194 | 0.002 |
| c25 | 2 | PI | 12 | 5.24 | 5.17 | 0.9868 | 1.110 | 0.000 |
| c25 | 2 | HeCBench | 7 | 15.17 | 15.29 | 1.0082 | 1.106 | 0.088 |
| c25 | 2 | all | 47 | 55.65 | 57.41 | 1.0315 | 1.915 | 0.143 |

c26, pass 2, sum of analysis_s over the 47 programs: vc 135.40 s, sc 67.03 s, co-off 66.81 s, co-on 69.72 s

c25, pass 2, sum of analysis_s over the 47 programs: vc 108.40 s, sc 54.48 s, co-off 55.65 s, co-on 57.41 s

Host effect (co-off, pass 2, all 47): c26 / c25 = 1.201

## Cost by the rule of CAP_84600.md section 3: geometric means (n programs)

| suite | mode | run only (n) | verdict step (n) | end-to-end (n) | run only, same programs as end-to-end |
|---|---|---|---|---|---|
| Indigo3 | vector-clock | 10.421 (400) | 3.607 (400) | 14.662 (400) | 10.421 (400) |
| Indigo3 | scalar-clock | 8.730 (400) | 3.384 (400) | 12.409 (400) | 8.730 (400) |
| Indigo3 | CO (C1) | 6.470 (400) | 3.296 (400) | 10.005 (400) | 6.470 (400) |
| Indigo3 | CO+chain, step-2 analysis_s as measured (EPYC) | 6.470 (400) | 2.781 (400) | 9.489 (400) | 6.470 (400) |
| Indigo3 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.470 (400) | 3.590 (400) | 10.313 (400) | 6.470 (400) |
| Indigo3 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.470 (400) | 4.134 (400) | 10.880 (400) | 6.470 (400) |
| Indigo3 | CO+chain, lower bound (= C1 analysis_s) | 6.470 (400) | 3.296 (400) | 10.005 (400) | 6.470 (400) |
| Indigo 1.3 | vector-clock | 6.932 (4130) | 2.349 (4130) | 9.405 (4130) | 6.932 (4130) |
| Indigo 1.3 | scalar-clock | 6.805 (4130) | 2.075 (4130) | 8.984 (4130) | 6.805 (4130) |
| Indigo 1.3 | CO (C1) | 5.458 (4130) | 1.999 (4130) | 7.521 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, step-2 analysis_s as measured (EPYC) | 5.458 (4130) | 1.783 (4130) | 7.327 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.458 (4130) | 2.134 (4130) | 7.660 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.458 (4130) | 2.426 (4130) | 7.957 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, lower bound (= C1 analysis_s) | 5.458 (4130) | 1.999 (4130) | 7.521 (4130) | 5.458 (4130) |
| ECL | vector-clock | 10.149 (60) | 3.477 (60) | 13.897 (60) | 10.149 (60) |
| ECL | scalar-clock | 8.820 (60) | 3.274 (60) | 12.351 (60) | 8.820 (60) |
| ECL | CO (C1) | 6.006 (60) | 3.147 (60) | 9.348 (60) | 6.006 (60) |
| ECL | CO+chain, step-2 analysis_s as measured (EPYC) | 6.006 (60) | 2.704 (60) | 8.952 (60) | 6.006 (60) |
| ECL | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.006 (60) | 3.285 (60) | 9.492 (60) | 6.006 (60) |
| ECL | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.006 (60) | 3.754 (60) | 9.979 (60) | 6.006 (60) |
| ECL | CO+chain, lower bound (= C1 analysis_s) | 6.006 (60) | 3.147 (60) | 9.348 (60) | 6.006 (60) |
| ScoR apps | vector-clock | 28.849 (28) | 15.380 (28) | 55.364 (28) | 28.849 (28) |
| ScoR apps | scalar-clock | 9.360 (28) | 8.079 (28) | 20.115 (28) | 9.360 (28) |
| ScoR apps | CO (C1) | 6.834 (28) | 7.941 (28) | 17.293 (28) | 6.834 (28) |
| ScoR apps | CO+chain, step-2 analysis_s as measured (EPYC) | 6.834 (28) | 6.327 (28) | 15.255 (28) | 6.834 (28) |
| ScoR apps | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.834 (28) | 8.308 (28) | 17.703 (28) | 6.834 (28) |
| ScoR apps | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.834 (28) | 12.179 (28) | 21.942 (28) | 6.834 (28) |
| ScoR apps | CO+chain, lower bound (= C1 analysis_s) | 6.834 (28) | 7.941 (28) | 17.293 (28) | 6.834 (28) |
| ScoR litmus | vector-clock | 8.845 (33) | 1.909 (33) | 10.839 (33) | 8.845 (33) |
| ScoR litmus | scalar-clock | 7.361 (33) | 1.639 (33) | 9.060 (33) | 7.361 (33) |
| ScoR litmus | CO (C1) | 5.637 (33) | 1.702 (33) | 7.406 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, step-2 analysis_s as measured (EPYC) | 5.637 (33) | 1.560 (33) | 7.276 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.637 (33) | 1.705 (33) | 7.409 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.637 (33) | 2.035 (33) | 7.748 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, lower bound (= C1 analysis_s) | 5.637 (33) | 1.702 (33) | 7.406 (33) | 5.637 (33) |
| cuHadron | vector-clock | 12.993 (34) | 0.819 (34) | 15.096 (34) | 12.993 (34) |
| cuHadron | scalar-clock | 10.752 (34) | 0.709 (34) | 12.180 (34) | 10.752 (34) |
| cuHadron | CO (C1) | 7.124 (34) | 0.722 (34) | 8.530 (34) | 7.124 (34) |
| cuHadron | CO+chain, step-2 analysis_s as measured (EPYC) | 7.124 (34) | 0.646 (34) | 8.419 (34) | 7.124 (34) |
| cuHadron | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 7.124 (34) | 0.790 (34) | 8.658 (34) | 7.124 (34) |
| cuHadron | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 7.124 (34) | 0.852 (34) | 8.772 (34) | 7.124 (34) |
| cuHadron | CO+chain, lower bound (= C1 analysis_s) | 7.124 (34) | 0.722 (34) | 8.530 (34) | 7.124 (34) |
| HeCBench other 14 | vector-clock | 1411.497 (12) | 0.663 (12) | 1421.126 (12) | 1411.497 (12) |
| HeCBench other 14 | scalar-clock | 246.314 (13) | 0.752 (13) | 249.588 (13) | 246.314 (13) |
| HeCBench other 14 | CO (C1) | 99.881 (14) | 0.626 (14) | 103.355 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, step-2 analysis_s as measured (EPYC) | 99.881 (14) | 0.519 (14) | 103.406 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 99.881 (14) | 0.635 (14) | 103.402 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 99.881 (14) | 0.664 (14) | 103.559 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, lower bound (= C1 analysis_s) | 99.881 (14) | 0.626 (14) | 103.355 (14) | 99.881 (14) |
| HeCBench SC 10 | vector-clock | 1694.363 (8) | 3.405 (8) | 1708.741 (8) | 1694.363 (8) |
| HeCBench SC 10 | scalar-clock | 512.634 (9) | 2.609 (9) | 520.908 (9) | 512.634 (9) |
| HeCBench SC 10 | CO (C1) | 150.442 (10) | 2.439 (10) | 159.563 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, step-2 analysis_s as measured (EPYC) | 150.442 (10) | 1.862 (10) | 156.697 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 150.442 (10) | 2.473 (10) | 159.683 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 150.442 (10) | 2.588 (10) | 160.081 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, lower bound (= C1 analysis_s) | 150.442 (10) | 2.439 (10) | 159.563 (10) | 150.442 (10) |
| HeCBench (P7+P9) | vector-clock | 1518.485 (20) | 1.275 (20) | 1529.854 (20) | 1518.485 (20) |
| HeCBench (P7+P9) | scalar-clock | 332.438 (22) | 1.251 (22) | 337.243 (22) | 332.438 (22) |
| HeCBench (P7+P9) | CO (C1) | 118.468 (24) | 1.103 (24) | 123.855 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, step-2 analysis_s as measured (EPYC) | 118.468 (24) | 0.884 (24) | 122.959 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 118.468 (24) | 1.119 (24) | 123.927 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 118.468 (24) | 1.171 (24) | 124.166 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, lower bound (= C1 analysis_s) | 118.468 (24) | 1.103 (24) | 123.855 (24) | 118.468 (24) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | vector-clock | 7.320 (4685) | 2.454 (4685) | 9.966 (4685) | 7.320 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | scalar-clock | 7.015 (4685) | 2.173 (4685) | 9.339 (4685) | 7.015 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO (C1) | 5.564 (4685) | 2.098 (4685) | 7.773 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, step-2 analysis_s as measured (EPYC) | 5.564 (4685) | 1.860 (4685) | 7.550 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.564 (4685) | 2.242 (4685) | 7.923 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.564 (4685) | 2.555 (4685) | 8.251 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, lower bound (= C1 analysis_s) | 5.564 (4685) | 2.098 (4685) | 7.773 (4685) | 5.564 (4685) |
| All incl. HeCBench (unrestricted) | vector-clock | 7.488 (4705) | 2.447 (4705) | 10.182 (4705) | 7.488 (4705) |
| All incl. HeCBench (unrestricted) | scalar-clock | 7.142 (4707) | 2.168 (4707) | 9.497 (4707) | 7.142 (4707) |
| All incl. HeCBench (unrestricted) | CO (C1) | 5.652 (4709) | 2.091 (4709) | 7.884 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, step-2 analysis_s as measured (EPYC) | 5.652 (4709) | 1.853 (4709) | 7.658 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.652 (4709) | 2.234 (4709) | 8.035 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.652 (4709) | 2.545 (4709) | 8.365 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, lower bound (= C1 analysis_s) | 5.652 (4709) | 2.091 (4709) | 7.884 (4709) | 5.652 (4709) |

Check against CAP_84600.md section 3 (All, 4,685-set; run only / verdict step / end-to-end):
  - vector-clock: CAP (7.32, 2.454, 9.966), recomputed (7.32, 2.454, 9.966) (n 4685/4685/4685) -> equal
  - scalar-clock: CAP (7.015, 2.173, 9.339), recomputed (7.015, 2.173, 9.339) (n 4685/4685/4685) -> equal
  - collector-only: CAP (5.564, 2.098, 7.773), recomputed (5.564, 2.098, 7.773) (n 4685/4685/4685) -> equal
  - collector alone over all finished programs (the paper's 5.7x): 5.652 (n 4709)

Chain rows whose run wall differs from C1's row of the same program: 0 of 4709 (run-only cost of the chain mode is C1's by construction when 0).

## analysis_s of the verdict step per suite: median, max, and the closure's share

Step 2 (chain, EPYC nodes) next to the A5 reference (C1, A5's node class). share = sum(chain_s) / sum(analysis_s) and the median of chain_s / analysis_s per program.

| suite | n | chain median (s) | chain max (s) | C1 ref median (s) | C1 ref max (s) | sum chain (s) | sum C1 ref (s) | sum chain_s (s) | share (sums) | share (median) |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0.607 | 1.512 | 0.784 | 1.630 | 269.5 | 312.5 | 0.53 | 0.0020 | 0.0018 |
| Indigo 1.3 (PI) | 4130 | 0.383 | 1.410 | 0.408 | 1.782 | 1669.1 | 1839.6 | 0.04 | 0.0000 | 0.0000 |
| ECL (P3) | 60 | 0.608 | 1.292 | 0.728 | 1.366 | 39.9 | 44.9 | 0.07 | 0.0017 | 0.0018 |
| ScoR apps (P4) | 28 | 1.236 | 9.072 | 1.382 | 14.529 | 68.4 | 96.2 | 0.05 | 0.0007 | 0.0000 |
| ScoR litmus (P5) | 33 | 0.352 | 0.816 | 0.361 | 0.465 | 11.7 | 12.4 | 0.00 | 0.0000 | 0.0000 |
| cuHadron (P6) | 34 | 0.314 | 0.443 | 0.356 | 0.488 | 10.9 | 12.1 | 0.01 | 0.0010 | 0.0000 |
| HeCBench other 14 (P7) | 14 | 0.678 | 5.991 | 0.792 | 11.836 | 22.2 | 31.4 | 1.46 | 0.0658 | 0.0092 |
| HeCBench SC 10 (P9) | 10 | 2.052 | 7.860 | 2.166 | 11.310 | 27.8 | 34.9 | 1.31 | 0.0474 | 0.0095 |
| HeCBench (P7+P9) | 24 | 0.944 | 7.860 | 1.153 | 11.836 | 50.0 | 66.3 | 2.77 | 0.0556 | 0.0095 |
| all but HeCBench | 4685 | 0.393 | 9.072 | 0.417 | 14.529 | 2069.5 | 2317.7 | 0.70 | 0.0003 | 0.0000 |
| all | 4709 | 0.394 | 9.072 | 0.418 | 14.529 | 2119.4 | 2384.0 | 3.48 | 0.0016 | 0.0000 |

Largest chain analysis_s: 9.072 s (P4-reduction-norace-large), its chain_s 0.000 s.
Largest chain_s: P7-stencil1d-cuda 0.631 s of 0.663 s; P9-atomicCAS-cuda 0.613 s of 7.860 s; P7-heartwall-cuda 0.434 s of 5.991 s; P9-dxtc2-cuda 0.339 s of 2.829 s; P7-srad-cuda 0.333 s of 2.281 s

Analysis nodes of step 2 (anode= in the notes, one per program): {'c5': 2360, 'c45': 2349}

Step-2 chain analysis_s over the A5 reference analysis_s, by analysis node (sums over the programs of that node; node class from the README: c5 EPYC 9115, c45 EPYC 7302P, c4/c58/c2 EPYC 9115, c25/c39 EPYC 7302P, c62 EPYC 8124P, c14/c26 Xeon 4110): c45 1.081 (ref sum 1154 s), c5 0.708 (ref sum 1229 s)

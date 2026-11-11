**P1 Indigo3**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 400 | 400 | 400 |
| programs reported | 200 | 200 | 200 |
| labelled races detected | 200 of 200 | 200 of 200 | 200 of 200 |
| labelled race-free reported | 0 of 200 | 0 of 200 | 0 of 200 |
| report pairs | 1522 | 1522 | 1522 |
| derived / rescued chain pairs | 6671 / 2292 | 6671 / 2292 | 14601 / 3737 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 459.0 | 220.5 | 219.3 |

New race-free reported (after, not before): none.

**P3 ECL**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 60 | 60 | 60 |
| programs reported | 16 | 16 | 16 |
| labelled races detected | 0 of 0 | 0 of 0 | 0 of 0 |
| labelled race-free reported | 16 of 60 | 16 of 60 | 16 of 60 |
| report pairs | 44 | 44 | 44 |
| derived / rescued chain pairs | 148 / 213 | 148 / 213 | 1577 / 540 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 66.4 | 31.4 | 32.9 |

New race-free reported (after, not before): none.

**P4 ScoR applications**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 28 | 28 | 28 |
| programs reported | 22 | 22 | 22 |
| labelled races detected | 14 of 14 | 14 of 14 | 14 of 14 |
| labelled race-free reported | 8 of 14 | 8 of 14 | 8 of 14 |
| report pairs | 172 | 172 | 259 |
| derived / rescued chain pairs | 5590 / 316 | 5590 / 316 | 8559 / 1051 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 140.3 | 61.9 | 62.8 |

New race-free reported (after, not before): none.

**P5 ScoR litmus + canary**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 33 | 33 | 33 |
| programs reported | 5 | 5 | 5 |
| labelled races detected | 4 of 19 | 4 of 19 | 4 of 19 |
| labelled race-free reported | 1 of 14 | 1 of 14 | 1 of 14 |
| report pairs | 6 | 6 | 14 |
| derived / rescued chain pairs | 4 / 0 | 4 / 0 | 125 / 36 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 18.6 | 9.7 | 10.2 |

New race-free reported (after, not before): none.

**P6 cuHadron (analysed 34 of 50)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 34 | 34 | 34 |
| programs reported | 8 | 8 | 8 |
| labelled races detected | 7 of 13 | 7 of 13 | 7 of 13 |
| labelled race-free reported | 1 of 21 | 1 of 21 | 1 of 21 |
| report pairs | 103 | 103 | 103 |
| derived / rescued chain pairs | 159 / 2 | 159 / 2 | 159 / 2 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 17.9 | 9.4 | 10.4 |

New race-free reported (after, not before): none.

**P7 HeCBench (other 14)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 14 | 14 | 14 |
| programs reported | 7 | 7 | 7 |
| labelled races detected | 0 of 0 | 0 of 0 | 0 of 0 |
| labelled race-free reported | 0 of 0 | 0 of 0 | 0 of 0 |
| report pairs | 73 | 73 | 73 |
| derived / rescued chain pairs | 56098 / 9383 | 56098 / 9383 | 56098 / 9383 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 41.3 | 19.3 | 20.7 |

New race-free reported (after, not before): none.

**P9 HeCBench (SC's 10)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 10 | 10 | 10 |
| programs reported | 5 | 5 | 5 |
| labelled races detected | 3 of 3 | 3 of 3 | 3 of 3 |
| labelled race-free reported | 2 of 7 | 2 of 7 | 2 of 7 |
| report pairs | 140 | 140 | 140 |
| derived / rescued chain pairs | 68191 / 12173 | 68191 / 12173 | 68191 / 12174 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 49.3 | 21.5 | 26.2 |

New race-free reported (after, not before): none.

**PI Indigo 1.3 inputs (1,862 racy / 1,260 race-free labelled, 1,008 unlabelled)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 4130 | 4130 | 4130 |
| programs reported | 2668 | 2668 | 2668 |
| labelled races detected | 1738 of 1862 | 1738 of 1862 | 1738 of 1862 |
| labelled race-free reported | 224 of 1260 | 224 of 1260 | 224 of 1260 |
| report pairs | 14166 | 14166 | 14169 |
| derived / rescued chain pairs | 5604 / 818 | 5604 / 818 | 6924 / 978 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 2763.5 | 1394.6 | 1526.0 |

New race-free reported (after, not before): none.

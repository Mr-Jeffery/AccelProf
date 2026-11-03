## Program level: CO-R against C1's collector-only run (separate recordings), per suite

Programs whose verdict differs (RACE / CLEAN / TIMEOUT / ERROR as recorded), with the cause of the program's differing pairs (the causes of the CO-R-only pairs when CO-R is Race, of the C1-only pairs when C1 is Race; a program can have several).

| suite | programs in both | same verdict | C1 Clean → CO-R Race | C1 Race → CO-R Clean | other differences | of the first: extended edge | rescue | other | none found (no differing pair) |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PI | 4130 | 4104 | 26 | 0 | 0 | 25 | 0 | 1 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P4 | 28 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P5 | 33 | 32 | 1 | 0 | 0 | 1 | 0 | 1 | 0 |
| P6 | 34 | 33 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| P7 | 14 | 13 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| P9 | 10 | 9 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 4679 | 28 | 0 | 2 | 26 | 1 | 2 | 0 |

## Pair pass: recordings whose first pair-level analysis hit the 3,600 s cap

- `P7-srad-cuda`: first pass rule on `analysis-timeout` (3603.8 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (8401.4 s), rule off `ok` (8294.1 s)
- `P9-tridiagonal-cuda`: first pass rule on `analysis-timeout` (3603.7 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (8814.3 s), rule off `ok` (8848.8 s)
- `P9-mr-cuda`: first pass rule on `analysis-timeout` (3603.7 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (6897.4 s), rule off `ok` (6904.4 s)

## S1 pairs not in (a)

| program | space | pc lo | pc hi | reason |
|---|---|---|---|---|

(a) and S1 hold the same pairs: both difference lists above are empty.

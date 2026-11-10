# Table 4 recomputed (unit: run; Indigo 1.3 rows per code)

layers: [('co-chain-b merged-s1', 4725), ('P9 id missing', 'atomicCAS'), ('P9 id missing', 'atomicCAS'), ('P9 id missing', 'atomicCAS'), ('P9 id missing', 'atomicCAS'), ('P9 id missing', 'atomicCAS'), ('P9 id missing', 'dxtc2'), ('P9 id missing', 'dxtc2'), ('P9 id missing', 'dxtc2'), ('P9 id missing', 'dxtc2'), ('P9 id missing', 'dxtc2'), ('P9 id missing', 'knn'), ('P9 id missing', 'knn'), ('P9 id missing', 'knn'), ('P9 id missing', 'knn'), ('P9 id missing', 'knn'), ('P9 id missing', 'tridiagonal'), ('P9 id missing', 'tridiagonal'), ('P9 id missing', 'tridiagonal'), ('P9 id missing', 'tridiagonal'), ('P9 id missing', 'tridiagonal'), ('P9 id missing', 'expdist'), ('P9 id missing', 'expdist'), ('P9 id missing', 'expdist'), ('P9 id missing', 'expdist'), ('P9 id missing', 'expdist'), ('P9 id missing', 'overlap'), ('P9 id missing', 'overlap'), ('P9 id missing', 'overlap'), ('P9 id missing', 'overlap'), ('P9 id missing', 'overlap'), ('P9 id missing', 'fpc'), ('P9 id missing', 'fpc'), ('P9 id missing', 'fpc'), ('P9 id missing', 'fpc'), ('P9 id missing', 'fpc'), ('P9 id missing', 'gpp'), ('P9 id missing', 'gpp'), ('P9 id missing', 'gpp'), ('P9 id missing', 'gpp'), ('P9 id missing', 'gpp'), ('P9 id missing', 'crs'), ('P9 id missing', 'crs'), ('P9 id missing', 'crs'), ('P9 id missing', 'crs'), ('P9 id missing', 'crs'), ('P9 id missing', 'mr'), ('P9 id missing', 'mr'), ('P9 id missing', 'mr'), ('P9 id missing', 'mr'), ('P9 id missing', 'mr')]

| suite | kind | labels (racy/free/unl) | racecheck | iGUARD | HiRace | SuperCollider | collector-only | scalar-clock | vector-clock |
|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | recall | 200/200 | 4/200 | 196/200 | - | - | 200/200 | 200/200 | 200/200 |
| | FP | | 0/200 | 100/200 | - | - | 0/200 | 0/200 | 0/200 |
| Indigo 1.3 | recall | 266/180 | 40/266 | 258/266 | 266/266 | 42/45 | 266/266 | 266/266 | 266/266 |
| | FP | | 0/180 | 108/180 | 0/180 | 0/44 | 32/180 | 0/180 | 0/180 |
| Indigo 1.3, SC's 99 | recall | 45/44 | 3/45 | 42/45 | 45/45 | 42/45 | 45/45 | 45/45 | 45/45 |
| | FP | | 0/44 | 24/44 | 0/44 | 0/44 | 4/44 | 0/44 | 0/44 |
| ScoR applications | recall | 14/14 | 0/13, 1 TO/ERR | 12/14 | - | - | 14/14 | 14/14 | 14/14 |
| | FP | | 0/14 | 7/14 | - | - | 8/14 | 2/14 | 2/14 |
| cuHadron (20 in scope) | recall | 14/22 | 4/6, 16 TO/ERR | 1/6, 16 TO/ERR | - | 9/13, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR |
| | FP | | 0/14 | 4/14 | - | 0/21 | 0/14 | 0/14 | 0/14 |
| HeCBench, SC's 10 | recall | 5/5 | 0/3, 2 TO/ERR | 0/3, 2 TO/ERR | - | 5/5 | 4/5 | 2/3, 2 TO/ERR | 2/3, 2 TO/ERR |
| | FP | | 0/5 | 3/5 | - | 0/5 | 1/5 | 0/5 | 0/5 |
| All (P1+PI+P4+P6@in) | recall | | 48/485, 17 TO/ERR | 467/486, 16 TO/ERR | 266/266 | 51/58, 16 TO/ERR | 486/486, 16 TO/ERR | 486/486, 16 TO/ERR | 486/486, 16 TO/ERR |
| | FP | | 0/408 | 219/408 | 0/180 | 0/65 | 40/408 | 2/408 | 2/408 |

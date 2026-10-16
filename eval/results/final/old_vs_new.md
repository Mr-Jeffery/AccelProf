| suite | mode | old (2026-09-22) RACE / CLEAN / TIMEOUT / ERROR | new (X1) RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |
|---|---|---|---|---|
| P1 | vector-clock | 182 / 199 / 19 / 0 | 200 / 200 / 0 / 0 | 19 |
| P1 | scalar-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P3 | vector-clock | 14 / 44 / 2 / 0 | 16 / 44 / 0 / 0 | 2 |
| P3 | scalar-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P4 | vector-clock | 14 / 4 / 10 / 0 | 16 / 12 / 0 / 0 | 13 |
| P4 | scalar-clock | 20 / 8 / 0 / 0 | 16 / 12 / 0 / 0 | 4 |
| P5 | vector-clock | 19 / 14 / 0 / 0 | 4 / 29 / 0 / 0 | 17 |
| P5 | scalar-clock | 18 / 15 / 0 / 0 | 2 / 31 / 0 / 0 | 16 |
| P6 | vector-clock | 5 / 24 / 4 / 17 | 8 / 26 / 0 / 16 | 6 |
| P6 | scalar-clock | 5 / 25 / 3 / 17 | 8 / 26 / 0 / 16 | 5 |
| P7 | vector-clock | 2 / 1 / 11 / 0 | 4 / 9 / 1 / 0 | 10 |
| P7 | scalar-clock | 2 / 2 / 10 / 0 | 4 / 9 / 1 / 0 | 9 |
| P9 | vector-clock | 1 / 1 / 8 / 0 | 2 / 6 / 2 / 0 | 7 |
| P9 | scalar-clock | 1 / 3 / 6 / 0 | 2 / 6 / 2 / 0 | 5 |
| PI | vector-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |
| PI | scalar-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |

| suite | mode | old → new | (id, mode) |
|---|---|---|---|
| P1 | vector-clock | TIMEOUT → CLEAN | 1 |
| P1 | vector-clock | TIMEOUT → RACE | 18 |
| P3 | vector-clock | TIMEOUT → RACE | 2 |
| P4 | scalar-clock | RACE → CLEAN | 4 |
| P4 | vector-clock | RACE → CLEAN | 3 |
| P4 | vector-clock | TIMEOUT → CLEAN | 5 |
| P4 | vector-clock | TIMEOUT → RACE | 5 |
| P5 | scalar-clock | RACE → CLEAN | 16 |
| P5 | vector-clock | CLEAN → RACE | 1 |
| P5 | vector-clock | RACE → CLEAN | 16 |
| P6 | scalar-clock | CLEAN → RACE | 1 |
| P6 | scalar-clock | ERROR → CLEAN | 1 |
| P6 | scalar-clock | TIMEOUT → CLEAN | 1 |
| P6 | scalar-clock | TIMEOUT → RACE | 2 |
| P6 | vector-clock | CLEAN → RACE | 1 |
| P6 | vector-clock | ERROR → CLEAN | 1 |
| P6 | vector-clock | TIMEOUT → CLEAN | 2 |
| P6 | vector-clock | TIMEOUT → RACE | 2 |
| P7 | scalar-clock | TIMEOUT → CLEAN | 7 |
| P7 | scalar-clock | TIMEOUT → RACE | 2 |
| P7 | vector-clock | TIMEOUT → CLEAN | 8 |
| P7 | vector-clock | TIMEOUT → RACE | 2 |
| P9 | scalar-clock | RACE → CLEAN | 1 |
| P9 | scalar-clock | TIMEOUT → CLEAN | 2 |
| P9 | scalar-clock | TIMEOUT → RACE | 2 |
| P9 | vector-clock | RACE → CLEAN | 1 |
| P9 | vector-clock | TIMEOUT → CLEAN | 4 |
| P9 | vector-clock | TIMEOUT → RACE | 2 |

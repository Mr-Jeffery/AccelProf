Keys in the plan (a recording and a confirm file): 9412; analysed without error: 9412; failed: 0; not yet run: 0.
Keys present in more than one shard output (deduplicated by (program, mode)): 48; duplicates whose pair bins / counts / confirm check differ from the first copy: 0.

### Table 1 -- barrier-ordered pairs by suite, mode and CFG bin

| suite | mode | confirm files re-analysed | files with >=1 pair | pairs | loop-carried | partial participation | early exit | branch arm | other | pairs also seen in another class |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 400 | 32 | 56 | 8 | 0 | 0 | 0 | 48 | 4 |
| P1 | scalar-clock | 400 | 32 | 56 | 8 | 0 | 0 | 0 | 48 | 4 |
| P3 | vector-clock | 60 | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| P3 | scalar-clock | 60 | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| P4 | vector-clock | 28 | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| P4 | scalar-clock | 28 | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| P5 | vector-clock | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P5 | scalar-clock | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P6 | vector-clock | 34 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| P6 | scalar-clock | 34 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| P7 | vector-clock | 13 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| P7 | scalar-clock | 13 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| P9 | vector-clock | 8 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| P9 | scalar-clock | 8 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| PI | vector-clock | 4130 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| PI | scalar-clock | 4130 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| all | vector-clock | 4706 | 898 | 1021 | 599 | 200 | 140 | 17 | 65 | 4 |
| all | scalar-clock | 4706 | 898 | 1021 | 599 | 200 | 140 | 17 | 65 | 4 |

A pair is one (kernel, ancient pc, current pc, space class) over all launches of the recording; "also seen in another class" counts pairs that were barrier-ordered in one launch and in another hb_class in a different launch.

### Table 2 -- the same pair in the two modes

| suite | distinct pairs | in both modes | vector-clock only | scalar-clock only |
|---|---|---|---|---|
| P1 | 56 | 56 | 0 | 0 |
| P3 | 22 | 22 | 0 | 0 |
| P4 | 83 | 83 | 0 | 0 |
| P6 | 1 | 1 | 0 | 0 |
| P7 | 2 | 2 | 0 | 0 |
| P9 | 17 | 17 | 0 | 0 |
| PI | 840 | 840 | 0 | 0 |
| all | 1021 | 1021 | 0 | 0 |
### Table 3 -- what the bins contain

| suite | mode | partial: a WARPSYNC between | partial: a BAR with a count operand | partial: no full-block BAR between u and v | early exit | branch arm | branch arm: every barrier between is outside postdom(u) | other: no qualifying barrier between u and v | other: a barrier between, none of the tests fired |
|---|---|---|---|---|---|---|---|---|---|
| P1 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| P1 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| P3 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| P3 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| P4 | vector-clock | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P4 | scalar-clock | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P6 | vector-clock | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P6 | scalar-clock | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P9 | vector-clock | 0 | 0 | 0 | 0 | 17 | 4 | 0 | 0 |
| P9 | scalar-clock | 0 | 0 | 0 | 0 | 17 | 4 | 0 | 0 |
| PI | vector-clock | 140 | 0 | 0 | 140 | 0 | 0 | 0 | 0 |
| PI | scalar-clock | 140 | 0 | 0 | 140 | 0 | 0 | 0 | 0 |
| all | vector-clock | 200 | 0 | 0 | 140 | 17 | 4 | 64 | 1 |
| all | scalar-clock | 200 | 0 | 0 | 140 | 17 | 4 | 64 | 1 |

### Table 5 -- the pairs of the `other` bin: fields of their verdict records

| suite | mode | space | observed distance | R1 strength | warp-same-instruction | event candidate | edge rescued | race type | pairs |
|---|---|---|---|---|---|---|---|---|---|
| P1 | scalar-clock | shared | warp | none | False | False | False | RAW | 24 |
| P1 | scalar-clock | shared | warp | none | False | False | False | WAW | 24 |
| P1 | vector-clock | shared | warp | none | False | False | False | RAW | 24 |
| P1 | vector-clock | shared | warp | none | False | False | False | WAW | 24 |
| P3 | scalar-clock | shared | warp | none | False | False | False | RAW | 8 |
| P3 | scalar-clock | shared | warp | none | False | False | False | WAW | 8 |
| P3 | vector-clock | shared | warp | none | False | False | False | RAW | 8 |
| P3 | vector-clock | shared | warp | none | False | False | False | WAW | 8 |
| P6 | scalar-clock | shared | block | none | False | False | False | RAW | 1 |
| P6 | vector-clock | shared | block | none | False | False | False | RAW | 1 |


### Table 6 -- the partial / early-exit / branch-arm pairs: is u (v) inside a natural loop that contains a BAR? (pairs; the two modes have the same pairs)

| suite | bin | u in a barrier loop | v in a barrier loop | pairs |
|---|---|---|---|---|
| P4 | partial participation | False | False | 48 |
| P4 | partial participation | False | True | 12 |
| P9 | branch arm | False | True | 4 |
| P9 | branch arm | True | False | 13 |
| PI | early exit | False | False | 140 |
| PI | partial participation | False | True | 140 |

### Table 4 -- the re-analysis against the X1 confirm files

9412 files re-analysed; report ids identical to the confirm file's: 9412; SC-report count identical: 9412.

### Skipped at planning

| suite | mode | reason | keys |
|---|---|---|---|
| P6 | scalar-clock | no recording in the view | 16 |
| P6 | vector-clock | no recording in the view | 16 |
| P7 | scalar-clock | no recording in the view | 1 |
| P7 | vector-clock | no recording in the view | 1 |
| P9 | scalar-clock | no recording in the view | 2 |
| P9 | vector-clock | no recording in the view | 2 |

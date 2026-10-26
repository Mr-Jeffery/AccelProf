# M3: the JIT path (PTX-only binaries)

Branch `eval/jit-path` from `eval/final-tables` (d484e42). Unmerged. Numbers only.

**Question.** Does the profiler read the SASS the driver compiles at load time, and are the pc offsets of its
records the offsets of that SASS (the ones `nvdisasm` prints for the JIT cubin)?

**Answer on these two programs: yes, with one precondition, and with a limit on what the data separates.**
The precondition is that the PTX must be one the installed driver accepts. nvcc 13.4's PTX is not accepted by a
580 driver (Error 222, run 1 below); nvcc 13.0's PTX is. The limit is that here the JIT SASS is instruction-for-instruction
the AOT SASS, so every pc offset is valid in both; the data do not tell which of the two the profiler read.

## Setup

| item | value |
|---|---|
| node, GPU | c63, RTX 4060 Ti (sm_89), driver 580.82.07 (job 321720; runs 1 on c64, driver 580.95.05) |
| profiler | main checkout `/home/fzheng4/AccelProf`, cuVein f551ca0; `accelprof -t pc_dependency_analysis -n 1`, both modes, 3 reps each, full dump (`hb_dump` default) |
| profiler CUDA_HOME | `/usr/local/cuda-13.4` |
| programs | ScoR `race_interwarp_none-atom_waw` (P5 litmus, 1 block x 33 threads); P4 `reduction_norace`, small input (`NBLOCKS=30 NTHREADS=512`) |
| SASS build | `nvcc -gencode arch=compute_89,code=sm_89 -lineinfo --cudart shared` |
| PTX-only build | `nvcc -gencode arch=compute_89,code=compute_89 -lineinfo --cudart shared` |
| check of the PTX-only build | `cuobjdump -lelf`: no ELF; `-lptx`: `*.sm_89.ptx` only (both programs) |
| JIT cubin | the driver's compute cache (`CUDA_CACHE_PATH`, a fresh directory per run), the ELF cut out of the cache file, disassembled with `nvdisasm -c -poff` |

Script `eval/jit-path/m3_jit_path.py`, control `eval/jit-path/m3_control134.py`, job scripts `m3*.sh`.

## Run 1: nvcc 13.4 PTX on a 580 driver: fails

Jobs 321682 (c64, 580.95.05) and 321710 (c63, 580.82.07). The 13.4 PTX is `.version 9.4`.

| build | native run | under the profiler (6 runs) |
|---|---|---|
| litmus, PTX-only | rc 1, `Error 222: the provided PTX was compiled with an unsupported toolchain.` | rc 1 in 6 of 6, 0 kernel JSONs |
| reduction, PTX-only | rc 0 (the program does not check launch errors) | rc 0 in 6 of 6, 0 kernel JSONs |
| SASS builds | rc 0 | 12 of 12 runs have 1 kernel JSON |

The driver's compute cache holds no entry in either PTX-only case (`index` only). Results: `eval/results/jit-path/run-13.4-ptx-error222/`.

## Run 2: nvcc 13.0 PTX (`.version 9.0`): works

Job 321720 (`--build-cuda /usr/local/cuda-13.0`). Results: `eval/results/jit-path/run-13.0-final/m3_results.json`.

### Verdict, report count, pcs (12 runs per program: 2 builds x 2 modes x 3 reps)

| program | build | mode | runs | verdict | reports | report pcs | pcs in the dump | pcs in the dump that are not instruction offsets of the cubin |
|---|---|---|---|---|---|---|---|---|
| atom_waw | SASS | both | 6 | CLEAN | 0 | none | 6: 0, 96, 160, 176, 240, 256 | 0 |
| atom_waw | PTX-only | both | 6 | CLEAN | 0 | none | the same 6 | 0 |
| reduction | SASS | both | 6 | RACE | 1 (`global:0xab0-0x1690:WAW`) | 2736, 5776 | 73 | 0 |
| reduction | PTX-only | both | 6 | RACE | 1 (`global:0xab0-0x1690:WAW`) | 2736, 5776 | the same 73 | 0 |

- All 12 runs of each program give one identical (verdict, report ids, pcs) result; the dump pcs of the SASS and PTX-only runs are equal sets.
- For the PTX-only runs the pc check and the analysis (CFG, atomic-scope sidecar) use the JIT cubin; no run raised an analysis error.
- The JIT cubin captured inside each of the 12 profiled PTX-only runs is byte-identical to the one from the native run (12 of 12).
- X1b rows for the same ids (SASS builds, `eval/results/final-b/merged/baselines-cuvein.csv`): `P4-reduction-norace-small` RACE, 1 report, `global:0xab0-0x1690:WAW`, both modes; `P5-race_interwarp_none-atom_waw` CLEAN, 0 reports, both modes. Run 2 reproduces both.
- The litmus is CLEAN in all 12 runs (it is labelled RACE in the manifest); this is X1b's result too, not a JIT effect.

### SASS against the JIT cubin

`nvdisasm -c -poff`, per function, the sequence of (offset, instruction text):

| program | functions | identical | instructions in the JIT cubin |
|---|---|---|---|
| litmus | 1 | 1 | 32 |
| reduction | 20 | 20 | 4,488 |

Control, `eval/results/jit-path/run-13.0-final/m3_control134.json` (job 321736): the AOT cubins built by nvcc 13.4 (run 1's SASS builds) are also identical to the 13.0 PTX's JIT cubin in all 21 functions. The PTX-only dumps analysed against the 13.4 AOT cubins give the same verdicts, report counts and pcs as against the JIT cubin; 0 dump pcs fall outside the instruction offsets of either.

## What the data do and do not show

- Show: a PTX-only binary runs under the profiler once the driver accepts its PTX; the records' pcs are instruction offsets of the cubin the driver JIT-compiled; verdicts, report counts and report pcs equal the SASS build's.
- Do not show: that the profiler reads the JIT SASS rather than some other copy of identical SASS. Every comparison had identical SASS on both sides, so a layout difference that would separate the two cases did not occur. A test that separates them needs a PTX whose JIT output differs from the AOT output (a driver newer than the toolkit's ptxas, for example); none was run.
- Not run: nvcc 13.4 PTX on a driver that accepts it (c79 has 615.71.09 and was held by another job); other programs; other architectures.

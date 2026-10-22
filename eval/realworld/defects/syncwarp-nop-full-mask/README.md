# Defect: a `__syncwarp(mask)` on its converged fast path is recorded with sync_mask 0xffffffff

Found by the T21b Opus triage of `cccl-1` (fixed build STILL-REPORTED). Class (c) of T21c step 3: a detector defect, located in
the trace (the collector's syncwarp record), not in HbClock or the vector/scalar clocks. Runs below: **WSL triage build** (cuVein
f551ca0 runtime on Jeffery's laptop, RTX 4060 Laptop sm_89, CUDA 13.3), triage only, never scored.

## Input

`syncwarp_partial_mask.cu`: kernel `partial_mask<<<1,32>>>`: lanes 0..21 read `s[t]`, `__syncwarp(0x3fffff)`, write
`s[(t+1)%22]`, `__syncwarp(0x3fffff)`, read `s[t]`; lanes 22..31 skip the branch and stay alive until `if (t == 0) out[32] = t;`
(as the non-raking lanes of cub `BlockReduceRaking` do). Control kernel `full_mask`: the same accesses, all 32 lanes, `__syncwarp()`.

    source ~/curace-wsl/env.sh
    nvcc -arch=native -lineinfo --cudart shared -o swpm syncwarp_partial_mask.cu
    ~/curace-wsl/run-detector.sh $PWD/swpm $PWD/out

## Expected and actual verdicts

| kernel | expected | vector-clock (actual) | scalar-clock (actual) |
|---|---|---|---|
| `partial_mask` | race-free (every conflicting pair is separated by `__syncwarp(0x3fffff)` and both lanes are in the mask) | 2 RACE (DR, structural): `0x160 STS` vs `0x80 LDS` (WAR, tid 1/0), `0x1b0 LDS` vs `0x160 STS` (RAW); `tv_violation` TV-syncwarp-completion-order | 2 RACE, same pairs; same `tv_violation` |
| `full_mask` (control) | race-free | 0 RACE (2 barrier-ordered) | 0 RACE |

## Mechanism (SASS and code)

- ptxas lowers each `__syncwarp(0x3fffff)` to `UMOV UR6, 0x3fffff ; BRA.CONV UR6, skip ; CALL.REL.NOINC $__cuda_sm70_warpsync ; skip: NOP`
  (0x0090/0x00b0/0x00d0/0x00f0 and 0x0120/0x0170/0x0190/0x01a0 here); the helper holds the only `WARPSYNC R5` (0x0270). With lanes 0..21
  converged, `BRA.CONV` is taken and the `WARPSYNC` never executes.
- Compute Sanitizer's `SANITIZER_INSTRUCTION_SYNCWARP` callback (registered at `nv-compute/src/compute_sanitizer.cpp:309`) fires at the
  `NOP` (pc 0xf0, 0x1a0) with mask `0xffffffff`; `SyncwarpCallback` (`nv-compute/gpu_src/gpu_patch_pc_dependency.cu:253-258`) forwards that
  mask as the record's `sync_mask`. Trace: `syncwarp pc=0xf0 sync_mask=0xffffffff active=0x3fffff` (the full-mask control has the same
  NOP form with `active=0xffffffff`, which is correct).
- HbClock follows its specification on that record: `sw_expected` (`sanalyzer/src/tools/pc_dependency_analysis.cpp:999-1003`) = sync_mask
  minus exited lanes = 0xffffffff (lanes 22..31 are alive, parked at the reconvergence point), `on_syncwarp` (:1026-1040) opens an
  instance that lanes 22..31 never join, so no join happens; the W2 monitor (:1998-2006) then reports TV-syncwarp-completion-order when
  lane 0..21 issue the next record (pc 0x160). `python/hb_oracle.py` refuses the same trace (`ALIGNMENT FAILURE`).
- Confirmation: the dumped trace with `sync_mask` set to 0x3fffff (the value in UR6) replayed through `python/hb_oracle.py`: 0 races
  (`wsl_run.txt`). The same replay on the T21b `cccl-1` drivers: buggy 30 -> 3 races (exactly the oracle pair, pcs 0xf0/0x130/0x140 vs
  0x1d0), fixed 30 -> 0.

Precondition for the false report: the mask is partial, the lanes outside it are alive (not exited) when the group arrives, and the
group is converged (fast path). A partial mask whose other lanes have already exited is handled (the first version of this input, with
no code after the branch, gave 0 races).

`wsl_run.txt` is the WSL run's output summary (SASS, run-detector output, trace records, verdicts in both modes, the HbClock monitor
lines, the oracle replays).

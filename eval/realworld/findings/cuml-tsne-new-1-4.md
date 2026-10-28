# Finding cuml-tsne-new-1-4: `SummarizationKernel` reads a child's payload (`countd`, `posxd`, `posyd`) after the volatile `massd` flag with no acquire fence

Repository rapidsai/cuml, pinned commit `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Class **DR**, global memory, cross-thread (cross-block) message passing whose release side is complete and whose acquire side is missing. Formal under PTX; a stale-L1 read is possible in principle, not tested. **Not in the oracle.** Triage: `eval/realworld/candidates/triage/cuml-tsne-new-1.md`, group S2. The flag itself is group S1: SC, by design, no separate dossier.

## 1. The accesses (`cpp/src/tsne/barnes_hut_kernels.cuh` @ c7e7738b)

| role | line | statement | SASS (traced R2 build) |
|---|---|---|---|
| producer payload (cell k) | 406, 408, 409 (pre-pass); 467, 469, 470 (main loop) | `countd[k] = cnt; … posxd[k] = px * m; posyd[k] = py * m;` | `STG.E` 0xa70 / 0xb90 / 0xba0; 0x1b20 / 0x1c80 / 0x1c90 (2672/2960/2976; 6944/7296/7312) |
| producer release | 410 / 475, then 411 / 477 | `__threadfence(); massd[k] = cm;` (`massd` is `volatile`) | `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL` 0xbb0 / 0x1cb0, then `STG.E.STRONG.SYS` 0xbe0 / 0x1d20 |
| consumer flag read | 383 / 434 / 442 | `(mass[…] = massd[ch])` | `LDG.E.STRONG.SYS` 0x250 … / 0x1240 … / 0xe90 … |
| consumer payload read | 397, 401, 402 (pre-pass); 459, 462, 463 (main loop) | `cnt += countd[ch]` … `px += posxd[ch] * m; py += posyd[ch] * m;` | `LDG.E` (e.g. 0x620 / 0x650 / 0x660; 0x15b0 / 0x15e0 / 0x15f0) |

## 2. Thread pair and why nothing orders it

- **Pair.** Thread P (assigned cell k) writes `countd[k]`, `posxd[k]`, `posyd[k]` (L406–L409, plain). It then executes `__threadfence()` (L410) and the strong store `massd[k] = cm` (L411).
  - Fence followed by a strong write is a **release pattern** (PTX §8.7).
- **Consumer.** Thread C, possibly in another block (`grid = SMs × 1`, 768 threads), is assigned k's parent cell.
  - It reads `massd[k]` (L383, strong) ≥ 0. In the **same** loop iteration it reads `countd[k]` (L397) and `posxd[k]`/`posyd[k]` (L401/L402), all plain, with no fence in between.
  - A strong read is an **acquire pattern** only if a fence follows it before the dependent accesses. Here none does.
- **Result.** P's fence and C's flag read do not synchronize, P's payload stores do not happen-before C's payload loads, and the plain conflicting pair is a DR.
  - The main loop has the same shape (L434/L442 → L459–L463). One exception: where the flag was read in an earlier iteration and L475's fence intervenes, the pair is ordered.
- **Hardware angle** (not tested). The payload loads are `LDG.E`: weak and L1-cacheable on sm_89.
  - The consumer thread's `CCTL.IVALL` happens only at its own fences. Another warp on the same SM may have pulled the 128-byte line holding `posxd[k]` (with neighbouring cells' entries) into L1 after that.
  - A stale `posxd[k]` hit is therefore possible in principle. The flag read itself is `.STRONG.SYS`, which bypasses L1, so seeing a new flag does not refresh the payload line.
- **Reference code.** The reference `cannylab/bh.cu` declares the payload `volatile int* countd` and `volatile float4* posMassd` (L388–L390), all strong, so it has no DR. The cuML port made the payload plain and kept `massd` volatile.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`, `kernel_8.json` = `SummarizationKernel<int,float>`, grid 34 × 768)

- **Payload reports.** 39 RACE reports, DR, global, all in `other_reports.csv`:
  - pre-pass read vs pre-pass write: 12 (e.g. 1568 → 2960, L401 → L408);
  - pre-pass read vs main-loop write: 3;
  - pre-pass write vs main-loop read: 12 (e.g. 2672 → 5616, L406 → L459);
  - main-loop read vs main-loop write: 12 (e.g. 5552 → 7296, L462 → L469).
- **Flag reports.** 24 SC reports on the `massd` flag itself (strong vs strong; S1).
- **Racecheck.** Not applicable: global memory.

## 4. Reproducer (`eval/realworld/findings/repro/cuml-tsne-new-1-4/`)

- **`repro.cu`.** `SummarizationKernel` L351–L482, statements copied (some joined).
  - Trimmed: the five wait-free pre-passes L374–L418. They are an optimisation; the kept main loop L420–L481 summarises every cell left with `massd < 0`, which with the pre-passes removed is every cell. The main loop has the same publication.
  - Input: a full quadtree over 32×32 unit-mass bodies (341 cells), with `massd = -1` for cells as after `ClearKernel2`. Launched `<<<SMs, 768>>>`, 20 launches.
  - The host checks every cell's mass and count exactly and its centre of mass within 1e-3.
- **`repro_fixed.cu`.** `__threadfence()` at the top of the `if (j == 0)` summation block: the acquire after the flag reads, before the payload reads.
- **`repro_perturb.cu`.** `__nanosleep(20000)` before the payload stores of odd cells. Neighbouring cells' lines are then more likely to sit in consumers' L1 when the odd cells publish.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings): 1 `MEMBAR` in `repro`, 2 in `repro_fixed`. Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/cpp/src/tsne/barnes_hut_kernels.cuh   (c7e7738b)
+++ b/cpp/src/tsne/barnes_hut_kernels.cuh
@@ -387,2 +387,3 @@
         // all children are ready
+        __threadfence();  // acquire: order the payload reads after the massd flag reads
         cm       = 0.0f;
@@ -447,2 +448,3 @@
     if (j == 0) {
+      __threadfence();  // acquire
       // all children are ready
```

An alternative is to restore the reference's `volatile` on `countd`/`posxd`/`posyd`, which makes every payload access strong.

## 6. Already known?

- **cuML.** The issue and PR searches as for cuml-tsne-new-1 found nothing on `SummarizationKernel`. #2565 fixed tree-build allocation races; #3816 is an unexplained hang.
- **Elsewhere.** HeCBench's bh fix `40e3c96b` touched the force kernel. The ECL original uses volatile payloads.
- **Commits.** The commit that made the payload plain was not identified.
- **Verdict.** **New**, as far as checked.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "The producer fences, and the consumer cannot read the payload before seeing the flag. The control dependency orders it, and it has worked for years."
- **Answer.**
  - PTX gives control dependencies no ordering, and the consumer has no acquire. So this is a data race under the model, and the plain loads may legally be satisfied from a stale L1 line.
  - The release side is correct. Only the reader's fence is missing: the same shape T21 corpus note 3 lists for `cccl-3`, `cmssw-1` and `raft-1`.
  - We claim a formal race. A wrong output is not expected natively.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck (n/a: global memory) | not applicable |

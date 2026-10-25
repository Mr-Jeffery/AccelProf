# T21c step 3: triage of the reports T21b handed over

This file triages `eval/results/realworld/other_reports.csv`: the 3,277 cuVein reports in T21b's recall runs
that no oracle pair, registered residual or both-builds pair explains (`triage_queue.md` §E). T21c's brief
asks for "every report T21b handed over" to be triaged into its four classes. The 18 candidates are
T21c's other half, on `study/realworld-candidates`, and are not covered here. Done 2026-10-25, with CPU reads
only and no GPU job.

**Method.**
- **Grouping.** The rows were grouped by (target, sorted innermost-frame line pair) into 164 groups. Every row is in
  exactly one group (`harness/t21c_triage_prep.py`).
- **Triage.** Six fresh-context Opus triagers worked in parallel, each on a share of the targets. For every group a
  triager read:
  - both source sites at the pinned commits, with their inlined frames;
  - the SASS around the pcs (`dots/`);
  - the vector-clock `hb_races` records (`a_tid`, `b_tid`, `dist`, `a2_uncertain`).
  A group whose members differ in mechanism is split into sub-groups.
- **Coordinator review** (the session that wrote this file):
  - coverage: 164 of 164 groups and 3,277 of 3,277 rows, with no row count off;
  - one labelling convention across the triagers (§6);
  - spot checks, listed in §8.

Classes, as T21c step 3 defines them:
- **(a)** a race under PTX §8.7.1, DR or SC;
- **(b)** ordered by a mechanism the detector does not model;
- **(c)** a detector or harness defect;
- **(d)** cannot decide.

## Result

| class | rows | of which the target's own oracle race |
|---|---|---|
| (a) DR | 1,716 | 668 |
| (a) SC | 1,312 | 142 |
| (b) | 2 | 0 |
| (c) | 247 | 0 |
| (d) | 0 | 0 |
| **all** | **3,277** | **810** |

Per target (rows):

| target | (a) DR | (a) SC | (b) | (c) | total |
|---|---|---|---|---|---|
| hecbench-hungarian-1 | 915 | 1,104 | | | 2,019 |
| llamacpp-5 | 512 | | | | 512 |
| cccl-3 | 66 | | | 156 | 222 |
| lit-shoc-1 | | 160 | | | 160 |
| raft-1 | 45 | | | 91 | 136 |
| hecbench-dxtc2-1 | 98 | | | | 98 |
| kokkos-6 | 48 | | | | 48 |
| cccl-4 | | 36 | | | 36 |
| cmssw-1 | 6 | 12 | | | 18 |
| kokkos-5 | 8 | | 2 | | 10 |
| hecbench-morphology-1 | 8 | | | | 8 |
| ginkgo-5 | 6 | | | | 6 |
| lit-exllamav3-1 | 4 | | | | 4 |

## 1. 810 rows are the targets' own oracle races, on pairs `recall_pairs.json` does not register

These are not new races. Each oracle's `buggy_expected` text, or its `fixed` reason, names more access pairs
than `recall_pairs.json` registers. The scorer matched the registered pair (DETECTED, DETECTED-AS-DR or
RESIDUAL-AS-EXPECTED, as scored), and every other pair of the same race was filed as "other".
Registering the named chains would take these rows out of the queue; no recall outcome changes.

| target | rows | what they are |
|---|---|---|
| llamacpp-5 | 512 | the oracle's hazard (1): CUB `BlockLoad` TempStorage reused by the second Load with no barrier (ssm-scan.cu L69-70, seen through `block_exchange.cuh:524/537`); `recall_pairs.json` lists only the smemB/smemC hazard |
| hecbench-hungarian-1, buggy | 130 | warp-synchronous `volatile` min reductions with no `__syncwarp` (rows L145-149, cols L185-190, `min_warp_reduce` L456-461): adjacent-step RAW, cross-step WAR, intra-step WAR; the oracle text names these lines, only some are registered |
| hecbench-hungarian-1, fixed | 36 | the intra-step steps of the residual the fixed reason names (L150-154, L192-200, L468-476); only L146 is registered |
| hecbench-dxtc2-1 | 98 | the `loadColorBlock` chains the oracle names: the `sums[]` XOR butterfly (L71-74), the covariance fill and tree reduction with the `__syncthreads` at L95/L106 commented out, `dps` L170 vs L131, the colors scatter (L161-163 vs L178); lanes 0-15 of warp 0 |
| cmssw-1 | 18 | the oracle bug (L22 store vs the last block's L179 RMW) and the registered residual against the earlier store L22 or L66 |
| hecbench-morphology-1 | 8 | the reverse-scan pair L98 the oracle names (cross-warp and intra-warp) |
| ginkgo-5 | 6 | the write-write half of the oracle's lost update on the bit-packed word (L154 vs L154) |
| raft-1 | 2 | the registered residual L322 vs the fixed build's L786, registered under the buggy numbering L776 |

## 2. 2,218 rows are races outside the oracles (class (a))

These are triage verdicts, not findings. T21c steps 4 and 5 require a dossier and a fresh-context verifier
before a race outside the oracles is counted. No dossier has been written yet.

| mechanism | target | rows | class | in both builds |
|---|---|---|---|---|
| same-value writes of plain shared/managed flags (`repeat`, `s_repeat_kernel`, `repeat_kernel`, `s_found`, `s_goto_5`) and of `v_cover_row`/`v_cover_column` by many threads in one barrier interval (step_2, step_4) | hungarian-1 | 927 | 651 DR, 276 SC | yes |
| step_4: `volatile` (`.STRONG.SYS`) load of `cover_row`/`cover_column` vs another thread's store in the same interval | hungarian-1 | 698 | SC | yes |
| step_4: different-value WAW `column_of_prime_at_row[l] = c` by two threads whose zeros share row l | hungarian-1 | 198 | DR | yes |
| step_5a/5b: writes of `row_of_green_at_column` / `row_of_star_at_column` where two augmenting paths join | hungarian-1 | 16 | DR | yes |
| step_2: the cover-claim protocol, a plain pre-check load or plain reset vs another thread's `atomicExch` | hungarian-1 | 14 | DR | yes |
| warp-synchronous tail of `reduce<T,256>` on `volatile` shared `sdata` (scan_kernel.h L126-131; the source's own comment says the section "would also need __sync calls if warp synchronous execution were not assumed") | lit-shoc-1 | 160 | SC | yes |
| last-block counter idiom: non-last blocks read or atomically update `Counter` fields; the last block rewrites them after its `atomicInc`/`atomic_fetch_add` with no acquire fence after it | cccl-3 66, raft-1 43, kokkos-5 4 | 113 | DR | yes |
| width-8 intra-warp reduction from warp 0: `__syncwarp` with 8-lane masks (0xff, 0xff00, ...) while lanes read other groups' slots (ReduceScan L351/L374) | kokkos-6 | 24 | DR | yes, unchanged by the fix |
| warp-synchronous tree step of `scalar_intra_warp_reduction`, width 32 (FunctorAnalysis L636) | kokkos-6 | 20 | DR | yes |
| decoupled look-back: relaxed tile-descriptor publish vs relaxed poll (single_pass_scan_operators.cuh:708/722), morally strong and unordered by design; no fix needed | cccl-4 | 36 | SC | yes |
| same-value `*global_flags = 0` by every thread of the last block | kokkos-5 4, kokkos-6 4 | 8 | DR | yes |
| same-value WAW: all 32 lanes store `max_red[warp_id]` (routing.cu L634; the upstream fix leaves it) | lit-exllamav3-1 | 4 | DR | yes |

The 113 counter-idiom rows depend on REVIEW.md item 2. Under strict PTX they are (a). If Jeffery takes the
"fence + counter" idiom as a hand-off, they move to (b). It is the same question as cccl-3's, cmssw-1's and
raft-1's scored residuals.

## 3. 247 rows are false reports (class (c)): one detector defect

**Emulated 64-bit shared `atomicAdd`.** On sm_89, ptxas lowers a 64-bit shared-memory `atomicAdd` to an `LDS.64`
followed by an `ATOMS.CAST.SPIN.64` retry loop. cuVein pairs the plain `LDS.64` with other threads' CAS. In the
source and the PTX it is one atomic, so nothing races.
- cccl-3 #06: 156 rows, the block histogram at agent_topk.cuh:818 (fixed :820).
- raft-1 #06: 91 rows, `histogram_smem` L255/L297. Some of these pcs are attributed to L291, but their address
  places them at the L297 `atomicAdd`.

It is the class already seen in P9 expdist (float/double, 4 reports). Minimal failing inputs, not run because
this pass used no GPU, are in `triage_other/cccl-3.md` (6 lines) and `triage_other/raft-1.md` (a 64-thread
`atomicAdd(&shared_u64, 1)`). Defect candidate: treat the emulation loop's initial load as part of the RMW.

## 4. 2 rows are ordered by a mechanism cuVein does not model (class (b))

kokkos-5 #02 and #05:
- Another block's relaxed `atomic_fetch_add` on `global_flags` is in the RMW chain that the last block's own
  RMW reads.
- A barrier then orders the last block's `*global_flags = 0`.
- Under PTX that is causality order through observation order. cuVein orders only through fenced
  release/acquire patterns, so this is a model gap, with a minimal input in `triage_other/kokkos-5.md`.

Medium confidence: the triager recalled the PTX causality-order clause from memory, so check it against the PTX
ISA text before scoring.

## 5. Harness and scoring findings (none changes a class)

1. **Registration gap** (§1): 810 rows are pairs of oracle races that `recall_pairs.json` does not register.
2. **`rw_score.py` (about L231) applies the fixed build's residual window (fixed L146 ±2) to buggy rows by line
   number.** So hungarian-1 buggy pairs at L144-148 count as explained by a different statement and never reach
   the queue, and the queue is incomplete there. Not fixed, not re-scored.
3. **`race_type` comes from the pc-edge verdict, not from `hb_races`.** hungarian-1 #66 is labelled RAW, and all
   197 of its records are WAR.
4. **Line attribution is off at a few pcs:**
   - hungarian-1 step_5a pc 0x120 is attributed to L416 (fixed L426); its operands show the L412 (L422) pre-loop
     store.
   - raft-1 #06, as in §3.
   - dxtc2 #26: an `LDS.128` attributed to L104 whose source read is L110 → L56.
5. **llamacpp-5 metadata:** `cuda_home` in the attribution and `meta.json` says cuda-13.3, but the build used nvcc
   13.4.92 (`cmake-configure.txt`, `ldd`), and the frames point into 13.4's CUB.
6. **Thread ids:** scalar-clock kernel JSONs keep no `hb_races`, so thread ids come from the vector-clock records
   only. The scalar-clock rows are the same pc pairs.
7. **Grouping artefact:** the line-pair key spans both builds, so hungarian-1 #40 merged buggy and fixed code.
   It is split into 40a and 40b.

## 6. Labels

- **`volatile` shared accesses are class SC** (the oracles' convention, D20 option (i)); cuVein reports them as DR,
  because sm_89 SASS has no `.STRONG` for them. That covers hungarian-1 #01-#37 (the buggy build's reductions take
  `volatile data*`; the fixed build dropped `volatile`) and lit-shoc-1 (`volatile T* sdata`). lit-shoc-1's
  triager wrote DR, which is relabelled here.
- **llamacpp-5 #01 is relabelled from (c) "harness scoring data" to (a) DR** (the oracle race, §1), like dxtc2's
  and morphology's unregistered pairs.
- The triagers' labels are kept in `orig_class` / `orig_race_class`.

## 7. Other observations

- **Possible out-of-bounds read in hungarian-1:** `min_reduce_kernel2` gets 128 bytes of dynamic shared memory,
  while `min_warp_reduce<32>` reads up to `sdata[47]` (main.cu:618, L457). This is from the source only; memcheck
  was not run.

## 8. What remains unverified

- No minimal failing input (§3, §4) was run.
- No dossier (T21c step 4), verifier (step 5) or "already known?" search for the §2 races.
- REVIEW.md item 2 decides the class of 113 rows (§2).
- The kokkos-5 (b) rests on a recalled PTX clause.
- raft-1 #05/#09 (filter_cnt) are medium confidence, because a later last-block `atomicAdd` could order them in
  some runs. The per-address atomic order in the traces would settle it.
- §5.2's hidden buggy rows are not triaged, because they are not in the queue.
- **Coordinator spot checks:**
  - lit-shoc-1 `scan_kernel.h` L81-L131 at the pinned commit;
  - the dxtc2 and morphology oracles' `buggy_expected` text against their `recall_pairs.json` entries;
  - the `volatile` declarations in hungarian-1 (both builds), dxtc2 and shoc.

  Every other group rests on its triager's write-up.

## Files

- `eval/results/realworld/other_reports_triage.csv`: one line per group or sub-group, with class, race_class,
  relation (oracle/other), mechanism, confidence, same_in_fixed, summary and the triager's original labels.
- `eval/results/realworld/other_reports_groups.csv`: the 164 groups.
- `eval/results/realworld/other_reports_rowgroups.csv`: row index of `other_reports.csv` → group.
- `eval/realworld/triage_other/<target>.md`: the per-group write-ups (accesses with file:line, tid pair, what
  orders them or fails to, class, fix or failing input). hungarian-1 is in two parts.
- `eval/realworld/harness/t21c_triage_prep.py` (grouping) and `t21c_triage_merge.py` (merge and labels).

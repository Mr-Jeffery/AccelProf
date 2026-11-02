# T23: R3's location gates over the closure of `same_loc` (`eval/R3_CLOSURE.md`)

Branch `fix/r3-same-loc-closure` (worktree `/home/fzheng4/wt-t23`), cut from `cuVein`
**afccba7de26de6474bb4e2dfcba372a7d226505b** ("Merge eval/final-rtraw (X4): the rtraw case study").
`cuVein` was still at afccba7 when the branch was cut (checked with `git rev-parse HEAD` in
`/home/fzheng4/AccelProf` immediately before `git worktree add`). Unmerged; Jeffery merges. Python
only (`python/sync_dominance.py`, tests, tooling, `design/proof/hb_proof.tex`); no `sanalyzer/`,
`nv-compute/` or `hb_oracle.py` change. Legend as in CLAUDE.md A4: **proved-in-effect** = an
invariant checked over the stated recordings, **tested** = a specific result asserted,
**unverified** = said so.

## 0. Result

* R3's gates (`_before_acquire`, both branches of `_past_release`) now ask "do these two atomic pcs
  touch one location?" of the **connected components** of `same_loc` (a union-find computed once per
  kernel in `attach_trace`), not of the pairs of observed atomic edges. The closure only adds pairs
  and every use is a decline, so it withholds certificates and grants none that were not granted
  before (**argued from the code**, `HBGraph.same_location` docstring; §3).
* The test of step 1 fails on afccba7's code (7 of 7 cases) and passes after the change (**tested**,
  §2). The green set that runs without a GPU: 200 passed + 7 new failing before, 209 passed after, 0
  failed; the 150 tests that need a GPU or `nvcc` are skipped in both and were **not run**.
* Re-score (§4), pair-level, no re-recording: **3 recordings change**, all in X4's `final-rtraw`
  store: in the 2 scalar-clock recordings (c58 run 20 and run 38) the pair 0x140/0x340 moves
  **ORDERED -> SC**; in the 1 vector-clock recording (c58 run 3) the verdict stays SC and only
  `hb_chain` is withdrawn. **No verdict moves** in the T20 parity store (65 programs x 2 modes, 636 scanned kernels: the 8
  flagged kernels analyzed twice, and 633 of the 636 in an all-kernels check), in
  X2's two stores (16 + 16 flagged kernels), or in X1's main store (32 flagged kernels; 9,398
  (program, mode) tasks scanned). X1's merged CSV through `make_tables.py`: the regenerated tables are
  byte-identical to the committed ones and, with no row moved, identical before and after.
* X1's 24 h vector-clock store, left open on 10-18 (BeeGFS was unmounted after the shutdown), was
  scanned on 10-20 once BeeGFS was back: 9 of its 11 programs have a `vector-clock` kernel directory
  and none can move (§4); **0 moved**.
* Not done, listed in §7: the GPU halves of the green set, a compile of the `.tex` paragraph.

## 1. The defect, in the code

`analyze()` builds `same_loc` from the trace's dependency edges: `frozenset((cur, anc))` for every
edge whose two pcs are atomic. R3's three gates then asked `frozenset((a, b)) in same_loc`. An edge
joins an access to the last earlier access of its address, so the pairs depend on the order of the
records. X4's schedule C (`eval/FINAL_RTRAW.md` section 6: block 0's winning CAS is recorded before
block 1's unlock) gives the edges 0xb0->0x230, 0x230->0x230, 0x230->0x1b0, 0x1b0->0x330. The unlock
0x330 is joined to 0x1b0 and to no CAS, so `_past_release(0x330, 0x340)` (landing on a non-CAS RMW:
"a CAS on its location?") answered no, and R3 certified the racy pair read 0x140 / write 0x340 with the
chain [0x1b0, 0x330]. In vector-clock mode `hb_races` already vetoed the chain (verdict SC); in
scalar-clock mode nothing did.

`hb_oracle.py` does **not** share the rule: its only uses of `sd` are the fence tables
(`gate_table`), scopes and `AlignmentError` (grep of `attach_trace`, `.chain(`, `.ordered(`,
`same_loc`, `release_points`, `_past_release`, `_before_acquire` finds none). So there was nothing to
mirror and no `HbClock` change (A4's invariant is untouched).

## 2. Step 1 and 2: the failing test, then the change

Test data (`python/testdata/r3_closure/`, README with provenance and sha256): X4's own files, copied
not re-recorded: `scalar_clock_c58_run20.json`
(`eval/results/final-rtraw/scor-scalar-clock/c58/run20/kernel_0.json`, sha256 ecb46fa5...),
`vector_clock_c58_run3.json` (`.../scor-recorded/c58/run3/kernel_0.json`, 66a288fc...), and the CFG
`race_interblock_none-lock_rtraw.sm_89.dot` (BeeGFS `final-rtraw/scor-scalar-clock/c58/cfg/`,
byte-identical to the `scor-recorded` one, ca6d2a97..., copied by SLURM job 314781). Both dumps carry
`hb_events` and `hb_sync_pass` / `hb_rmw_points`, so both verdict paths exist.

`test_r3_landing_closure_on_the_a2_inverted_rtraw` (`python/test_sync_dominance.py`): 3 dumps (the
scalar-clock recording; the vector-clock recording; that vector dump with the HbClock keys removed, i.e.
read as scalar-clock) x 2 paths (aggregates, and `CUVEIN_PREFER_RECORDS=1`) = 6 cases. Each asserts
that the one verdict for the pair {0x140, 0x340} is `SC` (volatile data: strong under the default
policy; `RACE` where volatile is weak, as in the existing tests) **and** `hb_chain is None`. Plus
`test_r3_location_classes_are_transitive` (`test_instance_gate.py`).

| run | revision | result |
|---|---|---|
| job 314784 (c12), the 7 new tests only | worktree at **8ec3455** (the commit that adds only tests and data) | **7 failed**: the 4 scalar-clock cases fail on the verdict (`ORDERED via chain ['0x1b0', '0x330']`); the 2 vector-clock cases fail only on the chain assertion (the verdict is already `SC`, class `sc`, chain still `['0x1b0','0x330']`); the unit test fails with `AttributeError: no same_location` |
| job 314793 (c58), green set on an `git archive` of 8ec3455 | 8ec3455 | 7 failed, **200 passed**, 150 skipped |
| job 314794 (c78), same set | **78323f9** (the change) | **209 passed** (200 + the 7 + 2 synthetic ones), 150 skipped, 0 failed |

The vector-clock cases are not a failing verdict on afccba7 (X4 said so: `hb_races` vetoes), they are a
failing certificate: the test asserts the certificate is withdrawn, not only that the veto hides it.

The change (`python/sync_dominance.py`, commit 78323f9; +43/-5 lines):

* `HBGraph._location_classes(pairs)`: union-find over the pcs the pairs join; `attach_trace` calls it
  once and stores `_loc_class`.
* `HBGraph.same_location(a, b, gate=None)`: `class(a) == class(b)`. The three sites call it,
  `same_location` is the last conjunct of each so the recorded firing is the one that made the gate
  true. `$CUVEIN_R3_LOC_CLOSURE=0` restores the edge-pair rule (ablation, as the other R3 knobs).
* Additive diagnostics, no effect on a verdict: `ordered()` returns `loc_closure`
  (`[(gate, pc, pc)]`, the gate firings that only the closure decided); `analyze()` copies it to the
  verdict as `r3_loc_closure` **only when non-empty** (a verdict the closure never touched is
  byte-identical to afccba7's).
* Two hand-built tests in `test_instance_gate.py`: X4's schedule C as a two-arm CFG (the closure
  declines at gate `landing`; with the knob off the chain `[0x1b0, 0x330]` is certified) and a control
  that the ordinary lock hand-off is still certified with no closure pair consulted.

The green set here is **not** CLAUDE.md A4's: `p_t23_test.sh` runs on `normal` (no GPU), on a
`git archive` of the revision with a copy of ScoR's stored artifacts (33 microbenchmark artifact
directories, copied from the main checkout at 14:31 on 10-18) and an `nvcc` stub, because some `normal`
nodes have no `nvcc` and the tests turn that into an error instead of a skip (job 314787 on c13: 32
`FileNotFoundError: nvcc` errors, not a regression). The 150 skips are 114 + 30 + 2 + 2 + 1 + 1 on-demand GPU builds
(`test_coherent_ldst`, `test_hb_substitutions`, `test_cp_async`, `test_barrier_exit`, gate_held,
write_before_lock, cuHadron intersubwarp). The ScoR corpus tests ran on the stored artifacts,
including `test_hb_clock_matches_specification` and `test_offline_barrier_pass_matches_oracle`.

## 3. Why the re-score can be limited to flagged kernels (and the check of that)

Every query a gate makes names a CAS pc (`_before_acquire`: a CAS `c` and `rel`; `_past_release`: a
CAS `c` and the landing, or the CAS landing and `r`). `same_location` differs from the edge-pair test
only on a pair the closure adds. So a kernel's verdicts can change only if the closure adds a pair
that names a CAS pc, which needs a class of at least 3 pcs. `t23_closure.py scan` computes that from
the kernel JSON's `edges` and the CFG's opcodes with `analyze()`'s own alignment and `same_loc` rules.
Kernels with no such pair are unchanged by construction (**argued from the code**); the scan also skips
a program whose dots contain no atomic opcode or no `.CAS` opcode (a text test, a superset of the
exact one). `diff` analyzes the flagged kernels twice (`$CUVEIN_R3_LOC_CLOSURE=0` and default) in one
process and compares the verdict lists record by record (class, `hb_chain`, verdict).

Check of the argument, **proved-in-effect on T20's parity store**: `diff --all --max-mb 300` analyzed
633 of its 636 scanned kernels twice (3 kernels over 300 MB skipped): 0 verdicts moved, the closure
fired in none. The same check was not run on X1's or X2's stores.

## 4. Step 3: the re-score

`eval/baselines/setup/t23_closure.py` (`scan`, `diff`, `summary`), drivers `p_t23_scan.sh`,
`p_t23_diff.sh`, `p_t23_tables.sh`, `p_t23_summary.sh`; outputs `eval/results/t23/{scan,diff}/<store>/`
(JSONL, committed); logs `eval/x_logs/t23-*.log` (force-added). No recording was made. Verdicts are
`sd.analyze(dot, kernel_json)` on the recorded aggregates (the default path), compared record by record;
the harness's CSV rows were not regenerated (§7).

| input | where it came from | scanned | closure adds a pair naming a CAS pc | analyzed twice | verdicts moved |
|---|---|---|---|---|---|
| X4 `final-rtraw` (5 labels, 3 nodes) | cuVein afccba7 (X4's report; dumps also committed under `eval/results/final-rtraw/`); BeeGFS store `final-rtraw` for the dots | 260 kernels | 260 | 260 | **3** (below) |
| T20 parity store `t20-parity2` (65 programs x 2 modes, dumps; recorded by T20's build, `STORE_INFO.json` git_head 31845b3 per `eval/AGGREGATES_DEFAULT.md` section 3) | BeeGFS | 680 tasks: 44 without atomic opcodes, 636 kernels (14 with a CAS pc, 349 with any growth) | 8 | 8 flagged; **633 of the 636 with `--all`** | **0** |
| X2 `final-certain` and `final-certain-recorded` (62 programs, vector-clock, dumps) | BeeGFS; recorded by `eval/final-certain` (head 7979869) | 369 kernels each (33 with a CAS pc) | 16 each | 16 each | **0** |
| X1 main store `final-2026-10` (4,725 programs x 2 modes; harness/runtime per `eval/FINAL_SWEEP.md` section 0) | BeeGFS; X1 branch `eval/final-sweep` head 43c855e3b1ca96805cb12d07a1de6a1839d947a2 | 9,398 (program, mode) tasks: 4,842 without atomic opcodes, 4,482 whose dots have no `.CAS`, 74 kernels (66 with a CAS pc) | 32 | 32 | **0** |
| X1 `-long`, `-long-sc`, `-24h-sc` | BeeGFS | 8 + 8 + 7 tasks: all without atomic opcodes except 1 without `.CAS` | 0 | 0 | 0 |
| X1 `-24h-vc` (11 program directories, recorded by git_head 40941876 per its `STORE_INFO.json`) | BeeGFS, rescanned 10-20 (job 315513, c19) | 9 tasks with a `vector-clock` directory: 8 without atomic opcodes, and `P9-atomicCAS-cuda` (30,000 kernels; it has CAS opcodes but every CFG cluster has fewer than 3 atomic instructions, so no class of 3 pcs can exist and the closure cannot add a pair). The other 2: `P7-stencil1d-cuda` has only `vector-clock-partial-rep1` (its dot has no atomic opcode), `P9-expdist-cuda` has no kernel directory (its dot has CAS opcodes; nothing recorded in this store to re-score) | 0 | 0 | 0 |
| X1 merged CSV `eval/results/baselines-cuvein.csv` through `make_tables.py` | `git show eval/final-sweep:...` (28,230 rows, sha256 bfbf32c5...); job 315313 | | | | `BASELINES.md` and `BASELINES_SUMMARY.md` regenerated from the unchanged CSV are **identical to the committed ones** and the "T23 rows" run is identical to the "as merged" run (0 diff lines) |

Scan errors: 0 in every store. T20's 8 flagged kernels are P4-graph-connectivity-racy-small (k1) and
the lock litmus P5 `norace_interblock_lock_waw`, `norace_interwarp_dev-blklock_waw`,
`race_interwarp_dev-blklock-no-stf_waw`, each in both modes; X1's 32 are 16 programs x 2 modes
(P4 graph-connectivity, matrix-multiplication, P5 lock litmus incl. `race_interblock_none-lock_rtraw`,
on which the closure did not fire).

### Every verdict that moves

All three are in X4's `final-rtraw` store, node c58, kernel `race_interblock_none-lock_rtraw`, pair
current 0x340 (block 0's write after its own unlock) / ancient 0x140 (block 1's read), WAR, global,
observed distance grid, found as an event-stream candidate:

| recording | mode | before (afccba7) | after (T23) | reason |
|---|---|---|---|---|
| `scor-scalar-clock/c58/run20` | scalar-clock | **ORDERED**, chain 0x1b0 -> 0x330 | **SC** (`sc`), no chain | gate `landing`: the chain lands on 0x330 (block 0's own unlock, an EXCH) and 0x330 is past the release of the lock block 0 took with a CAS; the closure joins 0x330 to the CAS 0xb0 through the observed edges 0xb0-0x230-0x1b0-0x330, no single edge does. The records show 0xb0 and 0x330 on one address. |
| `scor-scalar-clock/c58/run38` | scalar-clock | ORDERED, chain 0x1b0 -> 0x330 | SC (`sc`), no chain | same (closure pair 0xb0 / 0x330) |
| `scor-recorded/c58/run3` | vector-clock | SC (`sc`, `a2_uncertain`), chain [0x1b0, 0x330] reported, vetoed by `hb_races` | SC (`sc`, `a2_uncertain`), no chain | same pair. **No verdict change**: the certificate is withdrawn, the veto no longer has anything to hide. |

The other 257 X4 recordings all have closure growth (every lock recording does) but the closure fired
in none of them, so they are unchanged. The program-level verdict does not move in the 2 scalar-clock
recordings: the program stays RACE through the `dummy` WAW, which R3 cannot order on that trace; its
report counts go `races 1, sc 0, ordered 1` -> `races 1, sc 1, ordered 0` (`summary_old`/`summary_new`
in the diff record). The rates in `eval/FINAL_RTRAW.md` (2 of 50 scalar-clock, 1 of 150 vector-clock
recordings on c58) are reproduced as exactly these recordings. No new false positive appeared anywhere
the closure fired: it fired only on these three verdicts.

## 5. Step 4: the proof paragraph

`design/proof/hb_proof.tex`, a new paragraph "Location in the two declines (T23)" after "R3 as
implemented (T12)" (34 lines): defines the edge relation, shows it is not transitive on schedule C,
states that the two tests read its reflexive-symmetric-transitive closure (connected components,
union-find, once per kernel), why the certificate needs it ($\chi$ claims order in every schedule and
the recording, not the program, decided whether two pcs on one word looked like it), that
$\chi_{\approx}\subseteq\chi_{\approx_e}$ on every trace, the pc-granularity cost, and one new
assumption (R3d: a plain access to the same address between two atomics breaks the edge path).
**Not compiled**: there is no `pdflatex` on the `normal` nodes (job 314820) or on the laptop.

## 6. What the numbers do not say

* "Closure only withholds certificates" is argued from the code (all three uses are negated in
  `_chain_from`), and confirmed on T20's 633 kernels and X4's 260; it is not a proof for a CFG where
  `po` or `chain` change with `same_loc` in some way I did not read.
* The closure is at pc granularity. A pc that touches several words (an array of locks) joins their
  classes. The re-score found no verdict where that happened (the closure fired on 3 verdicts, all
  on a true same-address pair by the records), so its cost is **not measured** on a corpus that has such
  kernels; X1's stores have no `hb_events`, so the address evidence is available only for X4 (and T20,
  X2, where nothing fired).
* The re-score is at the level of `sd.analyze` verdict lists. A moved pair does not necessarily move a
  program row, and the converse needs no pair to move; X1's CSV rows were not regenerated by
  `parallel.py analyze` because no pair moved.
* `r3_loc_closure` lists gate firings the closure decided; one firing is not always the one that
  decided the pair (another chain, or an edge pair firing the same gate). That a verdict moved is
  decided by the knob-off run, not by the field.

## 7. Not run / unverified

* **X1 `final-2026-10-24h-vc`**: closed on 10-20 (§4). Between the shutdown and the return of BeeGFS no
  node probed on 10-20 (c8, c9, c12, c46-c48, c66, c76; jobs 315312, 315325, 315385) had
  `/mnt/beegfs`; the scan ran on c19 once it was back. `P9-expdist-cuda` has no recorded kernel in that
  store, so no verdict of the X1 CSV can be re-scored from it.
* X1 programs whose store directory is `*-partial-repN` (P9 and a few P7) are not enumerated by the
  scan (the harness' `analyze` does not read them either); 52 (id, mode) pairs of the main store have
  no kernel directory.
* The GPU halves of the green set (150 skips) and CLAUDE.md A4's "312 passed, 2 skipped" on a GPU node
  were not run; run the green set at install.
* The T6 parity was not re-run as a separate job: `hb_oracle.py` is unchanged and does not read the
  rule; the gate tests that compare `HbClock` with the oracle (`test_hb_clock_matches_specification`,
  `test_offline_barrier_pass_matches_oracle`) ran on the stored ScoR artifacts and passed in job 314794.
* `diff --all` was run on T20 only (3 kernels over 300 MB skipped), not on X1 or X2.
* Stores are not versioned: the commit shown for each is the branch whose report describes its
  recording, not a hash read from the store.
* Nothing was run on a GPU; the arm-sensitive facts (pc offsets) come from X4's sm_89 recordings.

## 8. Commits and commands

Commits on `fix/r3-same-loc-closure` (base afccba7): 8ec3455 (failing test + data), 78323f9 (change),
627369c / 4336498 / 1a9709c / f27b5dc / 3bd919e / e27ecac (re-score tooling), 4c200a2 (proof paragraph,
scan and diff outputs), 5319fe3 (summary script), 06706db (this report, first version), 50c756e (drivers exit 75 if a mount is missing), and the follow-up that closes the 24 h vector-clock store.

```
# step 1/2 (normal, no GPU): REV selects the exported revision
REV=8ec3455 sbatch --export=ALL,REV=8ec3455 eval/baselines/setup/p_t23_test.sh         # 314793
sbatch --export=ALL,REV=78323f9 eval/baselines/setup/p_t23_test.sh                      # 314794
# step 3
sbatch --export=ALL,STORE=final-rtraw,RTRAW=1 eval/baselines/setup/p_t23_scan.sh        # 314852
sbatch --array=0-7 --export=ALL,STORE=t20-parity2,IDFILE=eval/baselines/setup/t5b_parity_ids.txt eval/baselines/setup/p_t23_scan.sh   # 314853
sbatch --export=ALL,STORE=final-certain eval/baselines/setup/p_t23_scan.sh              # 314854 (and -recorded 314855)
sbatch --array=0-31 --export=ALL,STORE=final-2026-10 eval/baselines/setup/p_t23_scan.sh # 314874 (+ long, long-sc, 24h-sc)
sbatch --time=03:00:00 --exclude=c54,c2,c23,c46 --export=ALL,STORE=final-2026-10-24h-vc eval/baselines/setup/p_t23_scan.sh   # 315513 (10-20, c19)
sbatch --export=ALL,SCAN=final-rtraw eval/baselines/setup/p_t23_diff.sh                 # 314872
sbatch --export=ALL,SCAN=t20-parity2 eval/baselines/setup/p_t23_diff.sh                 # 314871
sbatch --array=0-3 --export=ALL,SCAN=t20-parity2,OUT=t20-parity2-all,ALL=1,MAXMB=300 eval/baselines/setup/p_t23_diff.sh   # 314910, 314930
sbatch --export=ALL,SCAN=final-certain eval/baselines/setup/p_t23_diff.sh               # 314893 (-recorded 314907)
sbatch --export=ALL,SCAN=final-2026-10 eval/baselines/setup/p_t23_diff.sh               # 314928 (killed by the shutdown after writing all 32 records)
sbatch --export=ALL,AFTER_CSV=$W/eval/results/t23/x1_merged.csv eval/baselines/setup/p_t23_tables.sh   # 315313
sbatch eval/baselines/setup/p_t23_summary.sh                                            # 315397: the counts above
```

Hardware: all jobs on `normal` (CPU only). Python 3.14.4 (`.env`), networkx as in the main checkout.

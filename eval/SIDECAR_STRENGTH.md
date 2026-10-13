# T10 — Sidecar strength and scope (O1)

Branch `fix/sidecar-strength`, from `cuVein` f127790 (6c34736 — T3b, T9 and T13 merged — plus
the 09-28 evening CLAUDE.md and `hb_proof.tex`). Code commits b467733 (the change and its tests)
and 6de19d0 (the engine's merged fallback); this report, the re-score tooling and results in the
commit after them. Decision D9 is **not** taken: nothing here is merged or installed. Hardware:
RTX 4060 Ti (sm_89; c1, c51, c58), drivers 580.82.07 / 580.95.05, CUDA 13.3; CPU re-scores on
`normal` nodes. Private runtime (`eval/baselines/setup/t9_build.sh` with `W=<worktree>`):
collector `583390c9ad93523f` → libsanalyzer `a89777270975133c` (b467733, job 292869; the E3
recording and the cost runs) and `e37bb490773ee05a` (6de19d0, job 292938; the final checks). The
installed runtime (collector `7bafac9fbac26efd`, libsanalyzer `75f46012144b56f2`) was run, never
written.

Labels as in CLAUDE.md A4: **proved-in-effect** (checked over N real traces), **tested** (a
verdict asserted), **unverified**.

**Summary.** A load or store is now strong at the scope its SASS `.STRONG.<scope>` token names —
`cuda::atomic` relaxed accesses (generic `LD/ST`) and `volatile` or `ld/st.relaxed.<scope>.global`
(address-spaced `LDG/STG`) alike — in the sidecar's new strength column, the engine, the oracle,
`barrier_only_pairs` and R2 (default policy `token`; the pre-T10 policies stay as ablations and
give the pre-T10 sidecar and engine path). On the kept corpus the only opcodes this changes are
`LDG/STG.E.STRONG.SYS`, i.e. `volatile` data, which occurs in 43 of 598 programs, all ScoR (16
applications, 27 litmus). There, 1,141 of 1,306 DR (kernel, pc pair) instances become SC; nothing
is lost or gained, and no verdict moves on any other program (545 × 2 modes). Verdicts: no new
false positive; false positives removed on 4 P4 programs at Race ∪ Latent and on 6 at Race
alone, among them T9's A2 case `matrix-multiplication-norace-small`; and **16 of the 18 ScoR
litmus races become SC-only in both modes** — under D2's counting a TP loss at both operating
points (P5 TPs 19 → 3 vector-clock, 18 → 2 scalar-clock) — plus `reduction-racy` at Race alone.
What stays a DR on the moved programs is their scope races (and the reduction's ticket pair). E1
and E3 do not move (the Indigo3 and ECL codes use `cuda::atomic`, strong already); E3,
re-recorded, is CLEAN with SC reports only. Engine == oracle holds, the installed engine gives the
same races from a T10 sidecar, the green set passes (275 + the one xfail), and the engine's memory
is unchanged. D9: adopt, with a D2 amendment for how ScoR is counted (§10).

## 1. What T9 left, and what is now a fact and what a policy

Before T10 the strength of a load or store was a *policy*, `--strong-ldst` / `$CUVEIN_STRONG_LDST`
(`sync_dominance.STRONG_LDST_POLICIES`, `coherent_scope`), default `generic`: a load or store
counted as strong (sidecar kind `ldst`, a key and moral-strength input of the engine, the oracle
and R2) only in the **generic** form `LD/ST.*.STRONG.<scope>`, which is how libcu++'s
`cuda::atomic` relaxed load/store lowers. The address-spaced form `LDG/STG.*.STRONG.<scope>` —
how a `volatile` access (and `ld/st.relaxed.<scope>.global`) lowers — was weak. The policy was
RC1's compromise of 2026-09-17, taken when a coherent pair was *ordered* (no conflict): calling
volatile strong then hid ScoR's volatile races. T9 removed that reason: with buckets (I2) and D12,
a morally strong pair is reported as an unordered strong conflict (SC) instead of being dropped,
and R2 decides only the DR/SC class, never the verdict. The policy — and with it a DR/SC split
that is not PTX's — was what T9 left.

Since T10 (D9 as proposed):

* **Fact, read off the SASS token** (default policy `token`, `sync_dominance.coherent_scope`):
  a load or store — `LD LDG LDS LDL ST STG STS STL` — whose opcode carries `.STRONG.<scope>`
  with a known scope is strong at that scope: `SM`/`CTA` → block, `GPU`/`SYS` → grid. No
  token, an unknown scope token, a copy (`LDGSTS`, never strong: Definition "Asynchronous
  copies") and `LDSM` are weak — scope errs narrow (Lemma "Monotonicity", converse). RMWs keep
  their column unchanged (`atomic_scope`: the token's scope, a bare shared `ATOMS` block, an RMW
  naming no scope the empty scope, never morally strong). Atomicity (RMW, release/acquire point,
  R3 atomic) is still the opcode's; strength no longer is: a strong load/store joins no clock
  and is never an R3 atomic, it only enters `key(e)` and `ms`.
* **Policy, kept as ablations only**: `generic` (the pre-T10 default), `all` (every `.STRONG`
  load/store; the same verdicts as `token` on every opcode of the kept corpus — it differs only
  for an unknown scope token, strong at the empty scope instead of weak), `none` (RMWs only).
  Under one of them the sidecar has the pre-T10 lines only (the same code writes them) and the
  engine takes the pre-T10 path (tested end to end under `generic`, §4).

## 2. Lowering and the corpus inventory

**Lowering on this toolchain** (sm_89, CUDA 13.3; `eval/baselines/setup/t10_lowering/`, job
292870 on a `rtx4060ti16g` node):

| source | SASS | strength (`token`) | pre-T10 `generic` |
|---|---|---|---|
| `st/ld.relaxed.cta.global` | `STG/LDG.E.STRONG.SM` | strong, block | weak |
| `st/ld.relaxed.gpu.global` | `STG/LDG.E.STRONG.GPU` | strong, grid | weak |
| `st/ld.relaxed.sys.global`, `volatile` global | `STG/LDG.E.STRONG.SYS` | strong, grid | weak |
| `cuda::atomic_ref<_, block>` relaxed store/load | `ST/LD.E.STRONG.SM` | strong, block | strong, block |
| `cuda::atomic_ref<_, device>` relaxed store/load | `ST/LD.E.STRONG.GPU` | strong, grid | strong, grid |
| `volatile` shared, `st/ld.relaxed.cta.shared` | `STS` / `LDS` (no token) | weak | weak |

The last row is a gap of the SASS, not of the rule: a strong shared-memory access carries no
token, so it is weak to every policy and an SC pair in shared memory is classed DR (errs toward a
report). No corpus instance of it was measured (unverified).

**Corpus inventory** (`eval/baselines/t10_token_scan.py` over the 776 dots of the stores `evcand`
and `full-2026-09-22`; `eval/results/t10-rescore/token_scan_{generic,token}.txt`): every opcode
with a `.STRONG` token is an `ATOM`/`ATOMG`/`RED` (`.SM`, `.GPU`, `.SYS`), or a generic
`LD/ST.E[.64].STRONG.SYS` (`LD.E.STRONG.SYS` 1,294 occurrences in 199 dots, `LD.E.64.STRONG.SYS` 9
in 1, `ST.E.STRONG.SYS` 291 in 161), or an address-spaced `LDG.E.STRONG.SYS` (2,407 in 35 dots) /
`STG.E.STRONG.SYS` (1,824 in 55 dots); the only atomic without one is the shared `ATOMS`. No
unknown scope token, no `.STRONG` on `LDS/STS/LDL/STL`, no `.SM`/`.GPU` on a load or store. So
the only opcodes whose strength T10 changes are `LDG/STG.E.STRONG.SYS` (weak → strong at grid),
and they occur in exactly **43 of the 598 programs** of T9's re-score selection — the 16 ScoR
applications of P4 (matrix-multiplication, reduction, rule-110, uts; norace and racy, small and
large) and 27 ScoR litmus kernels of P5 — all of them `volatile` data
(`eval/baselines/t10_rescore.py prepare`, every kernel of every dot, pydot). The Indigo3 codes (P1,
P3; the E1 suite) contain no `volatile` at all; their strong loads/stores are `cuda::atomic` in the
generic form, strong already under `generic`.

## 3. Implementation

* `python/sync_dominance.py`: policy `token` (default) in `coherent_scope`, the strength of a
  record for the sidecar, the oracle, `barrier_only_pairs` and R2 alike.
* `python/atomic_scope_sidecar.py`: under `token`, one comment line per memory pc of every
  kernel, `# strength <pc> <strong|weak> <scope|-> <kernel>`, derived from the same merged table as
  the coherent-pc lines (`<pc> <scope> <rmw|ldst> <kernel>`, kept). An engine older than T10
  skips `#` lines; under a pre-T10 policy no strength line is written.
* `HbEngine` (`pc_dependency_analysis.cpp`): parses the column into per-kernel tables
  (`kernel_strength`, merged / empty fallbacks mirroring `# async`), and `strong_scope()` gives a
  non-RMW record's strong scope from it when the sidecar has one, else from its `ldst` line as
  before; an RMW keeps its RMW column. One line changed in `process()`.
* Old sidecars keep today's behaviour exactly: without a strength line the engine code path is
  the pre-T10 one. Conversely, the `ldst` lines of a `token` sidecar list exactly the strong
  loads/stores with their scopes, so the **installed** engine computes the same races from a T10
  sidecar as the T10 engine (tested below) — merging the Python side alone already switches the
  pipeline to `token`, library or not.
* `hb_oracle.py`: unchanged logic (it reads the same table through `coherent_scope`); docstring
  and `--strong-ldst` help.

## 4. Verification (GPU, c1; `eval/baselines/setup/t10_check.sh`)

Run twice with identical results: job 292874 (b467733, libsanalyzer a8977727) and job 292939
(6de19d0, libsanalyzer e37bb490, the branch's engine).

| check | result |
|---|---|
| default tool path (no `YOSEMITE_HB_TRACE`), installed vs T10 runtime, 2 ScoR programs | identical up to device addresses and dist histograms (proved-in-effect, 2 programs) |
| one T10 sidecar, installed engine (75f46012) vs T10 engine vs T10 oracle, `strong_ldst_scopes.cu` (7 kernels) | equal `hb_races` and `hb_races_sync_only` on 7/7 (classes: SC ×5, DR ×2) |
| green set (CLAUDE.md A4; every trace re-recorded with the T10 runtime) | **275 passed, 1 xfailed** (`test_relaxed_handoff_should_race`, the I4 case), 0 failed, 0 skipped |
| `test_host_hb.py` (outside the green set) | 13 passed |
| `design/algorithms_check.py` on the 32 re-recorded ScoR traces (`token`) | oracle == Detect (switches off) and the second clock equal on 32/32 |

The installed baseline is the merge check's (48adefb: 238 passed + the one xfail); not re-run.
The 37 new tests (`python/test_atomic_memory_model.py`, all **tested**):
`testdata/strong_ldst_scopes.cu` has one strong-store/strong-load litmus per scope (inline PTX
`st/ld.relaxed.{cta,gpu,sys}.global`, the address-spaced forms T10 changes) at two distances
plus a plain control — the class in `hb_races` and in both modes' verdicts is SC for
cta/gpu/sys inter-warp and gpu/sys inter-block, DR for cta inter-block (cta does not cover another
block) and for the plain pair; engine == oracle on all seven; the sidecar's strength and `ldst`
lines name every access with its scope; `test_strength_token_rule` pins the rule per opcode (19
cases, the ablation policies included); the default policy is `token`; under
`CUVEIN_STRONG_LDST=generic` the sidecar has no strength column, the engine equals the oracle
under `generic`, and every pair of the litmus is a DR — the pre-T10 behaviour, end to end.

Changed expectations (deliberate, by D9's semantics; asserted per the active policy, so the
`generic` ablation keeps the old ones): ScoR's `race_*` litmus whose labelled race is between two
strong accesses (`_PTX_STRONG_RACES`, 16 of 18: volatile data against volatile data, or against
an atomic whose scope covers the other thread) now assert *SC reported, no RACE* instead of
*≥ 1 RACE*, in both modes; the two scope races (`race_interblock_blkatom`,
`race_interblock_blklock_waw`: a block-scope atomic or lock used across blocks) still assert
a RACE; `norace_*` additionally asserts no SC. `test_write_after_unlock_is_event_candidate`
(rtraw), `test_coherent_ldst.py::volatile_pair` and T9's I1 kernel (volatile data) assert the
class the policy gives (SC under `token`). Nothing was weakened to a "RACE or SC" check.

## 5. Re-score of the kept stores (no GPU)

Base: T9's re-scored store `t9-after` (the `evcand` + `full-2026-09-22` selection, 598 programs):
its vector-clock dumps carry what the installed engine writes (T9's oracle under `generic`), and
**T9's AFTER rows are the BEFORE** (`eval/results/t9-rescore/after/`, the T9 detector b1a6408; the
code of f127790 differs from it only in T3b's exit handling, which needs exit records these dumps
do not have, and 870dbb6's local-record order — none here; checked where it matters: the f127790
detector re-run on `t9-after` for 41 of the 43 affected programs, job 292953, gives the same
verdict, report ids and class counts as T9's rows on all 206 (id, mode, rep) rows,
`t10_rescore.py check-before`; the two left out are the 10 GB matrix-multiplication-large
scalar-clock dumps). AFTER: the
store `t10-after` — for the 43 affected programs the vector-clock dumps re-scored by the T10 oracle
(`token`), for the other 555 a symlink to `t9-after` (their strength tables are equal, so the oracle
would return the same `hb_races`) — analysed by `parallel.py analyze` with this branch
(`token`). Analysed: 588 programs (545 unaffected, 43 affected); not re-analysed: the 4 P1 1296n
programs T9's oracle could not finish and 6 unaffected programs with dumps above 10 GB (§9).
Tables: `eval/results/t10-rescore/T10_RESCORE_TABLES.md` (`t10_rescore.py tables`).

**Race sets** (the 37 affected programs with a vector-clock dump; (kernel, pc pair) instances of
`hb_races`, T9 oracle under `generic` → T10 oracle under `token`): 1,306 instances, all DR before;
after, **1,141 DR → SC and 165 DR**; none lost, none gained, none SC → DR; the second clock
(`hb_races_sync_only`) unchanged on every kernel. The 165 DR left are all scope races — RMW
pairs one of which is block-scope (`ATOMG.E.*.STRONG.SM`) and whose threads are in different
blocks, so not morally strong: rule-110-racy (128 large + 32 small; `ATOMG.E.ADD.STRONG.SM` 0x1b70
against the `.GPU` EXCH/ADD at 0x1120/0x12f0), matrix-multiplication-racy-small (2; the
block-scope lock CAS `ATOMG.E.CAS.STRONG.SM` 0xac0 against `ATOMG.E.EXCH.STRONG.GPU` 0xb80) and
ScoR `race_interblock_blklock_waw` (3; its block-scope lock used across blocks). No pair with a
`volatile` access on both sides stays a DR.

**Verdicts** (the harness's program verdict per (program, mode), reps collapsed as `make_tables`
does; labels from T9's manifest):

| mode | before → after | programs |
|---|---|---|
| scalar-clock | CLEAN → CLEAN | 308 |
| scalar-clock | RACE → RACE | 260 |
| scalar-clock | **RACE → CLEAN** | **20** |
| vector-clock | CLEAN → CLEAN | 302 |
| vector-clock | RACE → RACE | 232 |
| vector-clock | **RACE → CLEAN** | **19** |
| vector-clock | TIMEOUT → TIMEOUT | 35 |

No CLEAN → RACE anywhere: no new false positive, no true positive gained. **No row moved on a
program whose strength table is unchanged** (545 programs × 2 modes, **proved-in-effect**: P1, P2,
P3, P6 and the unaffected P4/P5/P9 programs re-score identically). Per suite:

| pset | mode | Race ∪ Latent TP/FN/FP/TN | Race alone TP/FN/FP/TN | programs with SC (labelled RACE/CLEAN) |
|---|---|---|---|---|
| P4 (ScoR apps, = E0) | scalar-clock | 14/0/6/8 → 14/0/**2**/12 | 14/0/6/8 → 14/0/**2**/12 | 0/0 → 6/6 |
| P4 | vector-clock | 9/0/5/4 → 9/0/**2**/7 | 9/0/5/4 → **7/2/0**/9 | 0/0 → 5/5 |
| P5 (ScoR litmus) | scalar-clock | 18/1/0/14 → **2/17**/0/14 | 18/1/0/14 → **2/17**/0/14 | 0/0 → 17/0 |
| P5 | vector-clock | 19/0/0/14 → **3/16**/0/14 | 10/9/0/14 → **3/16**/0/14 | 0/0 → 17/0 |
| P1, P2, P3, P6 | both | unchanged | unchanged | unchanged (P1 0/66, P3 0/34) |

(P4 vector-clock counts exclude its 10 TIMEOUT rows, unchanged.)

**Every moved program, with its cause** (all 20 + 19 rows are on affected programs; the cause of
each is the same: pairs of `LDG/STG.E.STRONG.SYS` — `volatile` data — or of such an access and an
`ATOMG` whose scope covers the other thread, DR under `generic`, SC under `token`):

* **True positives lost — the 16 ScoR litmus races between two strong accesses**, in both modes
  (RACE → CLEAN, every report now `sc` or `latent-sc`): `race_interblock_{blkfence_raw,
  fence_rtraw, lock-blkfence_waw, lock-no-stf_waw, lock-no-tf_waw, none-atom_waw, none-lock_rtraw,
  none-lock_waw}` and `race_interwarp_{blklock-no-stf_waw, blklock-no-tf_waw, dev-blklock-no-stf_waw,
  dev-blklock-no-tf_waw, none-atom_waw, none-blkatom_waw, none-blklock_waw, none-lock_waw}`. At
  Race alone the vector-clock loss is 7 of them (the other 9 were `latent`, not Race, already).
  They are exactly `_PTX_STRONG_RACES` of the green set (§4), where fresh recordings assert the
  same. Kept: `race_interblock_blkatom` (block-scope atomics across blocks), `race_interblock_
  blklock_waw` (3 DR of its block-scope lock, the data pair SC), and the canary (vector-clock).
* **True positives lost at Race alone only** — P4 `reduction-racy-{small,large}` (vector-clock):
  every planted pair is `volatile` and now SC; the program stays RACE at Race ∪ Latent only through
  the retirement-ticket pair (`ATOMG.E.INC.STRONG.GPU` vs the plain `STG.E` that resets the counter,
  `latent`), which the race-free build has too — it is D11's ticket idiom, not the planted race.
* **False positives removed** — P4 `matrix-multiplication-norace-small` (both modes; T9's A2 case:
  its four DR pairs are `volatile` critical-section accesses, now SC), `matrix-multiplication-
  norace-large` (scalar-clock; no vector-clock dump), `rule-110-norace-{small,large}` (both modes);
  and at Race alone `reduction-norace-{small,large}` (vector-clock), whose one remaining report is
  the same `latent` ticket pair (still a Race ∪ Latent FP in both modes, D11's case for T12).
* **Report sets that shrank on programs that stay RACE**: `matrix-multiplication-racy-{small,large}`,
  `rule-110-racy-{small,large}` — their scope races (block-scope RMWs across blocks) remain DR and
  keep the TP in both modes; their `volatile` pairs become SC. So on the programs that moved,
  what stays a DR is their scope races and the reduction's ticket pair (`uts`, affected but not
  moved, keeps its 10–11 shared-memory WAW reports in scalar-clock mode unchanged).

## 6. E0 / E1 / E3, and the explanation `eval/FIX_REPORT.md` gave

The old E-suite traces (`eval/driver.py`, 2026-09-1x, from a since-deleted worktree) were not
kept. **E0** (the ScoR applications: reduction, graph-connectivity) is re-scored through P4, which
holds the same programs in both builds and two input sizes; **E1** (Indigo3) through P1 and P3
(the Indigo3 sample and its race-free CC variants); **E3** (the four ECL-Suite race-free codes) had
no kept dump anywhere and was **re-recorded** (`eval/baselines/setup/t10_e3.sh`, job 292890 on c51,
T10 runtime a8977727, both modes, one rep; sources `github.com/burtscher/ECL-Suite` main, built for
sm_89 with CUDA 13.3 after replacing the two `cudaDeviceProp` clock fields CUDA 13 removed in the
banner `printf`; input `undirect2dim_rand_torus_100n_400e.egr`, E3's torus-100) and judged under
both policies on the same traces (`t10_policy_compare.py`, job 292933).

| suite | kept as | T10 moves | current verdicts (both modes) |
|---|---|---|---|
| E0 reduction | P4 `reduction-{norace,racy}-{small,large}` | every reported pair DR → SC (10–12 per program) | RACE at Race ∪ Latent in both builds, through one ticket pair (below); vector-clock Race alone: CLEAN in both builds |
| E0 graph-connectivity | P4 `graph-connectivity-*` | none (no `volatile`) | unchanged |
| E1 Indigo3 | P1, P3 | none (no `volatile` in the generated sources; `cuda::atomic` is generic-form, strong under `generic` already) | unchanged; SC reports on 66 P1 and 34 P3 race-free programs (T9); P1 race-free: no FP; P3: 14 / 16 FPs (vector / scalar), each exactly one same-pc shared-memory WAW |
| E3 ECL | re-recorded, `t10-e3` | none: `generic` and `token` give the same classes on every kernel | **CLEAN** in both modes; SC reports only: CC 25, GC 1, MIS 12, MST 6 / 7 (vector / scalar) |

(E3 in `E3-fixed.csv`, before RC1, T9 and T10: every code RACE, 40 structural reports.)

**The explanation, rewritten.** `FIX_REPORT.md` F1 and F5 called these reports benign races — real
HB-unordered accesses the algorithms tolerate. Under the PTX model most of them are not races:

* **E0 (F1, the reduction).** Every one of the 25 reports F1 lists is a pair of two `volatile`
  global accesses, `LDG/STG.E.STRONG.SYS` (F1 says so itself). A volatile access is a strong
  operation at system scope, so each pair is morally strong: an unordered strong conflict (SC),
  with defined behaviour — not a data race. Lock-step execution and the record-order inversion
  explain why the pairs are unordered in the trace; they never made them races. T10 classes them
  SC (all 10–12 per program). What stays is one pair per build: the retirement ticket
  (`ATOMG.E.INC.STRONG.GPU` against the plain `STG.E` that resets the counter) — a strong RMW
  against a weak store, a data race by PTX's letter, `latent` in this run; D11's ticket idiom,
  T12's case, identical in the race-free and the racy build. The racy build's planted race is
  `volatile` too, so it is now SC as well: the reduction reports no race of its planted bug under
  PTX (§5, TP lost at Race alone).
* **E1 and E3 (F5).** The "plain `LD.E.STRONG.SYS` reads" are not plain: a generic `LD` with
  `.STRONG.SYS` is a `cuda::atomic` relaxed load (Indigo3's `CudaAtomic` variants; ECL-Suite's
  `atomicRead`/`atomicWrite`, `library/ECLatomic.h`). Against an `ATOMG.E.CAS.STRONG.GPU` writer,
  or another relaxed load/store, the pair is morally strong — SC, not a race. RC1 (2026-09-17)
  made these accesses strong and T9 reports them as `sc` instead of ordering them; T10 adds nothing
  here (§2). The re-recorded ECL codes report **no race at all**, where F5's run counted 40
  structural reports. What remains a data race in these suites is weak on at least one side: the
  same-pc plain shared-memory WAW of the Indigo3 race-free CC programs (P3: each of their 30 RACE
  (program, mode) rows, 14 vector-clock and 16 scalar-clock, has exactly one report, that pair —
  RC4's `updated = true` flag of `FP_DIAGNOSIS.md`; that both stores write the same value is not
  recorded, so not checked) and plain reads of atomically updated locations — data races under PTX
  that the algorithms tolerate, for which the `benign` name stays right.

`FIX_REPORT.md` F1 and F5 carry a dated correction pointing here (the only edit to that file).

## 7. Cost

`YOSEMITE_HB_STATS` (`eval/baselines/setup/t10_measure.sh`, job 292932, one node c58, vector-clock
mode, one run each; BEFORE = installed runtime 75f46012 with the main checkout's `generic` sidecar,
AFTER = T10 runtime a8977727 with the `token` sidecar) on the one program of T5a/T9's measurement
set whose bucket keys change (reduction, large input; tiled_gemm and the Indigo3 CC program have no
address-spaced `.STRONG` access) and on one more affected program, rule-110-norace (small):

| program | buckets: locations / groups / entries / bytes | peak RSS | wall |
|---|---|---|---|
| P4 reduction-norace, large input | 1,079,357 / 1,101,498 / 1,123,578 / 360.0 MB, both | 6,634.5 → 6,635.3 MB | 9.63 → 8.53 s |
| P4 rule-110-norace, small input (per kernel, 16 kernels) | 17,408 / 19,456 / 52,222 / 7.7 MB, both | 872.3 → 869.7 MB | 1.92 → 1.57 s |

The bucket state is identical (an access keeps its key group and only the group's strong scope
changes, `W, weak` → `W, grid`; equal group counts mean no location of these programs mixes
volatile and plain accesses of one kind). The per-record cost is one hash lookup in the strength
table for a non-RMW record. The wall-clock numbers are one run each; they show no slowdown, and
one run cannot show more (the direction of the difference is not claimed). Sidecar size: one line
per memory pc (21 lines for `strong_ldst_scopes.cu`).

## 8. For whoever merges (T10 and T14 in parallel)

* **Files both branches edit.** T14 (`feat/a2-flag`) changes `hb_oracle.py`, `HbEngine` and
  `sync_dominance._hb_class`; T10's hunks there are small and elsewhere, but two are near T14's
  likely ones: in `pc_dependency_analysis.cpp` the one changed line of `process()`
  (`const int my_coh = strong_scope(pc, pit);`, just above the per-lane loop where RMW windows
  would be tracked) and the new members right after `atom_scope`; in `hb_oracle.py` the module
  docstring's sentence on moral strength. T10's other engine hunks are in `load_scopes()`,
  `select_kernel()` and the new `strong_scope()`; in `sync_dominance.py` the module docstring's
  R2 paragraph, the policy block, `strong_ldst_policy()`, `coherent_scope()` and the `main()`
  help — none in `_hb_class`. `python/test_hb_substitutions.py`: T10 changed the I1 fixture and its
  three tests (the class per policy) and the I1 paragraph of the docstring; T14 adds its lock
  test there. T10 does not touch `make_tables.py`, `hb_proof.tex`, CLAUDE.md or the generated
  tables.
* **T14's expectations meet T10's semantics.** The one verdict A2 affects, T9's
  `P4-matrix-multiplication-norace-small`, rests on four pairs of `LDG/STG.E.STRONG.SYS`
  (`volatile` data in the lock's critical section): under `token` they are SC, not DR (§5), so
  T14's "the four DR pairs flagged" holds on the pre-T10 policy only, and a lock-idiom test kernel
  with `volatile` data (like T9's I1 kernel) has SC, not DR, pairs to flag. Whether
  `a2_uncertain` also marks SC instances is T14's definition to settle; the merged tree's green
  set will show it either way.
* **Library.** Rebuild `libsanalyzer` from the merged tree and install that one file (the
  collector is unchanged by T10; the private T10 build is `sanalyzer/wt_install` of this
  worktree and must not be copied, it lacks T14). Then the green set from the merged tree.
* **The Python side alone already switches the pipeline.** The installed engine (75f46012) fed a
  sidecar from the merged `atomic_scope_sidecar.py` computes T10's races (§4, tested on 7
  kernels): after the merge the default policy is `token` whether or not the library is
  reinstalled, and engine == oracle holds either way.
* **Docs to update on merge** (not edited here by rule): `eval/README.md` §"False-positive
  diagnosis" lists `--strong-ldst {generic,all,none}` with no default; it is now
  `{token,generic,all,none}`, default `token`. `hb_proof.tex` §7 ("Two labeling details of the
  sidecar"): "a `.STRONG` load or store counts as strong only in its generic `LD`/`ST` form
  (policy generic; O1)" becomes "a load or store is strong at the scope its `.STRONG` token
  names, in the generic and the address-spaced form alike (O1, T10; `volatile` included); a strong
  shared-memory access lowers without a token on sm_89 and is weak (conservative by
  Lemma~\ref{lem:mono})"; the order of work's item (4) gets the branch, the counts of §5–§6 and
  "pending D9". CLAUDE.md B2's T10 row and D9 accordingly.

## 9. What remains unverified

* **Volatile ≡ relaxed.sys.** That PTX treats `ld/st.volatile` as relaxed operations at system
  scope is taken from the PTX ISA's memory-model chapter, not re-checked against one document
  version here; what was checked is that the compiler emits the identical
  `LDG/STG.E.STRONG.SYS` for `volatile` and for `st/ld.relaxed.sys.global` (§2). That ScoR's labels
  follow ScoRD's model, in which volatile data is ordinary data, is a reading of the suite (CUDA 8,
  compute_60, GPGPU-Sim; `ScoR/README.md`), not a statement of its authors.
* **Shared-memory strength.** Strong shared-memory accesses lower to `LDS/STS` with no token on
  sm_89, so the rule calls them weak and classes such a pair DR. How many corpus pairs this
  affects is not measured (the kept SASS cannot tell a volatile `LDS` from a plain one).
* **One architecture.** Only sm_89 SASS was seen. The parser accepts `.STRONG.CTA`, which no
  kept dump contains; on another SM the token text may differ (the unknown-token rule makes such a
  token weak, not strong).
* **Not re-analysed** (identical by construction: their strength tables are equal under both
  policies, `prepare` checked every kernel of every dot): the four P1 1296n programs T9's oracle
  could not finish, the six unaffected programs with dumps above 10 GB (P6
  `asyncmemcpy-memcpy_htod_kernel_race-racy`, P7 `hotspot`, P9 `crs`, `fpc`, `gpp`, `mr`; T9's
  rows stand for them).
* **E0 and E1 as suites.** The E-suite's own E0 and E1 traces were not kept; P4 holds E0's
  programs (both builds, two sizes) and P1/P3 the Indigo3 codes of E1 (a different sample of the
  generated codes: the E1 programs were not re-recorded — T10 cannot move them, since the
  generated Indigo3 sources contain no `volatile` and their strong loads/stores are generic-form).
  E3 was re-recorded once per mode (one schedule).
* **The installed engine on a T10 sidecar** was compared with the T10 engine on one binary (7
  kernels); the equality elsewhere is by construction (the `ldst` lines of a `token` sidecar are
  its strong pcs).
* **The engine's strength-column parser** has no test for malformed lines (skipped) or for the
  merged fallback of an undeclared kernel (6de19d0; no launch took that path in any run here).
* The default tool path was compared on 2 programs only.
* **Observation for T11, not investigated:** on the re-recorded ECL-GC (`runSmall`), 28 lanes of
  block 0 warp 3 exit (seq 459) and the 4 left then execute `__syncwarp()` with the full mask
  (seq 1636); `TV-record-after-exit` reads the syncwarp's named mask, so the engine records a
  trace-validity violation and the oracle raises (the policy comparison re-ran it with
  `YOSEMITE_HB_STRICT=0`, as the engine continues). No verdict reads it; whether a full-mask
  `__syncwarp` after partial exit is a trace defect or a W3 false alarm is T11's question.

## 10. D9: recommendation

**Adopt the token rule as the model's strength — and decide the ScoR presentation before
merging.** The DR/SC split is the model's (Definitions "Records" and "Verdicts": `str` and `scope`
are functions of the pc, read off the sidecar), and a DR reported on a pair of two
`LDG/STG.E.STRONG.SYS` accesses contradicts it: the compiler emits the same instruction for
`volatile` and for `st/ld.relaxed.sys.global`, so no sidecar can call one strong and the other
weak on facts, only on a policy — which is what `generic` is. The token rule is also what makes
the E0 and E3 explanations right (§6) and it costs nothing (§7).

The price is where the labels come from. ScoR's races are races of ScoRD's model, in which volatile
data is data; under PTX all but its two scope races are unordered strong conflicts. With D2's
counting (`sc` neither TP nor FP) the 18 P5 litmus races drop to 2 at both operating points, and
`reduction-racy`'s planted race leaves the TP column at Race alone (§5), although every one of
those pairs is still reported, as `sc`. So the recommendation comes with a D2 amendment for
labelled suites, in the spirit of D11: a labelled race that PTX calls an unordered strong conflict
is shown as *reported as SC* in its own column (with the PTX reason in a footnote), not as a miss,
and the paper states that ScoR's labels predate the PTX model. If a ScoR number under ScoRD's
notion of race is wanted, `CUVEIN_STRONG_LDST=generic` produces it end to end (tested, §4) and
should be named as that ablation, not be the default. Without such an amendment, merging this
branch makes the tables show ScoR as missed races; with `generic` kept instead, the detector keeps
calling well-defined PTX behaviour a data race. Either way the decision is D9's; this branch is
ready for the first.

## 11. Commands

From the worktree root `W` (`fix/sidecar-strength`); `ACCEL_PROF_HOME=W` for every run, the
worktree's own `lib/`, `ScoR/` and `cuHadron/` (copies), `build`, `.env`, `nv-compute/lib` and
`eval/baselines/{corpora,bin,inputs,setup/tools}` symlinked from the main checkout.

```
# private runtime (no write to the main checkout's build/ or lib/)
W=$W sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t10-build-%j.log eval/baselines/setup/t9_build.sh
                                               # 292869 (b467733: a8977727), 292938 (6de19d0: e37bb490)
# checks: default path, installed-vs-T10 engine on one T10 sidecar, green set, algorithms_check
W=$W sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t10-check-%j.log eval/baselines/setup/t10_check.sh
                                               # 292874 (c1, a8977727), 292939 (c1, e37bb490)
# lowering probe (sm_89, CUDA 13.3)
srun -n 1 -p rtx4060ti16g -x c54,c2 --time=00:15:00 bash eval/baselines/setup/t10_lowering/lowering_probe.sh
# corpus token inventory (776 dots)
srun -n 1 -p normal --time=00:30:00 .env/bin/python eval/baselines/t10_token_scan.py [--policy token] \
    /mnt/beegfs/$USER/cuvein_traces/evcand /mnt/beegfs/$USER/cuvein_traces/full-2026-09-22
# litmus preview on the copied ScoR artifacts (login node)
.env/bin/python eval/baselines/t10_policy_compare.py ScoR/microbenchmarks/artifacts/*_*
# re-score (no GPU)
srun -n 1 -p normal --time=03:00:00 -c 2 .env/bin/python eval/baselines/t10_rescore.py prepare   # 292888
W=$W sbatch --array=0-7 --exclusive -o $W/build_logs/t10-rescore-%A_%a.log \
    eval/baselines/setup/p_t10_rescore.sh                                                    # 292892
W=$W IDFILE=eval/results/t10-rescore/ids_unaffected.txt WHICH=after sbatch --array=0-31 \
    -o $W/build_logs/t10-analyze-%A_%a.log eval/baselines/setup/p_t10_analyze.sh              # 292900
W=$W IDFILE=eval/results/t10-rescore/ids_affected.txt WHICH=after-affected sbatch --array=0-7 \
    --exclusive -o $W/build_logs/t10-analyze-aff-%A_%a.log eval/baselines/setup/p_t10_analyze.sh  # 292940
.env/bin/python eval/baselines/t10_rescore.py tables \
    --after "eval/results/t10-rescore/after*/baselines-cuvein-shard*.csv" \
    --exclude "$(paste -sd, eval/results/t10-rescore/ids_not_reanalysed.txt)"
# the BEFORE rows checked: the f127790 detector on t9-after for 41 of the 43 affected programs
git archive -o before_code.tar f127790 python eval/baselines eval/aggregate.py   # extracted to CODE
W=$W CODE=<tree> IDFILE=eval/results/t10-rescore/ids_affected_before.txt sbatch --array=0-3 \
    -o $W/build_logs/t10-before-%A_%a.log eval/baselines/setup/p_t10_before.sh                 # 292953
.env/bin/python eval/baselines/t10_rescore.py check-before
# E3 re-recorded (ECL-Suite main, ~/incoming/ecl/ECL-Suite-main.tar.gz, sha256 be1e4139...)
W=$W sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t10-e3-%j.log eval/baselines/setup/t10_e3.sh
                                               # 292889 (build failed: CUDA 13 API), 292890 (c51)
srun -n 1 -p normal --time=00:30:00 .env/bin/python eval/baselines/t10_policy_compare.py \
    /mnt/beegfs/$USER/cuvein_traces/t10-e3/E3-* --json eval/results/t10-e3/policy_compare.json  # 292933
# HB_STATS, installed (generic sidecar) vs T10 (token sidecar), same node
W=$W sbatch -p rtx4060ti16g -x c54,c2 -o $W/build_logs/t10-measure-%j.log eval/baselines/setup/t10_measure.sh  # 292932
```

Outputs: `eval/results/t10-rescore/` (selection with the per-program strength diff, id lists, token
scans, `T10_RESCORE_TABLES.md`, the AFTER and the checked-BEFORE CSVs; the 43 oracle details in
`detail/` are gitignored, as T9's were, and copied to `/mnt/beegfs/fzheng4/t10-rescore-detail/`),
`eval/results/t10-e3/`,
`eval/baselines/setup/t10_stats/`; BeeGFS stores `cuvein_traces/t10-after` (unaffected programs are
symlinks to `t9-after`), `cuvein_traces/t10-e3`, confirm files `t10-confirm/`, check dumps
`t10_check/`, E3 binaries `t10-e3/`.

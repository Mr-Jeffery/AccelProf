# `a2_uncertain`: definition of the flag (T14, step 1)

Written 2026-09-28 against `cuVein` f127790, before any implementation (CLAUDE.md C/T14 step 1,
decision D15). Terms are those of `design/proof/hb_proof.tex`: records and `seq` (Definition
"Records": a dump record is one record per lane, in lane order at its position), successor and
chain `⇝` (Definition "Gate, chain"), `→hb` (Definition "Happens-before"), DR/SC (Definition
"Verdicts"), A2 (Trusted base), the matrix of §5. The gate is the trusting one (I4), as in the
code; nothing here depends on that choice except where said.

## 1. Windows and the assumption the flag rests on

For an RMW record `r` of thread `t`, `nx(r)` is the position of `t`'s next record of any kind
(memory, barrier arrival, syncwarp, exit, cp.async commit/wait; a `local` record is no record,
D14), and `+∞` if `t` has none. The **window** of `r` is `[pos(r), nx(r))`. The collector writes
`r` at the callback *before* the instruction, so `pos(r)` is an issue point; the RMW takes effect
somewhere in its window.

- **A2** (proof, Trusted base): on every location, `seq` order of the RMWs is coherence order.
- **A2w** (what the flag assumes instead): on every location ℓ the coherence order `co_ℓ` is
  some linear order of ℓ's RMWs with `r` before `q` whenever `nx(r) ≤ pos(q)` — an RMW has
  taken effect by its thread's next callback. Call such a `co` *window-consistent*; `seq` is one.
  T13 (`eval/NVBIT_SPIKE.md` §4) found every observed inversion inside overlapping windows and
  none outside (30 runs, all cross-warp pairs of the lock word). A2w is an assumption about the
  collector, measured under NVBit's timing, not proved.

For a window-consistent `co`, `→co` is Definition "Happens-before" with the successor relation of
Definition "Gate" taken from `co_ℓ` instead of `seq` (same gate, same `ms`). `→seq` is what the
engine and the oracle compute.

An edge `r → q` between successors on ℓ is **order-uncertain** (the brief's term) iff the windows
intersect, `pos(q) < nx(r)`. On each location the RMWs fall into **clusters**: maximal `seq`-runs in
which every RMW is issued while an earlier RMW of the run still has its window open. A cluster of
one RMW is a *singleton*; the others are *multi*. Every order-uncertain edge lies inside a multi
cluster; every window-consistent `co_ℓ` orders the clusters of ℓ as `seq` does (a member of a later
cluster is issued after every window of the earlier one closed) and can reorder only inside a
multi cluster. A location, kernel or trace with no multi cluster has `co = seq` for every
window-consistent `co`: there A2w implies A2 and the flag is 0 (§3).

## 2. The target, and why the brief's thread-pair approximation is not enough

A DR instance `(a, b)` (a record pair Check reports with class DR, `pos(a) < pos(b)`) should be
flagged if the execution may have ordered it: **F\* = { (a, b) : a →co b or b →co a for some
window-consistent co }**. The brief reads this as "reverse the order-uncertain edges on the
pair's location" and approximates it by "both threads hold RMWs on some location whose chain has
an order-uncertain edge between them". That approximation can **under**-flag, because `→co` is
transitive through other threads, other locations and barriers:

- *Block-leader lock.* Thread 0 of blocks X and B takes a global lock, `__syncthreads()`, the
  block works on shared data, `__syncthreads()`, thread 0 unlocks. If B's successful CAS is
  recorded before X's unlock that it read from, every conflicting pair (X's worker access, B's
  worker access) is a DR on the trace and ordered in the execution — and no worker holds an RMW.
- *Hand-over-hand.* A releases ℓ1 to X, X releases ℓ2 to B with the ℓ2 edge inverted: (A's access,
  B's access) is a DR on the trace; A and B share no location.
- *Non-adjacent inversion.* `r1, r2, r3` on ℓ with only `r1`'s window long: `co = r2, r3, r1` is
  window-consistent and puts `r3 ⇝ r1`, though `r3`'s successor edge `r2 → r3` is certain.

So the flag is computed by a clock, like `→hb` itself.

## 3. The flag as implemented (the "possible" clock)

Next to `vc[t]` each thread keeps a sparse delta `pd[t]`; `poss[t] = vc[t] ⊔ pd[t]`. `pd` follows
`vc` through every recorded operation (barrier/syncwarp joins, the recorded acquire joins the
releaser's `pd` with its clock, a publish stores `pd` with the clock, cp.async issue/commit/wait)
and receives, in addition, **late acquires**: when the window of an RMW `v` (thread `V`, ℓ) closes —
at `V`'s next record, before that record is processed, or at the end of the kernel —
`pd[V] ⊔= A(v)` with

- `A(v)` = the join `J_K` of the cluster `K` of `v` if `K` is multi: the *contribution* of every member
  `u` of `K` issued so far (`u`'s `poss` at issue, pre-tick: what `u` publishes) plus the cluster's
  inflow;
- `A(v)` = the inflow of `K` if `K` is a singleton after a multi cluster;
- nothing if `K` and the cluster before it are singletons (then the recorded chain is exact).

The **inflow** of `K` is the previous cluster's final `J` if that one was multi, else its single
RMW's final contribution (what it published, plus its own late acquire). RMWs whose scope is
empty (`none`, never morally strong) contribute nothing and acquire nothing; they still count as
members (their order is uncertain, and they break the recorded chain). Inside a multi cluster and
at its boundaries `ms` is not checked — the only place the flag ignores a static label.

A DR instance `(a, b)` is **flagged** iff `epoch(a) ≤ poss_b[tid(a)]`, or `a` is an RMW whose window
contains `pos(b)` and `epoch(b) ≤ poss_a[tid(b)]` after `a`'s late acquire. Here `poss_b` is `poss` of
`b`'s thread at `b` if `b` is not an RMW, and after `b`'s late acquire if it is. The decision for an
instance with an RMW endpoint whose window is still open is held on that window and taken when it
closes (deferral as in §3 of the proof for the instance gate); all other decisions are final at
Check. `hb_races[*].a2_uncertain` counts the flagged instances of each aggregated record (DR
records only; SC instances are never flagged); the dump carries `"hb_a2": 1`.

**Only over-flags.** *Claim:* for every window-consistent `co` and every `x →co y` (`y` a memory
record), `epoch(x) ≤ poss_y[tid(x)]`, with `poss_y` as above; and if `y →co x` with `pos(x) < pos(y)`,
then `x` is an RMW whose window contains `pos(y)` and `epoch(y) ≤ poss_x[tid(y)]`. Hence `F\* ⊆ flagged`.
*Sketch.* Generators (PO), (SYNC) and the agent ones are the same for every `co` and `pd` follows
`vc` through them. An (ATOM) edge of `→co` is a chain of `co`-consecutive, morally strong RMWs on one
location; take one step `z → z'`. Both are non-`none`. If they lie in one cluster, `z` was issued
before `nx(z')` (window-consistency: `z` before `z'` in `co` forces `pos(z) < nx(z')`), so `J_K` at
`nx(z')` holds `z`'s contribution; `z`'s `→co`-past through its own `co`-predecessors on ℓ consists
of members `co`-before `z`, hence `co`-before `z'`, hence issued before `nx(z')` and in `J_K`
directly, or comes through the inflow, which is in `J_K`. If they lie in different clusters, the clusters are
adjacent (a whole cluster between them would be `co`-between), `z` is a member of the previous
cluster and its final contribution is in the inflow of `z'`'s cluster; between two singletons the
recorded chain is the edge itself, under the same `ms` test. Knowledge that reaches `z` from
elsewhere reached `z`'s thread before `pos(z)` (its earlier windows closed before its next record)
and is in `z`'s contribution. `z'`'s thread and `z'` itself (for the flag) read `A(z')` at `nx(z')`,
and every later record of the thread comes after. Induction along the `→co` path gives the first
claim. For the second: a PO or SYNC step lands at or after its source's next record, so a path
from `y` first gets below `pos(y)` by a `co` step `u → z` with `pos(u) ≥ pos(y)`, and from there on
only `co` steps on `z`'s location keep it below; every record it visits there is an RMW `co`-after
some such `u`, so its window reaches past `pos(u) ≥ pos(y)`, and `x` is one of them. Walk back
along the `co` steps into `x`: the first record `m` whose issue-time `poss` already carries `y` (it
exists — `y` itself if `y` is an RMW there, else a record reached from `y` by PO or SYNC) is
issued at or after `pos(y)` and, being `co`-before `x`, before `nx(x)`: it is in `x`'s cluster and
its contribution is in `J` at `nx(x)`. ∎

*Consequence (the paper's statement):* under A1, **A2w** and A3, an unflagged DR instance is
unordered in the execution's own `→hb` (Proposition "Fidelity" with A2 weakened to A2w and the
single `co` of the execution); a flagged one may or may not be. A Race report (pc pair) rests on
A2 alone iff **every** DR instance of the pair is flagged; one unflagged instance makes the report
A2-robust.

**What over-flagging costs.** Nothing on a kernel with no multi cluster (`poss = vc`). Otherwise
the flag may mark an instance that no single window-consistent `co` orders: `J` joins members
whose orders no single `co` realises together; `ms` is ignored inside multi clusters (a
scope-mismatched chain inside a multi cluster counts as possible); the lanes of one warp
instruction always overlap (lane order is part of A2, and the flag treats it as uncertain); and
a thread with no next record keeps its window open to the end of the kernel — every dump in the
evcand store predates exit records (T3b), so there a thread's last RMW overlaps every later RMW on
its location. The measured number of flagged instances and reports, per suite, is in
`eval/A2_WINDOWS.md`.

## 4. The other direction: a manufactured edge

Inside a multi cluster the recorded chain can order two RMWs the other way round from the
execution, so `→seq ⊄ →co`: a pair ordered on the trace only through such an edge is not reported
and may be a race of the execution (D15's missed-race risk). The flag marks DR reports only and
says nothing about these pairs. What the window count says: a kernel with no multi cluster has
none (there `co = seq`); otherwise the number of overlapping cross-warp pairs on locations whose
RMWs release or acquire (an RMW next to a plain access to another location in its thread) is the
number of hand-offs whose direction the trace does not fix — an upper bound on the hand-offs
that can hide a race, not a count of hidden races. Enumerating them needs the "certain" clock
(only the chain edges every window-consistent `co` shares); not built — the value-recording
collector (D15, post-submission) removes the question.

## 5. What does not change

- **No verdict.** `_hb_class`, `CLASS_VERDICT` and the class of every pair are computed as before;
  `judge` copies a pair-level `a2_uncertain` (True: every DR instance flagged; False: some DR
  instance unflagged; None: no flag in the dump) onto the verdict record and reads it nowhere.
- **`barrier_only_pairs`** and the second clock (`hb_races_sync_only`): `Detect(T, sync)` has no
  (ATOM) generator, so it does not depend on coherence order; unaffected, and so is the
  barrier-ordered row in both modes. The flag is defined on the full clock's DR instances, i.e.
  in vector-clock mode. (R3 is not covered by it in either mode: its hops are observed
  atomic–atomic edges, directed, and an inversion can re-orient an instance's edge; a lock
  program observes both directions over its hand-offs, a single hand-off does not.)
- **Tables** (`make_tables.py`, D2's convention): a program whose positive at an operating point
  rests only on flagged reports is counted in its own `a2_uncertain` column, as neither TP nor FP,
  split by label so nothing is hidden. At Race alone that is "every this-run Race report flagged".
  At Race ∪ Latent a flagged report whose pair no static rule orders on the trace (no R1, no R3
  chain) stays a positive — reordered, it would be Latent (a raced pair is never barrier-ordered,
  and that row does not depend on coherence order) — so only reports with an R1 or R3 certificate
  move; this reads R3 off the trace (the caveat above).

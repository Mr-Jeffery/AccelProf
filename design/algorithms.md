# The algorithms as implemented (cuVein 3331d35), and an examination of the proof

Written 2026-09-24 from `python/hb_oracle.py`, `python/sync_dominance.py` and
`design/proof/hb_oracle_proof_v3.tex` / `hb_defs_v4.tex`, all at `cuVein` 3331d35.
`HbEngine` (`sanalyzer/src/tools/pc_dependency_analysis.cpp`) is the parity-tested port
of the oracle and is not transcribed separately. Nothing here was run; the examination
is by hand against the text of the code and the proof. Every claim that needs a run is
marked *to test*.

Terminology follows the proof: **sound** = misses no race, **complete** = every report is
a race. `≠ v3` marks a line that differs from Algorithm 1 of the v3 proof.

---

## 1. Inputs, records, static tables

**Thread ids.** `tid(block, warp, lane) = block << 10 | warp << 5 | lane`. The async agent
of `t` is `agent(t) = t | 1<<62` (T1a). `thread_distance(t1, t2)` ∈ {WARP, BLOCK, GRID}
compares the block and warp fields (an agent's distance is its thread's).

**Locations.** `loc = (shared, block, addr)` for shared memory, `(space, addr)` for global
and local. `≠ v3`: v3 keys local memory per thread, and keys the release map by address.

**Records of `hb_events`** (one per warp instruction, in `seq` order; T1a additions marked):

| type | fields | meaning |
|---|---|---|
| `read` / `write` / `atomic` | block, warp, pc, space, size, active_mask, lanes[{lane, addr}] | memory access; `atomic` is set from the collector flag but the model classifies RMWs by pc (below) |
| `barrier` | block, warp, bar_index, thread_count (0 = whole block), active_mask | one arrival record per warp of a `BAR.SYNC`/`BAR.RED` |
| `syncwarp` | block, warp, sync_mask, active_mask | a masked `WARPSYNC`; an instance by itself |
| `pipeline_commit` (T1a) | block, warp, active_mask | `cp.async.commit_group` by each active lane |
| `pipeline_wait` (T1a) | block, warp, active_mask, groups = N | `cp.async.wait_group N` (`wait_all` = 0) |
| *(exit)* | — | **not emitted**: the collector's `BlockExit` records are dropped by `hb_collect_events` (`≠ v3`, which has exit records) |

Dump-level markers: `hb_async: 1` (dump produced with the T1a collector; only then are copies
modelled as agent accesses), `hb_races`, `hb_races_sync_only` (vector-clock mode only),
`coherence_profile`, `tv_violation`.

**Static tables from the kernel CFG and the sidecar** (`sync_dominance`):

- `atom_scope[pc]` for RMW opcodes `ATOM|ATOMG|ATOMS|RED`: `.STRONG.{CTA,SM}` → BLOCK,
  `.STRONG.{GPU,SYS}` → GRID, bare `ATOMS` → BLOCK, other/unknown → NONE. Lattice
  NONE < WARP < BLOCK < GRID. (v3's `AtomScope`.)
- `coh_scope[pc]` = `atom_scope[pc]`, or, for a load/store carrying `.STRONG.<s>`, the scope
  of `<s>` **if the opcode form is admitted by the policy** `--strong-ldst`
  (`generic`, the default: only the generic `LD`/`ST` forms, i.e. `cuda::atomic`
  loads/stores; `all`: also `LDG/STG/LDS/STS/…`, i.e. `volatile`; `none`: RMWs only).
  `≠ v3`.
- `async_pcs` = the `LDGSTS` pcs, unless the kernel contains `ARRIVES.LDGSTSBAR` (mbarrier
  completion, unmodelled until T1b) in which case the set is empty and copies are the
  issuing thread's own accesses. Applied only to dumps with `hb_async`.
- `block_tc` = `block_thread_count` of the launch.

---

## 2. Algorithm 1 — vector-clock mode, as implemented

The oracle is the specification; the engine consumes the same records in buffer order.

```
State
  vc[t]          vector clock of t: barriers, syncwarps and atomic hand-offs; vc[t][t] starts at 1
  vs[t]          second clock of t, advanced by barriers/syncwarps ONLY                       ≠ v3
  released[loc]  (clock, block, scope) published by the last RMW on loc                       ≠ v3 (v3: by address)
  last_write[loc]   (tid, epoch, sepoch, pc, coh, block) of the last write or RMW on loc
  last_reads[loc]   tid ↦ (epoch, sepoch, pc, coh, block): each thread's latest read since last_write
  pending_bar[(block, bar)]   tids arrived at the open instance
  groups[t]      snapshots (vc, vs) of agent(t) taken at each commit, oldest first            ≠ v3
  profile[addr]  observed sequence of (tid, per-thread atomic index)                          observational
  TV state       bar_warps_seen[(block, bar)], warp_waiting[(block, warp)]                     monitor

own(t)   : if vc[t][t] = 0 then vc[t][t] ← 1;  return vc[t][t]        owns(t): the same on vs
Sync(S)  : for C in (vc, vs):  J ← ⊔_{u∈S} C[u];  for u ∈ S: C[u] ← J;  C[u][u] ← J[u] + 1
coherent(c1, b1, c2, b2) : c1 ≠ ⊥ ∧ c2 ≠ ⊥ ∧ (min(c1,c2) = GRID ∨ (min(c1,c2) = BLOCK ∧ b1 = b2))
covers(scope_r, block_r, scope_q, block_q) : the same test on two RMW scopes (v3's covers)

Conflict(prev, cur, o = tid(cur))              — prev = a last_write / last_reads entry
  if prev.epoch  > vc[o][prev.tid] : report (prev.tid, prev.pc, tid(cur), pc(cur), loc, kind)
  if prev.sepoch > vs[o][prev.tid] : sync_pairs[{prev.pc, pc(cur)}] += 1                       ≠ v3

for each record e in seq order:
  TV-seq-monotonic: seq(e) ≤ previous seq → reject

  pipeline_commit, lane t:                                                                   ≠ v3
      ag ← agent(t);  own(ag); owns(ag)
      groups[t].append((copy vc[ag], copy vs[ag]));  vc[ag][ag] += 1;  vs[ag][ag] += 1
  pipeline_wait N, lane t:                                                                   ≠ v3
      if |groups[t]| > N:  done ← |groups[t]| − N;  (svc, svs) ← groups[t][done − 1]
                            vc[t] ← vc[t] ⊔ svc;  vs[t] ← vs[t] ⊔ svs;  drop groups[t][0 .. done)
  syncwarp:            Sync(masked lanes as tids)
  barrier arrival:     A ← pending_bar[(block, bar)] ∪ active lanes;  expected ← thread_count or block_tc
      TV-overfill:     expected ≠ 0 ∧ |A| > expected → reject
      if expected = 0 ∨ |A| ≥ expected:
          TV-expected-nonzero-multiwarp: expected = 0 ∧ >1 warp ever arrived here → reject
          Sync(A);  pending_bar[(block, bar)] ← ∅;  the arrived warps are no longer pending
      else: the warp is pending at (block, bar)
      (an exited thread never arrives: the instance stays open forever)                     ≠ A3

  memory access at pc, space, per active lane t0 with address addr:
      TV-completion-order: (block, warp) pending at a barrier → reject
      t ← t0;   if pc ∈ async_pcs: t ← agent(t0);  own(t0); vc[t] ⊔= vc[t0]; own(t); (same on vs)   ≠ v3
      loc ← loc(space, block, addr);  coh ← coh_scope[pc]

      if pc ∈ atom_scope:                                              — RMW
          profile[addr].append((t, atom_idx[t]++))
          (acquire)  if released[loc] = (c, rb, rs) ∧ covers(atom_scope[pc], block, rs, rb): vc[t] ⊔= c
          own(t); owns(t)
          (check)    w ← last_write[loc]:  if w ∧ w.tid ≠ t ∧ ¬coherent(coh, block, w.coh, w.block): Conflict(w, e) kind "atomic"
                     for r ∈ last_reads[loc]: if r.tid ≠ t ∧ ¬coherent(coh, block, r.coh, r.block): Conflict(r, e) kind "WAR"
          (tick)     vc[t][t] ← own(t) + 1                                                    ≠ v3: v3 publishes first
          (publish)  released[loc] ← (copy vc[t], block, atom_scope[pc])                       — carries the post-tick own component
          (record)   last_write[loc] ← (t, vc[t][t], owns(t), pc, coh, block);  last_reads[loc] ← ∅   — post-tick epoch  ≠ v3
      else:                                                            — read or write
          ep ← own(t); sep ← owns(t)
          (check)    w ← last_write[loc]:  if w ∧ ¬coherent(coh, block, w.coh, w.block):
                         if w.tid ≠ t: Conflict(w, e) kind "WAW" if write else "RAW"
                         else if write ∧ t is an agent: Conflict(w, e, o = t0) kind "WAW"          ≠ v3
                     if write: for r ∈ last_reads[loc]: if r.tid ≠ t ∧ ¬coherent(...): Conflict(r, e) kind "WAR"
          (record)   if write: last_write[loc] ← (t, ep, sep, pc, coh, block);  last_reads[loc] ← ∅
                     else:     last_reads[loc][t] ← (ep, sep, pc, coh, block)

Output
  races             deduplicated on (addr, a_tid, a_pc, b_tid, b_pc, kind); agent ids mapped to the
                    issuing thread with "async" ∈ {a, b, ab}
  races_sync_only   sync_pairs as [pc_lo, pc_hi, count]
  coherence_profile per-address (tid, index) sequence and FNV-1a hash
```

**What it computes, stated as relations.** Write `conf_impl(a, b)` for
"same `loc`, different tids (an agent counts as a tid), at least one write or RMW, and
`¬coherent(a, b)`"; write `HB_impl` for the relation the clocks decide. Then a report is a
pair with `conf_impl` and `¬(a HB_impl b)` for `seq(a) < seq(b)` (Section 6 makes `HB_impl`
precise relative to the proof's `HB`). `races_sync_only` is the same over `HB_sync`, the
closure of (PO) and (SYNC) alone, at the granularity of pc pairs.

---

## 3. Algorithm 2 — scalar-clock mode, as implemented

Static rules over the kernel CFG, joined with the trace's dependency edges and the event
stream. The name refers to what the offline pass keeps per thread (its own component; the
joined base is shared by a sync group); the rules themselves are PC-level.

### 3.1 Region graph and static facts

```
parse the nvdisasm CFG: per basic block the list (pc, opcode); block edges; EXIT/RET → virtual exit
classify(opcode):
   BAR.SYNC*, BAR.RED*  → sync, scope BLOCK, qualifying          BAR.ARV* → sync, BLOCK, non-qualifying
   WARPSYNC             → sync, scope WARP,  qualifying           other BAR.*, unknown *SYNC* → tripwire (exit 2)
   MEMBAR.{GPU,SYS}     → fence, scope GRID, non-qualifying       MEMBAR.CTA → fence, scope BLOCK
   EXIT, RET            → exit
   LD/ST/ATOM/RED/LDGSTS families → mem
region graph G: each block is split at every sync/fence instruction; each such instruction is its
   own node; memory pcs map to the region they sit in (pc_node); exits go to VEXIT
dom, postdom over G (networkx immediate dominators, closed to full sets)
po(u, v) : pc_node[u] dominates pc_node[v], or same region and u < v          — certified program order
release_scope(u, a) : max scope of a fence f with f ∈ postdom(region u) ∩ dom(region a); NONE if none
```

From the trace (`nodes`, `edges`): `flags[pc]` = (space, access); `atom` = RMW pcs with
scope (R3's atomics); `coh` = coherent pcs (R2's); `sync_edges` = non-cold atomic–atomic
edges `(anc, cur, d)` with observed distance `d` > NONE and `min(scope) ≥ d`; `same_loc` =
every atomic–atomic edge pair at any distance (intra-thread included).

### 3.2 The three ordering rules

```
R1 dominance(u, v)  (u ≠ v):
   if region(u) = region(v): NONE
   best ← max scope over qualifying syncs s with s ∈ postdom(region u) ∩ dom(region v) or the mirror
   if best > NONE: delete every qualifying sync of scope ≥ best from G; if region(u) and region(v)
      are still connected in either direction (a sync-free path, e.g. a loop's wrap-around): NONE
   return best
R1 loop_scope(u)    (same pc):
   if region(u) is on no cycle: NONE
   for σ in (GRID, BLOCK, WARP): if deleting the qualifying syncs of scope ≥ σ breaks every cycle
      through region(u): return σ
   NONE
R2 coherence(u, v): min(coh[u], coh[v]) if both coherent, else NONE
R3 chain(anc, cur): a scoped happens-before path at PC level
   starts ← [(anc, GRID)] if anc ∈ atom
            else [(a, release_scope(anc, a)) for a ∈ atom with release_scope(anc, a) > NONE]   — fenced release
   DFS from each start (node n, synced?, path, acq):
      accept if synced ∧ n ≠ cur ∧ po(n, cur) ∧ ¬past_release(acq, cur)                       — dependency-ordered acquire
      hop  n → a2 along an observed sync edge (n, a2, d) if synced ∨ d ≤ first_scope; set acq ← a2
      po-hop n → b for atomics b with po(n, b), if synced ∨ anc ∈ atom
   past_release(acq, cur): acq is a CAS and some atomic r ≠ acq, cur with {acq, r} ∈ same_loc and
      po(acq, r) ∧ po(r, cur)  — cur lies past the thread's own unlock (knob CUVEIN_R3_PAST_RELEASE)
   cs_fenced(x, need): for every CAS c with po(c, x): release_scope(c, x) ≥ need
      — an ordinary store inside a CAS-acquired section needs a fence after the CAS

ordered(cur, anc, d, cur_read, anc_read, static):
   strength ← NONE if ¬static else loop_scope(cur) if cur = anc else dominance(cur, anc)      — R1
   strength ← max(strength, coherence(cur, anc))                                              — R2
   chain ← None
   if static ∧ strength < d ∧ ok(anc) ∧ ok(cur):  chain ← chain(anc, cur) or chain(cur, anc)   — R3, direction-agnostic
        where ok(x) = x ∈ atom ∨ x is a read ∨ cs_fenced(x, d)
   return (strength, chain)
```

`static = false` for a warp-same-instruction multi-lane write (no sync can intervene inside
one instruction; only R2 applies).

### 3.3 Candidate pairs

```
for each trace edge (cur ← anc), not cold, anc ≠ None:
   observed ← highest non-empty distance bucket of the edge (GRID > BLOCK > WARP), weight = its count
   if observed = NONE and the edge has no same-instruction lanes:
       observed ← the widest distance the EVENT STREAM shows for {cur, anc} (engine race records,
                  or the offline pass), else skip as intra_thread_only            — "edge rescue"
   judge(cur, anc, observed, weight, …)
then, if CUVEIN_EVENT_CANDIDATES ≠ 0:
   for each pc pair in (hb_races_sync_only ∪ hb_races) [vector-clock dump] or the offline pass
   [scalar-clock dump] that no edge produced a verdict for: take (anc, cur, distance, count) from
   the race records or the offline pass and judge it with event_candidate = true
```

A dependency edge keeps only the last accessor of a location, so a pair can have no edge
(read by A, read by B, write by B); the event stream restores it.

### 3.4 Offline barrier-only pass (`barrier_only_pairs`)

Algorithm 1 restricted to (PO) and (SYNC): the same records, the same `coherent` filter,
the same async agents (issue/commit/wait), **no** release/acquire joins, and one clock per
thread represented as a shared joined base per sync group plus a scalar own component
(`Sync` builds one base `J` and every participant points at it: O(threads) per barrier).
Output: `{(pc_lo, pc_hi): count}` of conflicts left unordered, the widest thread distance
per pair and the (earlier, later) orientation of the first one. Skipped when the dump has
no `hb_events`, when it exceeds `CUVEIN_BARRIER_PASS_MAX_LANES` (5,000,000 lane
accesses), or with `CUVEIN_BARRIER_PASS=0`. It is the scalar-clock mode's substitute for
the engine's `hb_races_sync_only` and is claimed identical to the oracle's second clock.

### 3.5 Verdict per pair (`judge`) and the matrix

```
read/read → skipped
same-instruction lanes: observed ← WARP, static ← false
(strength, chain) ← ordered(cur, anc, observed, …)
T1a: if cur or anc is a copy pc: chain ← None; if anc is the copy: strength ← NONE          — no static credit across a copy
r1r2 ← strength ≥ observed;   r3 ← chain ≠ None
vector-clock dump (hb_races present):
   dyn   ← {cur, anc} ∈ hb_races   (exact pc-pair match; legacy WAR records with a_pc = null match a read partner)
   sync  ← {cur, anc} ∈ hb_races_sync_only  (or the offline pass; None if neither exists)
   class ← model_bug   if dyn ∧ r1r2                 (R1/R2 claim all-schedule order, yet it raced: investigate)
           structural  if dyn ∧ ¬r1r2
           ordered     if ¬dyn ∧ (r1r2 ∨ r3)
           barrier-ordered if ¬dyn ∧ ¬r1r2 ∧ ¬r3 ∧ sync = false     (barrier joins alone order every observed conflict)
           latent      otherwise                                    (ordered only through this schedule's atomic hand-offs)
   verdict ← ORDERED iff class ∈ {ordered, barrier-ordered}
scalar-clock dump: ORDERED iff r1r2 ∨ r3 ∨ (offline pass exists ∧ {cur, anc} ∉ its pairs); else RACE
tags (never change the verdict): benign = "atomic-maintained-read" when a RAW/WAR race's read pc
   conflicts only with RMW writers; --assume-warp-lockstep turns a structural same-warp program-
   ordered pair into warp-po-ordered / ORDERED (never for a copy)
```

### 3.6 Cost

R1 is one dominator intersection per pair plus a reachability test on the region graph
(O(|G|)); `loop_scope` up to three reachability tests; R3 a DFS over atomic pcs and
observed hops; all per *distinct pc pair*. The only O(events) work is the offline pass,
O(lanes) plus O(threads) per barrier, memoised per kernel.

---

## 4. Deviation table — code at 3331d35 vs Algorithm 1 of the v3 proof

| # | item | code | v3 | who is right | action |
|---|---|---|---|---|---|
| 1 | tick / publish order | ticks, then publishes the post-tick clock; RMW recorded at the post-tick epoch | publishes, records at the pre-tick epoch, then ticks | **v3** — the code misses races (E1) | T9 Part 3, D1 |
| 2 | exit records | dropped; expected count ignores exits | exit records exist, "do nothing"; A3 pushes the count onto the collector | **neither**: A3 is false for early-exit kernels (E3) | model change + T3b |
| 3 | release map key | `loc` (per block for shared) | address | **code** (E4) | fix v3 text |
| 4 | conflict filter | `¬coherent(a, b)` with `.STRONG` ld/st per policy | any two accesses, ≥1 write/RMW | v4's DR/SC is the principled form; with one `last_write` the filter is **unsound** (E2) | decision: buckets (v4 O4) or policy `none` |
| 5 | second clock `vs`, `races_sync_only`, offline pass | present | absent | extension; needs its own statement (Prop. S below) | T9 |
| 6 | async agents (T1a) | present | absent | extension; needs a model appendix (E5) | T9 |
| 7 | readers check on RMW | present | present (`Check`) | agree | — |
| 8 | reader pcs in WAR | present | present | agree | — |
| 9 | monitor | four TV rejections; per-warp degrade when count unknown; no `exp` consistency check; partial-warp re-arrival accepted | six rows; rejects both; row 4 rejects a re-arriving warp | v3 row 4 over-rejects under ITS (E7); the rest v3 | adjust both |
| 10 | local memory key | `(local, addr)` | per thread | depends on what the collector records (E6) | check, then align or exclude |
| 11 | fence-gated (ATOM) | every strong RMW releases/acquires | same (v3 §impl 4, open) | open; v4 gates | decision |
| 12 | host ops, coherence profile, `HB_STATS` | present | outside / observational | — | — |
| 13 | mbarrier-completed copies | issuing thread's own access (pre-T1a reading) | absent | known hole | T1b |

---

## 5. Examination of the v3 proof against the implemented algorithm

### 5.1 The proof on its own terms

Checked by hand: Lemma `lem:seq`; the clock invariant `lem:vc` (all four cases, including
the completing-arrival case that uses (W2) and `lem:assembly`, and the atomic case where
publish-before-tick yields (c)); `lem:test` in both directions (the first edge leaving the
earlier thread is a tick; a record with epoch ≤ k is PO-before-or-equal the k-th tick);
`thm:complete`; `thm:sound` Case A (induction on `seq(d) < seq(b)` through `lastW`) and
Case B (readers since the last write, then Case A). I found no gap in these for the
algorithm *as written in the proof*. Two textual defects, both already in the deviation
table: `lastRelease` and the atomic successor are keyed by address (should be location,
E4), and §"State of the implementation" claims the code implements Algorithm 1 up to six
listed differences while the tick/publish order is not among them (E1).

### 5.2 E1 — tick before publish: `thm:sound` fails for the implementation

*Claim.* Let `Races(T)` be the proof's race set. The implementation reports a subset of
the proof's reports, and the omitted pairs are exactly

```
R_miss = { (a, b) : a a plain (non-RMW) record of t,  the PO-last tick of t before a is an RMW r,
           r ⊴HB b,  t's next tick after r is not in P(b),  seq(a) < seq(b) }
```

*Argument.* Let `c = epoch(r)` in the proof's numbering. The code publishes `{t: c+1}` at
`r` where the proof publishes `{t: c}`; barrier ticks publish the same values in both
(`Sync` is unchanged); joins only propagate. So for any other thread `u`,
`clk_impl[u][t] = clk_v3[u][t] + δ`, with `δ = 1` exactly when the maximal tick of `t` in
`u`'s frontier is an RMW reached through its (ATOM) edge (or a chain of them), and `δ = 0`
otherwise. Plain records keep their epochs; an RMW is recorded at `c+1` instead of `c`.
Now the test `epoch(a) > clk[u][t]`:

- `a` plain, `δ = 0`: identical outcome.
- `a` plain, `δ = 1`, `clk_v3 = c`: the proof reports iff `epoch(a) > c`, the code iff
  `epoch(a) > c+1`. They differ exactly for `epoch(a) = c+1`, the records of `t` between
  `r` and `t`'s next tick — those are unordered with `b` (no tick of `t` after `r` is in
  `P(b)`), so the proof reports a genuine race and the code does not. This is `R_miss`.
- `a` an RMW at tick `c'`: the code tests `c'+1 > clk_v3 + δ`. If `δ = 1` this is
  `c' > clk_v3`, the proof's test. If `δ = 0` then `clk_v3 ≠ c'` (the maximal tick is not
  an RMW), so `c'+1 > clk_v3 ⇔ c' > clk_v3`. No difference.
- In the opposite `seq` order (`b` before `a`), `a`'s own `Check` compares against `u`'s
  entry in `last_write`/`last_reads` with `t`'s clock of `u`, which is unaffected; the
  pair is reported. So the loss is one-directional, as observed on `rtraw`.

Consequences: `thm:complete` **holds** for the implementation (a subset of true races);
`thm:sound` **fails** on `R_miss`; `cor:causal` and hence the practical reading of the
certificate ("a race-free trace certifies") fail for the implementation until the order is
restored. The fix is the reordering in T9 Part 3; after it, `lem:vc`(c) holds as proved.
*Tested 2026-09-24* on the real `hb_oracle.py` (3331d35) with a hand-made seven-record
dump of the rtraw pattern (`design/proof/check_e1_e2.py`, no GPU): block 0 first, the
checked-in oracle reports nothing; with the three lines reordered (publish, record, tick)
it reports the RAW `(t: 0x28 write, u: 0x18 read)`; with u's read before t's write in
`seq` both report the WAR; block 1 first, both report nothing (the hand-off orders the
pair). Still to write: `test_write_after_unlock_other_schedule` on the real kernel, and
the corpus re-score.

### 5.3 E2 — the `coherent()` filter with a single `last_write` is unsound

With policy `generic` (the default since the RC1 fix), a `.STRONG` load or store is
*coherent* but joins no clocks. Two coherent writes with covering scopes never conflict, so
two unordered strong writes leave one `last_write` and the earlier is forgotten. The
location-level argument of `thm:sound` Case A needs `(a, d)` to be a race when `a` is
forgotten behind `d`; with the filter it is not a conflict, and the induction has no
witness. Counterexample (three threads, one location `x`):

```
A:  ST.E.STRONG.SYS x        (w0, cuda::atomic store)      — coherent, GRID
B:  ST.E.STRONG.SYS x        (w1)  unordered with w0        — coherent(w0, w1): no conflict, no report; last_write ← w1
    __syncthreads joining B and C
C:  LDG x                     (r, weak read)                 — last_write = w1, C knows B's epoch: no report
```

`(w0, r)` is a conflict (weak vs strong), unordered (A never synchronised with C): a race by
v3's definition and a **DR** by v4's; nothing at `x` is reported. Policy `none` restores
soundness (then `(w0, w1)` is reported) at the cost of the RC1 precision. This is
precisely v4's remark "Why v3's last-write bookkeeping is unsound here", and v4's buckets
`B_x[u, (kind, str, scope)]` (obligation O4) are the fix; v4's litmus O6 (vi) is the test.
*Tested 2026-09-24* the same way (`design/proof/check_e1_e2.py`, five records, block 0 =
A, block 1 = B and C with a 64-thread `__syncthreads`): policy `generic` reports nothing
— and `races_sync_only` is empty too, so the filter hides the pair from the second clock
as well; policy `none` reports the WAW `(w0, w1)`, the location-level witness. Still to
write: the real-kernel strict xfail.

The same filter also changes what "race" means for RMW pairs: two non-successive RMWs on a
location with covering scopes are not reported by the code even when no (ATOM) chain
connects them, while v3 reports them. v4's `SC` definition (RMW–RMW excluded) agrees with
the code; v3's definition does not. This is a definition to adopt, not a bug.

### 5.4 E3 — exits: assumption A3 is false, and the model must retire exited threads

`prop:fidelity` rests on A3 ("`exp(B)` is the number of threads the hardware barrier waits
for, and a thread that exits is not among them"). The collector's expected count is
`thread_count` or the block size and never subtracts exits, so for a kernel in which some
threads `return` before a `__syncthreads()`, A3 is false, no instance completes, (SYNC)
edges are missing, and every store → barrier → load pair is reported: T3's crs-cuda
(155 / 7 spurious reports on a race-free program). On the trace as recorded the reports
are "races of T", so `thm:complete` is not contradicted; completeness **with respect to
the execution** is, through `prop:fidelity`.

Fix at the model level, which the trace model already anticipates (exit records, and the
completion edges `exit_s CO dep_t^B` in §cert): an instance of key `(β, bar)` completes
when every thread of `β` has either arrived at it or exited before its completion;
`Definition instance` gains `exp = N_β − #exited(β)` per segment, `lem:assembly` and the
monitor rows follow, and the algorithm's `exit` case becomes "retire the lane from every
open and future instance of its block". The collector must emit per-warp exit records
with lane masks at the `EXIT` instruction, in `seq` order (T3b, route (a)). MM3 is
unchanged.

### 5.5 E4 — the release map must be keyed by location

v3 keys `lastRelease[x]` by address and defines the atomic successor "on one address". For
shared memory, two blocks' RMWs on one offset are on different locations; with a GRID
scope in the sidecar (`ATOMS` is BLOCK, so this needs a generic-addressed RMW resolved to
shared) v3 would create an (ATOM) edge across blocks that the hardware does not provide,
and in any case the successor relation is wrong. The code's `released[loc]` is the correct
model (F6). Change "address" to "location" in `Definition atomic successor`, the state
paragraph, and `lem:vc`(c). No proof step depends on the address form.

### 5.6 E5 — the async-agent extension has no model yet

T1a adds three kinds of events and a virtual thread per issuing thread. The proof's trace
model and `HB` need an appendix; a sketch that matches the code:

- Events: for thread `t`, copy records `c` with `tid(c) = agent(t)` at the `LDGSTS` pc (one
  global read, one shared write); `commit_k(t)`; `wait_N(t)`. Program order of `agent(t)`
  = its copies and commits in `seq`; a copy's *issue point* is its position in `t`'s PO.
- Ticks of `agent(t)`: its commits. `epoch(c) = 1 + #commits of t before c`. Copies
  issued after `commit_{k−1}` and before `commit_k` form group `k`.
- Generators: (ISSUE) every event of `t` PO-before the issue point of `c` precedes `c`
  (the code joins `vc[t]` into `vc[agent]` at issue, i.e. `P(issue point) ⊆ P(c)`);
  (WAIT) for `wait_N(t)` with `K` commits so far, every copy in groups `1 .. K−N` precedes
  every event of `t` PO-after the wait (the code joins the snapshot taken at
  `commit_{K−N}`, whose agent component is `K−N`, so exactly copies with epoch ≤ `K−N`
  become ordered). Two copies of one agent are never PO-ordered: the same-thread WAW check
  with observer `t` reports them unless a wait separated them.
- Clock invariant addendum: `vc[agent(t)][s]` = max tick of `s` in the frontier of the
  agent's last event, which by (ISSUE) is `t`'s frontier at the latest issue; the agent's
  own component counts commits. Both follow the shape of `lem:vc`.
- What the model must state as assumptions: a copy's global read is ordered after `t`'s
  earlier accesses only if PTX says so for `cp.async` (it is a weak asynchronous read;
  the code assumes issue order); barriers do not complete copies (correct per PTX);
  mbarrier completion is unmodelled (T1b) and such kernels silently keep the old reading.
  *To prove (T9):* `thm:complete` and `thm:sound` with these generators.

### 5.7 E6, E7 — smaller items

- **Local memory.** The code keys local accesses by `(local, addr)`. If the collector
  records the per-thread local window offset (the same value for every thread), distinct
  threads' private variables collide into one location and every local write becomes a
  spurious WAW. v3 keys local per thread. *To check* on one kernel with local spills;
  then either key per thread or exclude local memory from conflicts.
- **Monitor row 4.** v3 rejects a barrier arrival of a warp that is already pending. Under
  independent thread scheduling a warp can arrive at one `bar.sync` in two parts with
  disjoint lane masks; the code unions them (and (W1)'s "no thread id twice in a segment"
  still holds). Make row 4 per lane, not per warp.
- **Unknown expected count.** The code degrades to per-warp joins when the count is
  unknown and rejects only when a second warp appears; v3 rejects at once. On launched
  kernels the count is always known; keep v3's rule and delete the degrade path (v3 §impl
  item 1).

### 5.8 Proposition S — the second clock (to be added to the proof)

*Statement.* Let `HB_sync` be the closure of (PO) and (SYNC). After every record,
`vs[t][s]` = the maximal index among the *arrival* ticks of `s` in `t`'s frontier under
`HB_sync`, and `sync_pairs` contains the pc pair of every conflicting (in the `conf_impl`
sense) pair unordered by `HB_sync`, and nothing else. *Proof shape:* `lem:vc` with the
(ATOM) generator removed and ticks = arrivals (the RMW branch does not tick `vs`); the
test lemma is unchanged; the pc-pair projection loses nothing that the theorem claims. The
offline pass computes the same clocks with a shared base per sync group (`Sync` writes one
map and every participant references it, with its own component kept aside); its values
equal the oracle's `vs` because the base is immutable after the group and each thread's
component is overwritten only at its next group. *To test:* `test_offline_barrier_pass_matches_oracle` already does this per kernel.

### 5.9 Certificate (§cert)

Unchanged in structure. It applies to Algorithm 1 as written, under MM1–MM3 (still
obligations against the PTX formalisation, as the proof says). For the implementation:
`cor:causal` needs `thm:sound`, so it is void until E1 and E2 are resolved; `prop:fidelity`
needs A3, void for early-exit kernels until E3; the profile `Π` must be extended by the
agents' copies if E5 is adopted (copies are weak, so `Π` is unaffected; the matching
lemma's Step 1 must count exits — it already does, via MM3). Nothing in §cert refers to
the second clock or the verdict matrix; those are engineering, outside the certificate.

---

## 6. What v4 changes, against the same findings

| finding | v4 |
|---|---|
| E1 tick/publish | keeps publish-before-tick (Definition "Processing a record", step 4) — the fix must land in the code |
| E2 filter / last_write | fixed by buckets `B_x[u, key]` (Definition "Per-location state", `lem:rep`) and the DR/SC verdicts; reports RMW–RMW covering pairs never, strong–strong unordered pairs as SC (the code currently drops SC entirely — a decision) |
| E3 exits | "arrivals, departures and exits are processed as in v3": inherits the gap |
| E4 location key | inherits v3's address key (the RMW chain "on one location" in `def:chain` uses the right word) — align |
| E5 async | absent |
| E7 monitor | inherits |
| fence gating | fixed by `rel`/`acq` from fence adjacency (obligations O1–O3); `lem:ptx` discharges the (ATOM) containment |

---

## 7. Recommendations, in order

1. **Reorder tick/publish** in oracle and engine (T9 Part 3) and re-score; small, restores
   `thm:sound` for the RMW-only model. Needs D1.
2. **Decide E2**: implement v4's buckets (O4) with litmus O6 (vi) added first as a strict
   xfail, or fall back to policy `none` for the paper's soundness claims and present the
   `generic` precision as a separate configuration. Recommended: buckets.
3. **Adopt exit records into the model** (E3, T3b route (a)) and update `Definition instance`,
   `lem:assembly`, the monitor; A3 then becomes checkable rather than assumed.
4. **Edit v3** for E4 (location) and E7 (monitor row 4 per lane; delete the degrade path).
5. **Write the async appendix** (E5) and prove the two theorems with the new generators
   (T9); state the PTX assumption on `cp.async` read ordering explicitly; T1b closes the
   mbarrier hole.
6. **Add Proposition S** for the second clock, and a short paragraph on the verdict matrix
   stating that `latent` and `barrier-ordered` are engineering classes outside the
   single-trace theorems.
7. Update v3 §"State of the implementation" and the correspondence table
   (`vs`, `released[loc]`, `groups`, the new record kinds), and use the T8 names.

Status of this document: written from the code, unreviewed. `design/algorithms.tex`
renders §2–§4 as `algorithm2e` environments (labels `alg:vc-helpers`, `alg:vc-main`,
`alg:vc-access`, `alg:sc-static`, `alg:sc-rules`, `alg:sc-verdict`, `alg:sc-offline`,
`tab:deviations`); it compiles standalone and appended to `hb_oracle_proof_v3.tex`
(all macros are `\providecommand`-guarded). T6's remaining work is the fresh-context
review of §2–§3 against the code, the simulator `design/algorithms_check.py` against
the 33 litmus traces, and the walk-through of the two-modes examples; T9 starts from
§5. E1 and E2 were exercised on the real oracle with synthetic dumps
(`design/proof/check_e1_e2.py`); every other *to test* item is a test that does not exist
yet, and no claim here has been checked against a real trace.
